# Deploy: frontend on Vercel, backend on Render

Split architecture:

- **Vercel** — the Next.js 14 frontend (`frontend/`). Ideal host for Next.js.
- **Render** — backend (FastAPI + Swiss Ephemeris), Postgres, Redis. Kept on
  Render because Celery workers + the embedded MCP server + heavy binary deps
  (`pyswisseph`, `pandas`) need a persistent process, not serverless functions.

`render.yaml` no longer defines a frontend web service; it hosts backend +
Postgres + Redis only.

## The one gotcha: a cross-platform circular dependency

The backend needs the frontend origin for CORS (`ALLOWED_ORIGINS`); the
frontend needs the backend URL for its API calls. They live on different
platforms now, so bootstrap in this order:

### 1. Backend on Render (first — it has no dependency on the frontend URL)
- Deploy from `render.yaml` (Blueprint) or the existing service.
- Note its public URL, e.g. `https://oneiroscope-backend.onrender.com`.
- `ALLOWED_ORIGINS` is `sync: false` — leave it for now, set it in step 3.
- Confirm `ENVIRONMENT=production`.

### 2. Frontend on Vercel
- New Project → import `alpro1000/oneiro-scope`.
- **Root Directory: `frontend`** (this is the key setting for the monorepo;
  `frontend/vercel.json` supplies framework + build/install commands).
- Add Environment Variables (all → Production + Preview), each pointing at the
  backend URL from step 1:

  | Variable | Value |
  |---|---|
  | `NEXT_PUBLIC_API_URL` | `https://oneiroscope-backend.onrender.com` |
  | `NEXT_PUBLIC_LUNAR_API_URL` | `https://oneiroscope-backend.onrender.com` |
  | `ASTROLOGY_API_URL` | same backend URL |
  | `DREAMS_API_URL` | same backend URL |
  | `LUNAR_API_URL` | same backend URL |
  | `AUTH_API_URL` | same backend URL |
  | `BILLING_API_URL` | same backend URL |
  | `LUNAR_DEFAULT_TZ` | `Europe/Moscow` (or `UTC`) |
  | `SERVER_ACTION_ORIGINS` | your Vercel domain, host only, e.g. `oneiroscope.vercel.app` |

  `NEXT_PUBLIC_*` are baked at build time — after changing them, **redeploy**
  the frontend (Vercel does this on the next push; or trigger manually).
- Deploy → note the Vercel URL, e.g. `https://oneiroscope.vercel.app`.

### 3. Close the loop on Render
- Set backend `ALLOWED_ORIGINS` to the Vercel URL(s), **with scheme**,
  comma-separated: `https://oneiroscope.vercel.app`
  (add `https://www.<custom-domain>` too once a custom domain is attached).
- Redeploy the backend so CORS picks it up.

## Custom domain (optional)
Attach it in Vercel (frontend) and add its `https://` origin to the backend
`ALLOWED_ORIGINS` and to `SERVER_ACTION_ORIGINS` (host only).

## Sanity checks
- Browser: open the Vercel URL, confirm calendar/astrology/dream pages load
  data (network tab hits the Render backend, no CORS error).
- `curl https://<backend>/health` → 200.
- No request in the browser points at `localhost` (that means a `NEXT_PUBLIC_*`
  wasn't set before the build — set it and redeploy).
