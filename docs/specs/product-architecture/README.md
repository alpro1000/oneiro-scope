# Product architecture: MCP-first, thin portal

Decision (2026-07, owner): **the chat is the product surface.** OneiroScope
ships as a remote-MCP connector for Claude / ChatGPT / Gemini. The website is
not an app — it is a thin portal that explains, signs up, charges, and hands
out access. Rich web UI is deferred until demand proves it is needed.

## Why

- The product is conversational by nature (ask about a chart, tell a dream,
  ask when to sign a contract). The chat already supplies natural-language
  input, follow-ups, memory, voice and mobile clients — for free.
- The moat is the deterministic engine + cited knowledge bases + provenance.
  A bespoke frontend adds none of it.
- Connector directories are distribution. A standalone web app needs marketing
  that a solo founder does not have.

Accepted cost: users on free ChatGPT tiers cannot add custom connectors, so
that segment is unreachable until a thin web chat exists. It is also the
segment that monetises worst.

## Surfaces

| Surface | Role | Status |
|---|---|---|
| **MCP connector** (`/mcp`) | the product — 45 tools | implemented (#155) |
| **Portal** (web) | explain · sign up · pay · issue access · legal | to build |
| **Kept web pages** | lunar calendar, natal-chart form — cheap, already work, good SEO landing content | already exist |
| **Rich web UI** | interactive maps, dashboards | deferred |

## The orchestrator — how a reading stays complete

Problem: a connector exposes 45 tools; the model does not know which sequence
makes a coherent reading and the user does not know what to ask, so the strong
material (astrocartography, decade map, life-pivot validation) never surfaces.

Solution: the server answers that itself. `analysis_plan`
(`backend/services/strategic/analysis_plan.py`) takes the inputs known so far
and returns an **ordered plan**:

- `next_step` — the single next thing to run,
- `ready` — everything runnable now, in canonical reading order,
- `blocked` — each with the exact input it waits on,
- `questions_to_ask` — verbatim questions (ru/en) to unblock them,
- `completed` — stages already run, so they stop being offered.

Canonical order (tracks): **Foundation** → natal chart · **Self** → money
contour, vocation map · **Timing** → transits, decade map, solar return,
electional day, horoscope · **Validation** → life pivots · **Place** →
astrocartography · **Relationships** → synastry · **Standalone** (no birth
data) → lunar day, dream, physiognomy, character→face.

Two design notes:
- Dependencies are **advisory, not enforced** (`better_after`): every tool
  recomputes the chart itself, so a user can jump straight to the money
  contour; the plan only says it reads better after the natal chart.
- Missing birth time does not block — it **degrades** (`degraded_without`),
  because houses and the Ascendant need it. The plan says so in words.

The connector's system instruction should tell the model to call
`analysis_plan` first whenever the user asks for a reading.

## Portal specification

Four jobs, nothing more.

### 1. Explain
- Landing: what it is, what makes it different (deterministic maths, cited
  sources, confidence ladder, no fortune-telling), example outputs.
- "How it works": add the connector in Claude / ChatGPT / Gemini, with the
  three concrete paths from `docs/deploy/mcp-connector.md`.
- Docs: what each analysis answers (generated from `analysis_plan`, so the
  site and the tool never drift apart).

### 2. Sign up
- Identity via the external IdP that also issues the OAuth tokens for the
  connector (any provider with Dynamic Client Registration). One account,
  used by both the portal and the connector — no second user table.

### 3. Pay
- Subscription via the existing billing code (`backend/api/v1/billing.py`,
  Stripe / Lemon providers already present).
- Plans gate by **quota and tool tier**, not by hiding tools: free tier gets
  lunar + natal + dream at a low call ceiling; paid unlocks the strategic
  patterns (decade map, life pivots, astrocartography, reports) and raises the
  ceiling. Quota infrastructure exists (`backend/tests/test_quotas.py`).

### 4. Issue and manage access
- "Connect" page: the MCP URL, an authorise button, current plan, usage this
  period, revoke.

### Legal (required for directory listing)
- Privacy policy and terms at stable URLs; the reflective/entertainment
  disclaimer already travels in every interpretive response.

## Entitlement wiring

```
Portal (IdP account + subscription)
        │  subscription state → scopes/claims in the access token
        ▼
Token (OAuth 2.1, aud = <backend>/mcp)
        │
MCP server: BearerAuthMiddleware validates iss/aud/exp/scope
        │  scope + quota decide which tools answer
        ▼
Tools (deterministic; no user data stored — birth data is passed per call)
```

`MCP_REQUIRED_SCOPES` gates the whole surface; per-tool tiering rides on the
same claims. Because the resource server was built first (#155), the paying
user and the connected user are the same identity automatically.

## Build order

1. **Now:** Render deploy → `/mcp` live → add the connector in Claude and use
   it. No website needed at all (`MCP_PUBLIC_URL` can be the Render URL).
2. **Then:** portal — landing, IdP sign-up, subscription, connect page, legal.
3. **Then:** directory submissions (privacy policy + tool annotations ready).
4. **Only on demand:** rich web UI for maps and dashboards.

The existing Next.js frontend is **parked, not deleted** — the lunar calendar
and i18n work stay useful as portal content.
