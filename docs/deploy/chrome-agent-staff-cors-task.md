# Task for Claude-for-Chrome: STAFF_ACCOUNTS + CORS + DCR on the live deployment

Hand this whole file to the browser agent. It drives dashboards in a browser
where the owner is already logged in. Repo: `alpro1000/oneiro-scope`.

## Goal

Three settings that live only in dashboards, so no deploy can carry them:

1. **`STAFF_ACCOUNTS`** — the owner cannot use their own product. The free tier
   grants one natal chart for life and applies to the owner exactly as to a
   customer, so every test of the paid path answers `entitlement_required`.
   Naming the owner's account lifts it to the PRO tier.
2. **`ALLOWED_ORIGINS`** — verify it, do not assume. It was `sync: false` for
   months, i.e. it existed only as a prompt in the dashboard and was never set,
   and the whole Vercel frontend was refused by CORS. The blueprint now carries
   a value, but Render applies `render.yaml` on blueprint sync, **not on every
   deploy** — so it may still be wrong.
3. **Dynamic Client Registration in Auth0** — Claude registers itself as an
   OAuth client before it can send anyone to log in. Auth0 ships with that flag
   OFF, and without it the connector dies with "Failed to start MCP
   authorization" while everything on our side is correct.

## Guardrails (read first, obey strictly)

- **Never type, paste, echo or screenshot a secret.** `SECRET_KEY`, database
  URLs, API keys, Auth0 client secrets, management tokens. This task needs
  none of them. If a step seems to require one, STOP and ask the owner.
- **`STAFF_ACCOUNTS` is not a secret, but it is personal data.** It is fine to
  type into the Render form. Do not post the full `user_id` into any public
  place; reporting it back to the owner in chat is fine.
- **Change only the three things named here.** Do not edit, reorder or delete
  any other environment variable, even one that looks wrong. Report anything
  suspicious instead.
- **Do not change plans, add paid features, or delete anything.** If a step
  looks billable, describe it and wait for an explicit "yes".
- **Never invent an ID, tenant name or URL.** Copy exactly what the dashboard
  shows and carry it forward verbatim.
- If the UI does not match this script, describe what you see and ask. Both
  dashboards get reorganised regularly.
- After each phase, post a short status line: what you did, what you read.

## What the owner must supply

- Access to the Render dashboard (service **`oneiroscope-backend`**).
- Access to the Auth0 tenant used by the connector.

---

## Phase 0 — Read the current state (no changes)

1. Open `https://oneiroscope-backend.onrender.com/connect/diagnostics`.
   This is a self-check the server serves about itself. Report the **whole**
   JSON body.
2. From that body, report these four things explicitly, because the later
   phases are judged against them:
   - the check `browser_origins` → `ok` and `detail`;
   - the check `dcr_advertised` → `ok` and `detail` (absent if OAuth is not
     configured at all — say so);
   - `tools.count` and `tools.names`;
   - `config.auth_issuer`.
3. If the page 404s or has no `tools` field, the running deployment predates
   this task: go to Render → `oneiroscope-backend` → **Manual Deploy → Deploy
   latest commit**, wait for **Live**, then retry step 1.

**Report before continuing.** If `browser_origins` and `dcr_advertised` are
both already `ok`, Phases 2 and 3 are no-ops — say so and skip them.

---

## Phase 1 — Find the owner's OAuth subject (Auth0)

The owner's account may have **no email** in our database: when someone
connects through Claude/ChatGPT, the record is created from the OAuth token's
subject, and Auth0 does not always release an email claim. So matching on
email alone can silently fail. We supply both.

1. Go to `https://manage.auth0.com` → the tenant shown as `config.auth_issuer`
   in Phase 0 (e.g. `dev-ab12cd34.eu.auth0.com`). If several tenants exist,
   pick the one whose domain matches that issuer — do not guess.
2. **User Management → Users**. Find the owner's user. It is normally the only
   human user, or the one with `alpro1000@gmail.com`.
3. Open it and copy the **`user_id`** field verbatim, **including the prefix
   before the vertical bar**: it looks like `auth0|68f3…` or
   `google-oauth2|1043…`. The prefix is part of the identifier.
4. If there are **several** users that could be the owner (e.g. one via Google
   and one via username/password), report all of their `user_id` values and
   ask which to use — or propose adding all of them, comma-separated, which is
   safe and correct.
5. If the Users list is empty, the owner has never completed a login through
   the connector. Report that: the email alone will be set in Phase 2 and the
   subject added later.

Report the `user_id` value(s) before continuing.

---

## Phase 2 — Render environment variables

1. `https://dashboard.render.com` → service **`oneiroscope-backend`**
   (the **web** service — not `oneiroscope-postgres`, not `oneiroscope-redis`).
2. Left menu → **Environment**.
3. **`STAFF_ACCOUNTS`** — if the key exists, edit it; otherwise
   **+ Add Environment Variable**:
   - Key: `STAFF_ACCOUNTS`
   - Value: `alpro1000@gmail.com,<user_id from Phase 1>`
   - Example of the shape (do NOT copy this literal id):
     `alpro1000@gmail.com,auth0|68f3a1b2c3d4e5f6a7b8c9d0`
   - Spacing around the comma does not matter; case does not matter.
   - If Phase 1 found no user, set just `alpro1000@gmail.com`.
4. **`ALLOWED_ORIGINS`** — read the current value and report it.
   - If it is missing, empty, or contains only `localhost`, set it to
     `https://oneiroscope.vercel.app`.
   - If it already contains `https://oneiroscope.vercel.app`, **leave it
     alone** — it may also list a custom domain that must not be lost.
   - Values are comma-separated and must include the scheme (`https://`).
5. **Save Changes.** Render redeploys automatically; on the free plan this
   takes roughly 2–5 minutes. Wait for the service to read **Live**.

Report: the value you set for `STAFF_ACCOUNTS` (the email plus how many
subjects), what `ALLOWED_ORIGINS` was before and after, and the deploy status.

---

## Phase 3 — Dynamic Client Registration (Auth0)

Skip if `dcr_advertised` was already `ok` in Phase 0.

1. `https://manage.auth0.com` → same tenant → **Settings** (bottom-left, the
   tenant settings — not an application's settings) → **Advanced** tab.
2. Enable **OIDC Dynamic Application Registration**. Save.
3. Still in tenant settings, check **Default Directory** / the connection
   settings: clients created dynamically must be allowed to use your database
   or social connection, or a self-registered client will exist but be unable
   to log anyone in. If you cannot find this, report what you see rather than
   experimenting.
4. Verify: open
   `https://<tenant-domain>/.well-known/openid-configuration` and confirm the
   JSON contains a `registration_endpoint` field. Report that line.

---

## Phase 4 — Verify, end to end

1. Reload `https://oneiroscope-backend.onrender.com/connect/diagnostics`.
   Report the full JSON again. Expected: `browser_origins` → `ok: true`,
   and `dcr_advertised` → `ok: true` if Phase 3 ran.
2. Open `https://oneiroscope.vercel.app/ru/calendar` and confirm lunar days
   render (this is the CORS path that was broken).
3. Open `https://oneiroscope.vercel.app/ru/astrocartography`, type `Прага`
   into the city field and confirm suggestions appear with coordinates. If it
   says "поиск недоступен", CORS is still wrong — report it.
4. **The staff check cannot be verified from a browser** — it applies to MCP
   calls made under the owner's OAuth identity. Tell the owner to run a natal
   chart from their chat client for their own data
   (`01.07.1977, 22:30, Запорожье`) and report whether
   `entitlement_required` still appears. If it does, the subject in
   `STAFF_ACCOUNTS` is not the one the connector authenticates as — bring back
   the Phase 1 list and we will try the others.

---

## Phase 5 — Report

Post a summary with:

- `STAFF_ACCOUNTS`: set / already correct — and how many identities it names.
- `ALLOWED_ORIGINS`: before → after.
- DCR: enabled / already on / could not find the setting.
- The final `/connect/diagnostics` JSON.
- `tools.count` — expected **19**. If a chat client shows a different number
  or offers tools absent from `tools.names` (`transit_arc`, `transit_meaning`,
  `electional_day`, `list_event_types`, `horoscope_report`), that is the
  client's cached schema, **not** a server fault: the fix is to remove and
  re-add the connector in that client. Say this explicitly in the report — it
  has been misdiagnosed as a server bug three times.
- Anything you saw that this file did not predict.
