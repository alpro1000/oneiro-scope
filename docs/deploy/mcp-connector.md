# OneiroScope as a connector (remote MCP)

One remote MCP server, three chats. Claude, ChatGPT and Gemini all speak MCP,
so the same URL works everywhere — only the place you paste it differs.

Implementation: `backend/mcp/remote.py` (transport + OAuth resource server),
mounted into the FastAPI app in `backend/app/main.py` at `settings.MCP_PATH`
(default `/mcp`). Same Render service as the REST API — no second host.

## Architecture

```
Claude / ChatGPT / Gemini
        │  HTTPS + Bearer (OAuth 2.1, PKCE)
        ▼
https://<backend>/mcp          ← streamable-HTTP transport (FastMCP)
        │  guarded by BearerAuthMiddleware
        ▼
backend/mcp/tools/*            ← 30+ tools (natal, transits, lunar, dreams,
                                  physiognomy, strategic patterns)
https://<backend>/.well-known/oauth-protected-resource   ← RFC 9728 discovery
```

The MCP spec requires **OAuth 2.1 with PKCE**; a plain API key is not a valid
connector flow, and pure `client_credentials` is rejected as a user-facing
flow. This repo implements the **resource server** half only — token
validation and discovery. The **authorization server** is external on purpose:
running your own is the one part genuinely worth delegating.

## 1. Pick an authorization server

Claude prefers **Dynamic Client Registration** (it registers itself), and also
supports Client ID Metadata Documents or Anthropic-held credentials. Any IdP
with DCR works: Auth0, Clerk, Stytch, WorkOS, Descope, Scalekit.

Configure there:
- an **API / resource** whose identifier is exactly your MCP URL,
  e.g. `https://oneiroscope-backend.onrender.com/mcp` (this becomes the `aud`),
- scopes, if you want them (e.g. `mcp:read`),
- DCR enabled.

## 2. Backend env vars (Render)

| Variable | Value | Notes |
|---|---|---|
| `MCP_ENABLED` | `true` | default |
| `MCP_PATH` | `/mcp` | default |
| `MCP_PUBLIC_URL` | `https://<backend>/mcp` | canonical resource id + OAuth audience |
| `MCP_REQUIRE_AUTH` | `true` | keep true for anything public |
| `MCP_AUTH_ISSUER` | e.g. `https://you.eu.auth0.com/` | your IdP |
| `MCP_AUTH_JWKS_URL` | *(optional)* | defaults to issuer + `/.well-known/jwks.json` |
| `MCP_AUTH_AUDIENCE` | *(optional)* | defaults to `MCP_PUBLIC_URL` |
| `MCP_REQUIRED_SCOPES` | *(optional)* | space-separated |
| `MCP_DEV_TOKEN` | local only | static bearer; **refused in production** |

Safety rail: in production with `MCP_REQUIRE_AUTH=true` and no
`MCP_AUTH_ISSUER`, the MCP surface refuses to mount rather than exposing the
tools unauthenticated. The REST API still boots.

## 3. Verify the deployment

```bash
# discovery document — must list your authorization server
curl -s https://<backend>/.well-known/oauth-protected-resource | jq

# unauthenticated call — must be 401 with a WWW-Authenticate header
curl -i -X POST https://<backend>/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Local smoke test without an IdP:

```bash
MCP_DEV_TOKEN=local-secret MCP_PUBLIC_URL=http://localhost:8000/mcp \
  uvicorn backend.app.main:app --port 8000
curl -s -X POST localhost:8000/mcp \
  -H 'authorization: Bearer local-secret' \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## 4. Add it in each chat

**Claude** — Settings → Connectors → *Add custom connector* → paste
`https://<backend>/mcp`. Claude fetches the discovery document, runs the OAuth
consent flow, then lists the tools. (Custom connectors are a paid-plan
feature; org admins can restrict them.)

**ChatGPT** — connectors were renamed **apps** in Dec 2025. Settings →
*Security and login* → enable **Developer mode**; then Settings → **Plugins**
(or `chatgpt.com/plugins`) → **+** → paste the server URL. Available on
Plus/Pro/Business — **not** on Free. For a public listing you ship through the
**Apps SDK** and its review process.

**Gemini** — MCP support landed in **Gemini Spark** (web + mobile, June 2026):
at the bottom of `gemini.google.com/apps` add a custom app link. In the Gemini
API, pass an `mcp_server` tool. Gemini CLI reads MCP servers from
`settings.json`.

Reality check: "any user, any chat" isn't symmetric yet — ChatGPT needs a paid
plan plus Developer mode, Gemini's support is still rolling out, and the
directories require review. Adding by URL works today on every platform above.

## 5. Directory submission (optional, later)

Needed to reach users who won't paste a URL:
- stable **privacy policy URL** and public docs,
- tool **annotations** (`readOnlyHint`, `destructiveHint`, …) so reviewers can
  see which tools mutate state — ours are read-only computations,
- accurate tool names/descriptions (they are the review surface),
- OAuth via DCR / CIMD / Anthropic-held creds — each user still consents.

Details change; check the current Claude and OpenAI docs before submitting.

## Notes specific to this project

- The disclaimer and no-determinism rules apply to connector output exactly as
  in the app: every interpretive tool response carries its disclaimer, and the
  confidence ladder travels in the `layer`/`confidence` fields.
- Physiognomy tools stay self-reflection-only (`western.json` ethics note); the
  reverse-physiognomy tool keeps its `fictional_or_self_only` gate.
- Tools are stateless and read-only, which is what makes this safe to expose:
  no tool writes user data, and birth data is passed per call, not stored.
