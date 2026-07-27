# Task for Claude-for-Chrome: close the MCP connector with OAuth (Auth0 + Render)

Hand this whole file to the browser agent. It drives dashboards in a browser
where the owner is already logged in. Repo: `alpro1000/oneiro-scope`.

## Goal

Bring the OneiroScope MCP connector up **already authenticated** — never
passing through a state where `/mcp` is open to the internet. At the end,
adding the connector in Claude must trigger an Auth0 login and then work.

Background for the whole task: `docs/deploy/auth0-setup.md` (values, traps) and
`docs/deploy/mcp-connector.md` (how the endpoint behaves). Read them if a step
does not match what you see.

## Guardrails (read first, obey strictly)

- **Never type, paste, echo or screenshot a secret.** Client secrets, API keys,
  `SECRET_KEY`, database passwords, management tokens. If a step needs a secret
  value you do not have, STOP and ask the owner. Never put a secret into chat.
- **Never enable `MCP_REQUIRE_AUTH=false`.** The owner explicitly chose the
  route with no open window. If a step seems to require opening the endpoint,
  stop and ask instead.
- **Confirm before anything destructive or billable**: deleting a service or
  application, changing a plan, enabling paid features. Describe it and wait
  for "yes".
- **Do not touch unrelated projects, services or tenants.**
- **Never invent a URL, tenant name or ID.** Copy exactly what the dashboard
  shows and carry it forward verbatim.
- If the UI differs from this script, describe what you see and ask. Auth0's
  console gets reorganised regularly; this file will be out of date before the
  product is.
- After each phase, post a short status line: what you did, and any value the
  next phase needs.

## What the owner must supply

- Access to the Render dashboard (service `oneiroscope-backend`).
- An Auth0 account, or permission to create a free one.

Nothing else. There is no secret to hand over for this task: the connector uses
Dynamic Client Registration, so no client secret is ever pasted anywhere.

---

## Phase 0 — Read the current state (no changes)

1. Open `https://oneiroscope-backend.onrender.com/connect/diagnostics`.
   This is a self-check page the server serves about itself. Report the whole
   JSON body back — in particular `ready`, `mode`, and every check where
   `"ok": false`.
2. If the page 404s, the deployment predates it: go to Render → service
   `oneiroscope-backend` → **Manual Deploy → Deploy latest commit**, wait for
   **Live**, then retry step 1.
3. Expected right now: `mode` is `unavailable` or `public`, and the
   `auth_configured` check is failing. That is what this task fixes.

Report the JSON before continuing.

---

## Phase 1 — Auth0 tenant and API

1. Go to `https://auth0.com`, sign in or create a free account.
   - If creating: pick a region and tell the owner which one. It ends up in the
     issuer hostname and cannot be changed later.
2. Note the tenant domain shown in the top-left, e.g.
   `dev-ab12cd34.eu.auth0.com`. **Record it** — every later step uses it.
3. **Applications → APIs → Create API**:
   - Name: `OneiroScope MCP`
   - Identifier: `https://oneiroscope-backend.onrender.com/mcp`
     (exact, no trailing slash — this becomes the token audience; Auth0 never
     calls this URL)
   - Signing algorithm: **RS256**
4. Leave permissions/scopes empty for now.

Report: the tenant domain.

---

## Phase 2 — The two settings that break everything if missed

Both of these are documented failure modes, not optional polish.

1. **Default Audience.** Auth0 issues an opaque token instead of a JWT unless
   the request names an audience, and MCP clients send `resource`, not
   `audience`. Go to **Settings → General → API Authorization Settings →
   Default Audience** and set it to
   `https://oneiroscope-backend.onrender.com/mcp`. Save.
   - Symptom if skipped: login succeeds, then every tool call fails with
     "Malformed token".

2. **Dynamic Client Registration.** Go to **Settings → Advanced → OIDC Dynamic
   Application Registration** and turn it **on**.
   - Symptom if skipped: Claude reports it "couldn't register with the sign-in
     service".

3. **Domain-level connection.** DCR-created applications can only use
   connections flagged domain-level, and there is no dashboard toggle. Go to
   **Authentication → Database** and note the connection name (usually
   `Username-Password-Authentication`).
   - Try the dashboard first: open the connection and look for a
     "domain level" / "promote to domain level" switch. Some tenants have it.
   - If there is no switch, this needs a Management API call. **Do not attempt
     it blind** — report to the owner that the connection needs
     `is_domain_connection: true`, and that `docs/deploy/auth0-setup.md` has
     the exact `curl`. Ask whether they want to run it or to use the API
     Explorer under **Applications → APIs → Auth0 Management API → API
     Explorer**.
   - Symptom if skipped: the login page loads with no way to sign in.

4. Verify the issuer publishes what clients need. Open
   `https://<tenant-domain>/.well-known/oauth-authorization-server` in a tab.
   Confirm the JSON contains `registration_endpoint`. If it does not, DCR is
   still off — go back to step 2.

Report: which of the three were already set, which you changed, and whether
`registration_endpoint` is present.

---

## Phase 3 — Render environment

Only now touch Render, so the endpoint goes from closed to authenticated with
no open state in between.

1. `https://dashboard.render.com` → service **oneiroscope-backend** →
   **Environment**.
2. Set or confirm, exactly:

   | Key | Value |
   |---|---|
   | `MCP_ENABLED` | `true` |
   | `MCP_PUBLIC_URL` | `https://oneiroscope-backend.onrender.com/mcp` |
   | `MCP_REQUIRE_AUTH` | `true` |
   | `MCP_AUTH_ISSUER` | `https://<tenant-domain>/` — **with the trailing slash** |
   | `MCP_AUTH_AUDIENCE` | `https://oneiroscope-backend.onrender.com/mcp` |
   | `MCP_REQUIRED_SCOPES` | *(leave empty / do not create)* |

   The trailing slash on the issuer is not cosmetic: Auth0 puts it in the `iss`
   claim, and a mismatch rejects every token.
3. Do **not** add `MCP_DEV_TOKEN`. It is refused in production anyway.
4. Save. Render will redeploy automatically; if it does not, use
   **Manual Deploy → Deploy latest commit**. Wait for **Live**.

Report: the list of MCP-prefixed variables now set (values are not secret —
they are all public URLs), and the deploy status.

---

## Phase 4 — Verify before touching Claude

1. Reload `https://oneiroscope-backend.onrender.com/connect/diagnostics`.
   - Expected: `"ready": true`, `"mode": "oauth"`, every check `ok: true`.
   - If `jwks_reachable` fails → the issuer is wrong (usually the missing
     trailing slash).
   - If `host_allowed` fails → `MCP_PUBLIC_URL` does not match the real
     hostname.
   - If `discovery_published` fails → `MCP_REQUIRE_AUTH` is not `true`.
   Fix and re-check before continuing. Report the JSON either way.
2. Open `https://oneiroscope-backend.onrender.com/.well-known/oauth-protected-resource/mcp`
   (the canonical RFC 9728 path — the bare path without `/mcp` answers too).
   Expected: JSON listing your Auth0 domain under `authorization_servers`,
   **with its trailing slash**, matching the `issuer` in Auth0's own
   `/.well-known/openid-configuration` character for character.
   A 404 here means OAuth is not both configured and enforced.
3. Open `https://oneiroscope-backend.onrender.com/connect`.
   Expected: the connect page, showing the connector URL.

Do not proceed until step 1 says `ready: true`.

---

## Phase 5 — Add the connector in Claude

1. Claude → **Settings → Connectors → Add custom connector**.
2. URL: `https://oneiroscope-backend.onrender.com/mcp`
3. Expected: Claude registers itself, opens an Auth0 login, and you create an
   account or sign in. Then the tools appear.
4. Smoke test in a chat:
   `Посчитай мою карту: 1 июля 1977, 22:30, Запорожье`
   Expected: it calls `validate_birth_data` / `calculate_natal_chart` (or starts
   from `analysis_plan`) and returns a chart with a disclaimer.
5. If it fails, re-open `/connect/diagnostics` first — it will usually name the
   cause. The symptom→cause table at the end of
   `docs/deploy/auth0-setup.md` covers the rest.

Report: whether the connector answered, and the first ~10 lines of its reply.

---

## Phase 6 — Other panels (check, mostly nothing to do)

Only report on these; change nothing without asking.

- **Vercel** — the frontend is parked by decision (MCP-first architecture, see
  `docs/specs/product-architecture/`). `render.yaml` no longer defines a
  frontend service. If a Vercel project exists and is failing, that is expected
  and harmless. Report its state; do not delete it.
- **Lemon Squeezy** (billing) — needed only when the owner starts charging. If
  the account exists, confirm the store and product slugs match
  `backend/services/billing/lemon_provider.py`. If it does not exist, note that
  and stop; subscriptions are not on the critical path for the connector.
- **GeoNames** — the geocoder account (`GEONAMES_USERNAME` on Render). It was
  configured previously. Confirm the variable is still set; a missing one
  degrades city search to a ~90-city fallback list rather than breaking.
- **Render → Postgres and Redis** — confirm both are running and that
  `DATABASE_URL` / `REDIS_URL` are wired to them. The connector does not need
  the database, but the account page does.
- **Render → `ENVIRONMENT`** — should be `production`. If it says
  `development`, report it: the app auto-creates database tables in that mode,
  which is not wanted in production. Do not change it without asking, since it
  also affects cookie flags and the dev-token path.

---

## Definition of done

- `/connect/diagnostics` reports `ready: true`, `mode: "oauth"`.
- `/.well-known/oauth-protected-resource/mcp` lists the Auth0 domain, trailing
  slash matching Auth0's own `issuer`.
- Adding the connector in Claude triggers an Auth0 login.
- The smoke-test question returns a computed chart.
- `MCP_REQUIRE_AUTH` was `true` at every moment — the endpoint was never open.
- A short written report: what was changed in each panel, what was already
  correct, and anything you were asked to stop on.
