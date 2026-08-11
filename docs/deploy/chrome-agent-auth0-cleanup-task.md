# Task for Claude-for-Chrome: clean up stale Auth0 clients, reconnect

Hand this whole file to the browser agent. It drives the Auth0 dashboard in a
browser where the owner is already logged in.

Tenant: `dev-u22itgv3h8ew1sgz.eu.auth0.com`.
Backend: `https://oneiroscope-backend.onrender.com`.

## Situation

Adding the OneiroScope connector in Claude fails with **"Couldn't register
with OneiroScope's sign-in service"**.

The cause is NOT that dynamic registration is broken — it demonstrably works.
The tenant's application list holds **six third-party clients that dynamic
registration created** (five named `Claude`, one named `ChatGPT`, all with
Client IDs starting `tpc_`). Every connect/disconnect cycle left one behind
until the tenant hit its cap on third-party applications, and new
registrations now fail.

So this task is cleanup, not reconfiguration.

## Guardrails (read first, obey strictly)

- **Never type, paste, echo or screenshot a Client Secret**, a signing key, or
  a Management API token. Client *IDs* are fine — they are public identifiers.
- **Delete ONLY the applications named in Phase 2.** Deleting an application
  is irreversible. If a row does not match the list exactly — different name,
  different type, no `tpc_` prefix — leave it and report it.
- **Never delete `API Explorer Application`.** It is Auth0's own Management
  API client; removing it breaks the tenant's admin tooling.
- **Never delete the API** (Applications → APIs → `OneiroScope MCP`). That is
  the resource the tokens are issued for; without it every login stops working.
- Do not change plans, enable paid features, or touch other tenants.
- After each phase, post a short status line.
- **Navigate by URL, never by hunting the sidebar.** A browser agent once
  burned 68 steps scrolling Auth0's menus to reach one toggle and died of
  context overflow mid-task. Auth0's dashboard URLs are stable — use them:
  - Applications: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/applications`
  - APIs: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/apis`
  - Database connections: `https://manage.auth0.com/dashboard/eu/dev-u22itgv3h8ew1sgz/connections/database`
  Within a page, use the search box rather than scrolling.
- **NEVER transcribe an identifier — use the copy button.** Not Client IDs,
  not `user_id`s, not connection ids. This cost three separate debugging
  sessions:
  - an Auth0 `user_id` came back two characters short;
  - `tpc_` client ids in a deletion report drifted by a character each;
  - a Client ID read off a screenshot turned capital `I` into digit `1`, and
    Auth0 answered `Unknown client` for an hour while every setting around it
    was already correct.
  Auth0 renders IDs in a font where `I`/`1`, `O`/`0` and `l`/`I` are barely
  distinguishable, and a screenshot cannot be proofread. Every ID field in the
  dashboard has a copy icon next to it. Use it, paste it, and if the value must
  reach a human, tell them to copy it themselves rather than reading yours.

- **One phase per run.** These phases are independent; finishing one and
  reporting beats attempting all of them and losing the transcript.

## Phase 0 — Inventory (no changes)

1. Auth0 → **Applications → Applications**.
2. List every application with: **name, type, Client ID prefix, and whether it
   carries the THIRD-PARTY badge**.
3. Report the list. Expected shape, from the owner's screenshot:

   | Name | Type | Badge | Verdict |
   |---|---|---|---|
   | API Explorer Application | Machine to Machine | — | **KEEP** — Auth0 admin tooling |
   | ChatGPT | Generic | THIRD-PARTY | delete (Phase 2) |
   | Claude ×5 | Generic | THIRD-PARTY | delete (Phase 2) |
   | Claude MCP Connector | Native | — | **KEEP for now** — see Phase 3 |
   | Default App | Generic | — | KEEP — Auth0's default, harmless |
   | OneiroScope MCP (Test Application) | Machine to Machine | — | KEEP — created with the API |

4. If the real list differs from this table, **stop and report** rather than
   improvising.

## Phase 1 — Confirm the diagnosis (no changes)

Open:

```
https://oneiroscope-backend.onrender.com/connect/diagnostics?probe=1
```

Report the `dcr_advertised` row verbatim. `?probe=1` sends a deliberately
invalid registration (empty body — it cannot create a client) and reads the
status:

- **400 / 422** → registration is open. Confirms the quota diagnosis: the
  endpoint accepts requests, the tenant just has no room for another client.
- **401 / 403** → registration really is refused. Then the quota theory is
  wrong; report it and stop before deleting anything.

## Phase 2 — Delete the stale dynamic clients

Only rows that are **Generic + THIRD-PARTY badge + Client ID starting
`tpc_`**. These are disposable by design: dynamic registration recreates one
on the next connect.

1. All five applications named **`Claude`**.
2. The application named **`ChatGPT`** — unless the owner says they are
   actively using a ChatGPT connector right now. Ask if unsure.

**Verify on the page, not from a list.** All the Claude rows share the same
name, and Auth0's delete dialog asks you to type the application NAME — so the
confirmation step checks nothing that distinguishes them. Before opening
Danger Zone, confirm on the application's own page that it carries the
THIRD-PARTY badge and a `tpc_` Client ID. Client IDs transcribed into a report
drift by a character or two; the screen is the source of truth.

Wait for the tenant's "approaching its available applications limit" banner to
disappear before moving on. While it is still showing there may be no room for
a new registration, and a failed connect leaves yet another dead client — the
exact loop that produced six of them.

For each: **⋯ menu → Delete** (or open the app → Settings → Danger Zone →
Delete). Confirm the dialog. Report each deletion by Client ID.

Expected result: six deletions, and the only remaining Claude-related rows are
`Claude MCP Connector` (Native) plus whatever Phase 0 flagged as KEEP.

## Phase 3 — Reconnect

1. In Claude: **Settings → Connectors → OneiroScope → remove it** if it is
   still listed. Claude may hold credentials for a client that no longer
   exists.
2. **Add custom connector**:
   - Name: `OneiroScope`
   - Remote MCP server URL: `https://oneiroscope-backend.onrender.com/mcp`
   - **Advanced settings: leave OAuth Client ID and Secret EMPTY.** Dynamic
     registration will create a fresh client now that there is room.
3. Click **Add** / **Connect** → an Auth0 login opens.
4. **Tell the owner to complete the login themselves, and to use the SAME
   sign-in method as before** (password vs Google). A different method creates
   a different Auth0 `user_id`, which will not match the one configured in the
   backend's `STAFF_ACCOUNTS`, and the natal chart will keep answering
   `entitlement_required`.
5. If registration still fails after the cleanup, do NOT retry in a loop —
   each attempt may leave another client. Report and stop; the fallback is
   Phase 4.

## Phase 4 — Fallback, only if Phase 3 failed

Skip DCR entirely by giving the connector a client of its own.

1. Auth0 → **Applications → Create Application** → **Regular Web Application**.
   Name it `OneiroScope Connector (manual)`.
2. Settings → **Allowed Callback URLs**:
   ```
   https://claude.ai/api/mcp/auth_callback, https://claude.com/api/mcp/auth_callback
   ```
   The connector's own error dialog shows the exact callback it expects —
   prefer that value if it differs.
3. **Advanced Settings → Grant Types**: enable `Authorization Code` and
   `Refresh Token`.
4. Copy the **Client ID**. The **Secret** must be handled by the owner —
   do not display or transcribe it; ask them to paste it themselves.
5. In Claude → Add custom connector → Advanced settings → paste both.

## Phase 5 — Verify and report

1. In Claude, open the connector's tool list. Expect **19 tools**. If it shows
   `transit_arc`, `transit_meaning`, `electional_day`, `list_event_types` or
   `horoscope_report`, the connector is showing a cached schema — remove and
   re-add it again.
2. Ask the owner to run a natal chart for `01.07.1977, 22:30, Запорожье`.
   - Success → done.
   - `entitlement_required` → ask them for the **`authenticated_as`** field in
     that response. It names the exact OAuth subject they authenticated as,
     which is the value that must appear in the backend's `STAFF_ACCOUNTS`.
     Report it back; do not guess it from the Auth0 user list.
3. Final report: which Client IDs were deleted, whether reconnection used
   dynamic registration or a manual client, the tool count, and the natal
   chart outcome.

## Why this will recur

Every connect/disconnect cycle leaves one dynamically registered client
behind — Auth0 does not garbage-collect them, and the connector does not
unregister on removal. Six accumulated before the tenant ran out of room.
Expect to run this cleanup again after a few reconnection cycles, and check
the application list first whenever a connector suddenly refuses to register.
