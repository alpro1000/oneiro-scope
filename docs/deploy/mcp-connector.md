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
| `MCP_PUBLIC_URL` | `https://<backend>/mcp` | canonical resource id + OAuth audience — **also the Host allow-list source**, see below |
| `MCP_ALLOWED_HOSTS` | *(optional)* | extra Host header values (custom domain), comma-separated |
| `MCP_REQUIRE_AUTH` | `true` | keep true for anything public |
| `MCP_AUTH_ISSUER` | e.g. `https://you.eu.auth0.com/` | your IdP |
| `MCP_AUTH_JWKS_URL` | *(optional)* | defaults to issuer + `/.well-known/jwks.json` |
| `MCP_AUTH_AUDIENCE` | *(optional)* | defaults to `MCP_PUBLIC_URL` |
| `MCP_REQUIRED_SCOPES` | *(optional)* | space-separated |
| `MCP_DEV_TOKEN` | local only | static bearer; **refused in production** |

Safety rail: in production with `MCP_REQUIRE_AUTH=true` and no
`MCP_AUTH_ISSUER`, the MCP surface refuses to mount rather than exposing the
tools unauthenticated. The REST API still boots.

### Three things that silently break the connector

Each of these produces a client-side error that names none of them, so they
are worth knowing by shape:

1. **`/mcp/mcp`.** FastMCP's transport serves itself at `/mcp` *inside* its own
   app; mounting that under `MCP_PATH` would put the endpoint at `/mcp/mcp` and
   404 the URL users paste. `build_mcp_http_app()` sets
   `streamable_http_path = "/"` so the mount path is the endpoint. A
   `MountPathNormalizer` middleware also rewrites bare `/mcp` in place instead
   of letting the router answer `307 → /mcp/` — behind a TLS-terminating proxy
   whose forwarded headers aren't trusted, that redirect's `Location` comes
   back `http://` and clients refuse it.
2. **`421 Invalid Host header`.** The transport enables DNS-rebinding
   protection by default with a *localhost-only* allow-list, which rejects
   every request to a real deployment. The public host comes from
   `MCP_PUBLIC_URL` (plus `MCP_ALLOWED_HOSTS` for a custom domain). With
   neither set, protection is switched off and a warning is logged — an
   unconfigured server that answers beats one that 421s everything.
3. **"Couldn't register with the sign-in service".** Publishing the RFC 9728
   document is a claim that this resource is OAuth-protected. Clients act on it
   *before* calling `/mcp`: they read it, look for `authorization_servers`, and
   when absent fall back to treating this origin as the authorization server
   and attempt Dynamic Client Registration against it — which fails. So
   `/.well-known/oauth-protected-resource` answers **404 until
   `MCP_AUTH_ISSUER` is set**. A public server must not advertise OAuth.

## 3. Verify the deployment

```bash
# discovery document — 404 on a public server, your AS once MCP_AUTH_ISSUER is set
curl -s https://<backend>/.well-known/oauth-protected-resource | jq

# handshake — must be 200 with an mcp-session-id header (no redirect)
curl -i -X POST https://<backend>/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
       "protocolVersion":"2025-06-18","capabilities":{},
       "clientInfo":{"name":"curl","version":"0"}}}'
```

With `MCP_REQUIRE_AUTH=true` the same call must instead be `401` with a
`WWW-Authenticate` header pointing at the discovery document.

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
