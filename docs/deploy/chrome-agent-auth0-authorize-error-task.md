# Task for Claude-for-Chrome: Auth0 answers "Oops!, something went wrong" at login

Hand this whole file to the browser agent. It drives the Auth0 dashboard in a
browser where the owner is already logged in.

Tenant: `dev-u22itgv3h8ew1sgz.eu.auth0.com`
Backend: `https://oneiroscope-backend.onrender.com`

## Situation

Connecting the OneiroScope connector opens the Auth0 login and, instead of a
sign-in form, shows Auth0's own branded error page:

> **OneiroScope** — Oops!, something went wrong
> There could be a misconfiguration in the system or a service outage.

Observed 2026-09-05 08:16 local time, on a phone, at
`dev-u22itgv3h8ew1sgz.eu.auth0.com`.

**This is not the same failure as the previous two tasks.** Those were
"Couldn't register with OneiroScope's sign-in service" — a failure to register
a client, before Auth0 was ever reached. Here the request got all the way to
Auth0's `/authorize` and Auth0 aborted, rendering the tenant's own branded
error page. Different step, different causes.

### What has already been ruled out — do not re-investigate it

The backend was probed live on 2026-09-05 06:21 UTC, on the deployed commit
`70de69163e5c`, through a working MCP connector. A call to `dream_series_stats`
returned a resolved account (`"status": "insufficient_data"`, with a real
`user_id`) rather than `"sign_in_required"`.

For that to happen, every one of these had to be correct: the bearer token
validated against JWKS, `iss` matched (trailing slash included), `aud` matched,
`/mcp` was mounted, the Host allow-list passed, and the OAuth subject reached
the tool and resolved to a user row.

So the resource server is healthy and **the fault is on the Auth0 side, at the
`/authorize` step, for the client the phone is using**. A different client
(the one already configured in the owner's desktop Claude) authenticates fine
against the same tenant right now.

Do not change anything on Render. Do not touch `MCP_AUTH_ISSUER`,
`MCP_AUTH_AUDIENCE`, `MCP_PUBLIC_URL` or `MCP_REQUIRE_AUTH` — they are proven
correct by the probe above, and changing them would break the connection that
currently works.

## Known-good values (copy, never retype)

| | Value |
|---|---|
| Issuer | `https://dev-u22itgv3h8ew1sgz.eu.auth0.com/` — **with** the trailing slash |
| API identifier / audience | `https://oneiroscope-backend.onrender.com/mcp` |
| API name in the dashboard | `OneiroScope MCP` |
| Manual application | `OneiroScope Connector (manual)` |

## Guardrails (read first, obey strictly)

- **Never type, paste, echo or screenshot a Client Secret**, a signing key, or
  a Management API token. Client *IDs* are public identifiers and are fine.
- **Never set `MCP_REQUIRE_AUTH=false`** and never suggest it. The owner chose
  the route with no open window; opening `/mcp` to the internet is not a
  diagnostic step.
- **Confirm before anything irreversible or billable**: deleting an
  application, changing a plan, enabling a paid feature, changing a
  connection's settings. Describe it and wait for "yes".
- **Never delete `API Explorer Application`** (Auth0's own admin client) or the
  API `OneiroScope MCP` (the resource every token is issued for).
- Do not touch other tenants, projects or services.
- **Navigate by URL, never by hunting the sidebar.** A browser agent once burned
  68 steps scrolling Auth0's menus and died of context overflow mid-task:
  - Logs: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/logs`
  - Applications: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/applications`
  - APIs: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/apis`
  - Database connections: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/connections/database`
- **NEVER transcribe an identifier — use the copy button.** Auth0 renders IDs
  in a font where `I`/`1`, `O`/`0` and `l`/`I` are barely distinguishable. This
  has already cost three debugging sessions: a `user_id` two characters short,
  `tpc_` ids drifting a character per report, and a capital `I` read as digit
  `1` that had Auth0 answering `Unknown client` for an hour while every setting
  around it was already correct.
- **One phase per run.** Finishing a phase and reporting beats attempting all
  of them and losing the transcript.
- **Do not retry a failed connect in a loop.** Every attempt can leave another
  dead `tpc_` client behind, and the tenant has a cap on them — that loop is
  what produced six of them last time.

---

## Phase 0 — Read the reason out of the Auth0 log (no changes)

This is the whole point of the task. Auth0 never prints the reason on that
error page; it writes it to the tenant log. Everything after this phase depends
on what you find here, so **stop and report before doing anything else.**

1. Open `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/logs`.
2. Find the entries around **2026-09-05, 08:16 local time** (the log shows UTC
   — convert, and if in doubt take the newest failed entry). Ask the owner to
   reproduce the error while you watch the log if nothing matches.
3. Open the top matching entry and report **verbatim, copied not retyped**:
   - `type` (the short event code) and its human label
   - `description` — this is the sentence that names the cause
   - `client_name` and `client_id`
   - `connection` (if present)
   - `user_agent` — confirms it is the phone
4. Report those five fields and **stop**. Do not act on a guess about what they
   mean; the branch table in Phase 2 keys off the `description` text.

If the log shows no failed entry at that time at all, say so — that would mean
the request never reached Auth0, which contradicts the screenshot and needs the
owner's input before continuing.

---

## Phase 1 — Two read-only facts to report alongside the log

Neither changes anything.

1. Open, and report the `dcr_advertised` row verbatim:
   ```
   https://oneiroscope-backend.onrender.com/connect/diagnostics?probe=1
   ```
   `?probe=1` sends a deliberately invalid registration (empty body — it cannot
   create a client) and reads the status: **400 / 422** → dynamic registration
   is open; **401 / 403** → it is refused.
2. Open the Applications list and report every row with **name, type, Client ID
   prefix, and whether it carries the THIRD-PARTY badge**. Note in particular:
   - how many rows have a `tpc_` Client ID (these are disposable, created one
     per connect attempt), and
   - whether the tenant shows an **"approaching its available applications
     limit"** banner.

---

## Phase 2 — Branch on what the log said

Match the `description` from Phase 0. **If none of these match, report the text
and stop** — inventing a fix for an unrecognised error is how the previous
rounds went wrong.

### A. `Client "..." is not authorized to access resource server "https://oneiroscope-backend.onrender.com/mcp"`

The single most likely cause, and it is a permission on the **application**,
not on the API.

1. Applications → open the application whose `client_id` the log named.
2. Tab **API Access** → row `OneiroScope MCP` → **Edit** → enable
   **User-delegated Access**. Leave the scopes empty.
3. **The two permissions here are not interchangeable:**

   | | What it is | Needed here |
   |---|---|---|
   | **User-delegated Access** | the user delegates access to the app — authorization-code flow | **YES** |
   | **Client Access** | the app acting as itself — client credentials | no |

   Enabling Client Access creates a client grant and leaves the error word for
   word unchanged. `0 / 0 permissions granted` afterwards is normal: the API
   declares no scopes and the server requires none.

4. If the named client has a **`tpc_` Client ID**, it is a throwaway created by
   dynamic registration and it will be replaced by a new one on the next
   connect — fixing the permission on it buys one session. Do A, then go to
   Phase 3, which makes the connector use a stable client instead.

### B. Anything naming a limit, quota, or "too many applications" — or Phase 1 showed the limit banner

The tenant caps third-party applications and each connect attempt leaves one
behind. Cleanup is already scripted: follow
`docs/deploy/chrome-agent-auth0-cleanup-task.md` Phase 2, then return here.
Deleting applications is irreversible — confirm with the owner first.

### C. `Callback URL mismatch` (usually a specific Auth0 page, but check)

Applications → the named application → Settings → **Allowed Callback URLs**.
The connector dialog shows the exact callback it expects — prefer that value
over these. Known ones:

```
https://claude.ai/api/mcp/auth_callback, https://claude.com/api/mcp/auth_callback
```

A phone client may use a callback that is not in the list even though desktop
works. If the dialog shows a third URL, add it and report which one it was.

### D. The description names a Rule, Action, Flow or Hook

Auth0 → **Actions → Flows → Login**. An Action that throws renders exactly this
generic page. Report which Action is in the flow and the error text; **do not
disable or edit an Action** without the owner's explicit yes — it may be
carrying a deliberate rule.

### E. The description names the connection, or "no sign-in method"

Check `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/connections/database`
→ `Username-Password-Authentication`:
- **Applications tab** — the failing application must be enabled on it.
- **Disable Sign Ups** — report whether it is on. With it on, a person who has
  no account yet sees a login with no way to register. This is an open question
  the owner has been meaning to check; report the state, do not change it.

---

## Phase 3 — Give the connector a stable client (do this if Phase 2 was A with a `tpc_` client, or if the fix keeps evaporating)

Dynamic registration mints a fresh client on every connect, and a fresh client
has no API Access permission — so the error returns after each reconnect. A
manual client keeps its settings.

An application named `OneiroScope Connector (manual)` already exists in this
tenant. **Check it before creating another one** — a duplicate adds to the very
quota that Phase 2B is about.

On that application verify, in this order:

1. Settings → **Allowed Callback URLs** contains what the connector dialog
   shows (see Phase 2C).
2. Advanced Settings → **Grant Types**: exactly `Authorization Code` and
   `Refresh Token` enabled, **everything else off**. Auth0 ticks these
   generously by default; a previous agent left `Implicit` and
   `Client Credentials` on and called it "for flexibility". It is the opposite:
   Implicit was dropped from OAuth 2.1 and puts the token in the address bar,
   where it lands in history and logs; Client Credentials on a client with a
   user callback means a leaked secret yields tokens with no user at all.
3. Tab **API Access** → `OneiroScope MCP` → **User-delegated Access** enabled
   (the table in Phase 2A).
4. APIs → `OneiroScope MCP` → Settings → **Allow Offline Access — ON**. This
   one lives on the API, not on the application, which is why it gets missed.
   Without it Auth0 issues no refresh token and the connector drops "by itself"
   after an hour or two.

Then, in Claude → Settings → Connectors → OneiroScope → **Advanced settings**,
put the **Client ID** and **Client Secret** of that application in.

- Copy the Client ID with the copy button and hand it over.
- **The Secret is the owner's to handle.** Do not open it, display it,
  screenshot it or paste it. Tell the owner where it is and let them copy it
  themselves.

---

## Phase 4 — Verify, and be honest about the boundary

A saved form is not a working connector. You can confirm the dashboard state;
you **cannot** confirm the connection — that needs the owner.

1. Ask the owner to remove and re-add the connector, then complete the Auth0
   login themselves.
2. Ask them to use the **same sign-in method as before** (password vs Google).
   A different method produces a different Auth0 `user_id`, which will not
   match `STAFF_ACCOUNTS` in the backend, and the natal chart will keep
   answering `entitlement_required`.
3. Ask them to open the connector's tool list and compare it against the live
   registry at
   `https://oneiroscope-backend.onrender.com/connect/diagnostics` → `tools.names`.
   Compare against that page, not against a number in this file: a list showing
   `transit_arc`, `transit_meaning`, `electional_day`, `list_event_types` or
   `horoscope_report` is a **cached client schema**, not a server problem —
   remove and re-add the connector again.
4. Ask them to run one tool. `dream_series_stats` is the safest: read-only,
   writes nothing, consumes no free-tier grant, and its answer distinguishes
   the two states directly — a real `user_id` means the OAuth subject arrived,
   `"status": "sign_in_required"` means it did not.

**Final report:** the five log fields from Phase 0 verbatim, which branch of
Phase 2 applied, exactly what was changed (with Client IDs pasted, not
retyped), whether a manual or dynamic client is now in use, and the outcome of
step 4 in the owner's own words.

If any phase leaves you unsure, stop and report. Every wrong turn in this
tenant so far came from acting on a plausible reading instead of the log line.
