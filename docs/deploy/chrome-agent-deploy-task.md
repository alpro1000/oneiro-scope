# Task for Claude-for-Chrome: split deploy (backend on Render, frontend on Vercel)

Hand this whole file to the browser agent. It drives the **Render** and
**Vercel** dashboards in a browser where the owner is already logged in.
Repo: `alpro1000/oneiro-scope`. Code is already prepared (see
`docs/deploy/vercel-frontend.md`, `render.yaml`, `frontend/vercel.json`).

## Goal
Get the FastAPI backend + Postgres + Redis running on **Render**, and the
Next.js frontend running on **Vercel**, wired to each other, with CORS closed.

## Guardrails (read first, obey strictly)
- **Never type or reveal secrets** (API keys, DB passwords, SECRET_KEY). Where
  a secret value is required and unknown, STOP and ask the owner for it, or
  leave the field and flag it. Do not paste secrets into chat.
- **Confirm before anything destructive**: deleting a service, deleting a
  project, removing a database, changing a plan that costs money. Describe what
  you're about to delete and wait for a "yes".
- **Do not touch unrelated projects/services** — only the two named below.
- **Never guess a URL or domain.** Use the exact URLs the dashboards show you;
  carry them forward verbatim.
- If a step's UI differs from this script, describe what you see and ask rather
  than clicking blindly.
- Work in the exact phase order below — the ordering resolves a
  backend↔frontend circular dependency. Do not reorder.
- After each phase, post a short status line (what you did + the URL produced).

## Precondition (confirm with owner)
The prepared config lives on branch `claude/fandorin-portrait-generation-d422my`.
For Render's Blueprint and Vercel's import to use it, it should be merged to
`main` first. Ask the owner: "Is the split-deploy PR merged to main, or should
I deploy from the branch?" Proceed per their answer.

---

## Phase A — Backend on Render (do this FIRST)
1. Go to https://dashboard.render.com.
2. If a Blueprint for this repo exists: open it → **Manual Sync / Apply** so it
   picks up the updated `render.yaml` (which now defines only
   `oneiroscope-backend`, `oneiroscope-postgres`, `oneiroscope-redis` — the
   frontend web service was removed).
   - If Render proposes to **delete** the old `oneiroscope-frontend` service,
     that is expected (it moved to Vercel) — but CONFIRM with the owner before
     approving the delete.
   - If no Blueprint exists: create one → **New → Blueprint** → pick the repo
     and correct branch.
3. Open the `oneiroscope-backend` service → **Environment**. Verify:
   - `ENVIRONMENT = production`
   - `DATABASE_URL`, `DATABASE_URL_SYNC`, `REDIS_URL` are wired from the DB/Redis.
   - Secret-bearing keys (`SECRET_KEY`, `GEONAMES_USERNAME`, `*_API_KEY`) —
     if any are empty and the owner wants that provider, ASK the owner for the
     value; otherwise leave empty and note it.
   - Leave `ALLOWED_ORIGINS` empty for now (set in Phase C).
4. Trigger a deploy. Wait for it to go **Live**. Open the service URL shown at
   the top, e.g. `https://oneiroscope-backend.onrender.com`.
5. Verify: visit `<backend-url>/health` → expect HTTP 200 / a small JSON.
   Note: on the free plan the first request after idle can take 30–50s.
6. **Record `BACKEND_URL`** (the exact https URL) and report it. It is the
   input to every step in Phase B.

## Phase B — Frontend on Vercel
1. Go to https://vercel.com/dashboard → **Add New… → Project**.
2. Import the GitHub repo `alpro1000/oneiro-scope` (authorize if asked).
3. **Configure Project → Root Directory: `frontend`** (critical — it's a
   monorepo; `frontend/vercel.json` supplies framework + commands). Framework
   should auto-detect as **Next.js**.
4. **Environment Variables** — add each of these for **Production AND Preview**.
   Set every `*_API_URL` value to the `BACKEND_URL` from Phase A:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `BACKEND_URL` |
   | `NEXT_PUBLIC_LUNAR_API_URL` | `BACKEND_URL` |
   | `ASTROLOGY_API_URL` | `BACKEND_URL` |
   | `DREAMS_API_URL` | `BACKEND_URL` |
   | `LUNAR_API_URL` | `BACKEND_URL` |
   | `AUTH_API_URL` | `BACKEND_URL` |
   | `BILLING_API_URL` | `BACKEND_URL` |
   | `LUNAR_DEFAULT_TZ` | `Europe/Moscow` |
   | `SERVER_ACTION_ORIGINS` | (leave blank for now; fill in step 7) |

5. Click **Deploy**. Wait for the build to succeed.
6. **Record `FRONTEND_URL`** (the production URL Vercel assigns, e.g.
   `https://oneiroscope.vercel.app`) and report it.
7. Set `SERVER_ACTION_ORIGINS` to the **host only** of `FRONTEND_URL`
   (e.g. `oneiroscope.vercel.app`, no `https://`). Because `NEXT_PUBLIC_*` and
   this value are baked at build time, **redeploy** the frontend after setting
   it (Deployments → latest → Redeploy).

## Phase C — Close the CORS loop on Render
1. Back in Render → `oneiroscope-backend` → **Environment**.
2. Set `ALLOWED_ORIGINS` = `FRONTEND_URL` **with scheme**, e.g.
   `https://oneiroscope.vercel.app`. (If the owner has a custom domain too, add
   it comma-separated: `https://oneiroscope.vercel.app,https://www.example.com`.)
3. Save → this triggers a backend redeploy. Wait for **Live**.

## Verification (report pass/fail for each)
1. Open `FRONTEND_URL` in the browser. Load the calendar / astrology / dreams
   pages. Confirm data appears.
2. Open DevTools → Network. Confirm API requests go to `BACKEND_URL` and return
   200, with **no CORS errors** in the console.
3. Confirm **no** request targets `localhost` (if one does, a `NEXT_PUBLIC_*`
   var was missing at build time — re-check Phase B step 4 and redeploy).
4. `GET <BACKEND_URL>/health` → 200.

## Final report to the owner
- `BACKEND_URL` and `FRONTEND_URL`.
- Whether the old Render frontend service was deleted (and that you confirmed).
- Any env var left empty because it needed a secret (list the names).
- Verification results (the 4 checks above), with any console errors quoted.
- Anything you had to ask about or that differed from this script.
