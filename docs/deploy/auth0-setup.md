# Closing the MCP endpoint: Auth0 as the authorization server

`backend/mcp/remote.py` implements the **resource server** half of OAuth 2.1 —
it validates tokens and publishes discovery. It deliberately does not issue
tokens. This is the click-by-click for wiring an issuer that does.

Auth0 is the example because it supports **Dynamic Client Registration**, which
is what Claude prefers (it registers itself, so you never paste a client ID).
Clerk, Stytch, WorkOS, Descope and Scalekit all work the same way — only the
console differs. UIs move; if a screen doesn't match, trust the current vendor
docs over this file and correct it here afterwards.

Until this is done the deployment runs with `MCP_REQUIRE_AUTH=false`, which
means **anyone with the URL can call every tool**. That is the reason to do it.

---

## What has to be true at the end

| Thing | Value for this deployment |
|---|---|
| Issuer | `https://<tenant>.<region>.auth0.com/` (trailing slash) |
| Audience / resource id | `https://oneiroscope-backend.onrender.com/mcp` |
| JWKS | `https://<tenant>.<region>.auth0.com/.well-known/jwks.json` |
| Token format | **JWT** (not opaque) — see step 3, this is the usual trip-up |
| DCR | enabled, with at least one domain-level connection |

The audience must equal `MCP_PUBLIC_URL` exactly — same scheme, host, path, no
trailing slash. A mismatch shows up as `Token rejected: Invalid audience`.

---

## 1. Tenant

Create a free Auth0 tenant. Region matters only for latency and data
residency; the region ends up in the issuer hostname, so pick before you wire
anything.

## 2. Register the MCP server as an API

Auth0 dashboard → **Applications → APIs → Create API**.

- **Name**: `OneiroScope MCP`
- **Identifier**: `https://oneiroscope-backend.onrender.com/mcp`
  (this becomes the `aud` claim — it is an identifier, Auth0 never calls it)
- **Signing algorithm**: RS256

Scopes are optional. Start with none: `MCP_REQUIRED_SCOPES` empty means the
resource server checks signature, issuer, audience and expiry only. Add
`mcp:read` / `mcp:write` later if you want per-tool gating — the enforcement
point already exists in `verify_bearer()`.

## 3. Make sure you get a JWT back, not an opaque token

Auth0 issues a JWT access token only when the authorize request carries an
`audience`. MCP clients send the RFC 8707 `resource` parameter instead, and
whether Auth0 maps one to the other depends on the tenant's settings and how
current your tenant is.

The reliable belt-and-braces setting: **Settings → General → API Authorization
Settings → Default Audience** = `https://oneiroscope-backend.onrender.com/mcp`.

With that set, every token the tenant issues is a JWT for this API even if the
client never asked. It is a tenant-wide setting — fine for a tenant that exists
only to guard this server, worth revisiting if you later add other APIs.

Symptom if you skip it: the connector completes the login flow, then every
call fails with `Malformed token` — because the token is a 32-char opaque
string, not a JWT.

## 4. Enable Dynamic Client Registration

**Settings → Advanced → OIDC Dynamic Application Registration** → on.

Then the part that is easy to miss: DCR-created clients can only use
connections flagged **domain-level**. With none flagged, the login page shows
no way to sign in. There is no dashboard toggle — it goes through the
Management API:

```bash
# find the connection id: Authentication → Database → <your connection>
curl -X PATCH "https://<tenant>.<region>.auth0.com/api/v2/connections/<CONNECTION_ID>" \
  -H "authorization: Bearer <MGMT_API_TOKEN>" \
  -H "content-type: application/json" \
  -d '{"is_domain_connection": true}'
```

A management token comes from **Applications → APIs → Auth0 Management API →
API Explorer**.

If you would rather not enable DCR at all, Claude also accepts a client ID you
paste into the connector's advanced settings. Then create a **Regular Web
Application** in Auth0 instead, allow the callback URL Claude shows you, and
skip this step.

## 5. Point the backend at it

Render → the backend service → **Environment**:

| Key | Value |
|---|---|
| `MCP_AUTH_ISSUER` | `https://<tenant>.<region>.auth0.com/` |
| `MCP_AUTH_AUDIENCE` | `https://oneiroscope-backend.onrender.com/mcp` |
| `MCP_REQUIRE_AUTH` | `true` |
| `MCP_REQUIRED_SCOPES` | *(leave empty for now)* |

`MCP_AUTH_JWKS_URL` is derived from the issuer and only needs setting for an
IdP that puts JWKS somewhere non-standard.

Save → deploy. Two behaviours flip on this deploy: the discovery document
starts being served (it 404s while there is no issuer, on purpose — see
`docs/deploy/mcp-connector.md`), and `/mcp` starts refusing anonymous calls.

## 6. Verify before touching the chat client

The quickest check needs no terminal — open
**`<BASE>/connect/diagnostics`** in a browser. The server reports on its own
configuration: `ready: true` and `mode: "oauth"` means every failure mode in
this document is clear. Anything failing comes with the environment variable
that fixes it. (A browser agent can read this page; it cannot run curl.)

The same checks by hand:

```bash
BASE=https://oneiroscope-backend.onrender.com

# 1. discovery is live and names the issuer. Use the CANONICAL path — RFC 9728
#    §3.1 appends the resource's own path to the well-known segment, so this is
#    what a conforming client requests. The bare path answers as a fallback.
curl -s $BASE/.well-known/oauth-protected-resource/mcp | jq
# → {"resource":".../mcp","authorization_servers":["https://<tenant>...auth0.com/"],...}
#                                     note the trailing slash ↑  it must match step 2

# 2. the issuer's own metadata is reachable (this is what the client reads next)
curl -s https://<tenant>.<region>.auth0.com/.well-known/oauth-authorization-server | jq \
  '{issuer, registration_endpoint, authorization_endpoint, token_endpoint}'
# registration_endpoint must be present, or DCR is still off.
# `issuer` must equal step 1's authorization_servers[0] CHARACTER FOR CHARACTER.
# Auth0 returns it with a trailing slash; RFC 8414 §3.3 lets a strict client
# abort on a one-character difference, before any login window appears. So set
# MCP_AUTH_ISSUER to exactly this string — it is now published unmodified.

# 3. anonymous calls are refused, and say where to log in
curl -i -X POST $BASE/mcp -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# → 401 + WWW-Authenticate: Bearer realm="OneiroScope MCP", resource_metadata="..."
```

All three green means the failure surface left is inside the IdP, not here.

## 7. Add the connector

Claude → Settings → Connectors → *Add custom connector* →
`https://oneiroscope-backend.onrender.com/mcp`. It reads the discovery
document, registers itself, opens the Auth0 login, and comes back with a token.

Smoke test: *"Посчитай мою карту: 1 июля 1977, 22:30, Запорожье"* — should call
`validate_birth_data` then `calculate_natal_chart`, or start from
`analysis_plan`.

---

## When it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| "Couldn't register with the sign-in service" | discovery served with no `authorization_servers`, client tries DCR against this origin | set `MCP_AUTH_ISSUER` **and** `MCP_REQUIRE_AUTH=true`, or leave the issuer unset so discovery 404s and the server reads as public |
| Discovery still 404s with the issuer set | `MCP_REQUIRE_AUTH` is still `false` — the server won't advertise protection it doesn't enforce | set `MCP_REQUIRE_AUTH=true` (the log says so at startup) |
| Login page loads, no sign-in method | DCR client has no domain-level connection | step 4 `is_domain_connection` |
| Connects, every tool call fails `Malformed token` | opaque access token | step 3 Default Audience |
| `Token rejected: Invalid audience` | `MCP_AUTH_AUDIENCE` ≠ the API identifier | make them byte-identical |
| `Token rejected: Invalid issuer` | trailing-slash mismatch | Auth0 issuer **has** a trailing slash |
| Client aborts during metadata discovery, before any login window | the `issuer` we publish differs from the one Auth0 returns — RFC 8414 §3.3 requires them byte-identical, and a strict client stops there | set `MCP_AUTH_ISSUER` to exactly what `/.well-known/openid-configuration` reports, **including** the trailing slash. It is now published verbatim, not normalised |
| Discovery 404s at `/.well-known/oauth-protected-resource/mcp` | pre-fix build served only the bare path | redeploy; RFC 9728 §3.1 puts the resource's path *after* the well-known segment, and both paths are served now |
| `Could not fetch JWKS` (503) | egress blocked or wrong JWKS URL | `curl` the JWKS URL from the Render shell |
| `421 Invalid Host header` | transport allow-list | `MCP_PUBLIC_URL` / `MCP_ALLOWED_HOSTS`, see mcp-connector.md |
| 404 on `/mcp` | endpoint at `/mcp/mcp` (pre-fix build) | redeploy latest `main` |

## Cost

Auth0's free tier covers 25k monthly active users, which is far past the point
where this project would need a paid plan for other reasons. DCR and RS256 are
not gated behind a paid tier.

## What this does not cover

Auth0 authenticates the *connector*. It says nothing about which plan a user is
on or how many analyses they have run — that is the account layer
(`backend/api/v1/auth.py`, `billing.py`, `users.py`) and the portal account
page. Linking the two means mapping the token's `sub` to a `User` row; the
subject is already handed to the transport in
`scope["state"]["mcp_subject"]`, which is the hook to build on.

---

## Когда динамическая регистрация не срабатывает

Симптом в Claude: **«Couldn't register with OneiroScope's sign-in service»**,
подключение не начинается. Это провал шага, на котором Claude регистрирует
себя OAuth-клиентом (RFC 7591) — до всякого логина.

**Внимание на ложно-зелёную проверку.** Строка `dcr_advertised` в
`/connect/diagnostics` по умолчанию читает лишь наличие поля
`registration_endpoint` в discovery-документе, а Auth0 публикует это поле
независимо от настройки тенанта. Проверить по-настоящему:

```
<backend>/connect/diagnostics?probe=1
```

Проба посылает намеренно невалидную регистрацию (пустое тело), поэтому
клиента не создаёт: `400` — регистрация открыта, `403` — отказ.

### Путь A — обойти DCR вовсе (5 минут, рекомендую)

Диалог коннектора сам это предлагает: «add an OAuth Client ID».

1. Auth0 → **Applications → Create Application** → **Regular Web Application**.
2. В настройках приложения → **Allowed Callback URLs**, через запятую:
   ```
   https://claude.ai/api/mcp/auth_callback,
   https://claude.com/api/mcp/auth_callback
   ```
   (точный адрес показан в самом диалоге коннектора при ошибке — сверьте.)
3. **Advanced Settings → Grant Types**: включить `Authorization Code` и
   `Refresh Token`.
4. **Applications → APIs → `OneiroScope MCP` → Settings → Allow Offline
   Access — ВКЛЮЧИТЬ.** Без этого Auth0 не выдаёт refresh-токен, коннектор
   подключится и отвалится через час-другой «сам по себе». Пункт живёт у
   API, а не у приложения, поэтому его пропускают.
5. Скопировать **Client ID** и **Client Secret**.
6. В Claude → Connectors → OneiroScope → **Advanced settings**: вставить оба.

Что не нужно: авторизовывать приложение для API отдельным списком — это
требуется только для machine-to-machine (client credentials). Здесь поток
authorization code, и audience приходит из нашего RFC 9728 документа.

Серверу это безразлично: он ресурс-сервер, проверяет подпись по JWKS и
audience. Кто именно клиент — дело Claude и Auth0.

### Путь B — починить DCR

Классическая ловушка Auth0: динамически зарегистрированные клиенты —
**third-party applications**, а они могут пользоваться только **domain-level**
соединениями. Мало включить флаг:

1. **Settings → Advanced → OIDC Dynamic Application Registration** — включить.
2. Повысить соединение до domain-level. В дашборде этого пункта нет, только
   Management API (Auth0 → **Management API Explorer**):
   ```
   GET   /api/v2/connections            → найти id нужного соединения
   PATCH /api/v2/connections/{id}       {"is_domain_connection": true}
   ```
3. Проверить: `<backend>/connect/diagnostics?probe=1` → `400`.
