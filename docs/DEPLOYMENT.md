# OneiroScope Deployment Guide

Production checklist for a solo founder in the EU running the service end
to end. The stack is intentionally light: **Render** for the backend
(Python + Postgres + Redis), **Vercel** for the Next.js frontend,
**Lemon Squeezy** as Merchant of Record (no юр.лицо needed), **Resend**
for transactional email, and **Capacitor** to wrap the same Next.js
build into iOS / Android shells.

Estimated time from clean repo to live service: **2-3 days**. From there
to App Store / Play Store approval: **1-3 weeks** (Apple review queue).

---

## 0. Pre-deploy decisions (resolved 2026-06-14)

- **Merchant of Record:** Lemon Squeezy. They handle EU VAT (one-stop
  shop), US sales tax, KYC, chargebacks. You operate as a freelancer
  receiving payouts to your personal SEPA account.
- **No legal entity required** — Lemon Squeezy is the seller of record.
  Russian customers are charged in EUR through Lemon's card processor.
- **Render** for backend + Postgres + Redis (one bill, predictable).
- **Vercel** for the Next.js frontend (free tier handles MVP traffic).
- **Resend** for transactional email ($20/mo).
- **DeepL Pro API** for UI translation ($30/mo); native speakers review
  `lunar_tables.json` + `symbols.json` (psychology / astrology context).

---

## 1. Backend — Render

### 1.1 Create services

`render.yaml` already declares:
- `oneiroscope-backend` (Python web service, free or $7/mo)
- `oneiroscope-postgres` (managed Postgres, free 90 days then $7/mo)
- `oneiroscope-redis` (free 25 MB)
- `oneiroscope-frontend` (Node) — **leave declared but unused** if you
  prefer Vercel.

```bash
# From the Render Dashboard:
# 1. New → Blueprint → connect this repo
# 2. Render reads render.yaml and provisions all services
```

### 1.2 Environment variables (Render dashboard → Environment)

```env
# Core
ENVIRONMENT=production
SECRET_KEY=<64 random bytes — generate once, never commit>
DATABASE_URL=<auto-filled by Render from oneiroscope-postgres>
DATABASE_URL_SYNC=<auto-filled>
REDIS_URL=<auto-filled by Render from oneiroscope-redis>
ALLOWED_ORIGINS=https://oneiroscope.app,https://www.oneiroscope.app,https://app.oneiroscope.app

# LLM providers — at least one. Cheap-to-expensive order:
GROQ_API_KEY=gsk_...          # FREE tier, recommended primary
GEMINI_API_KEY=...            # $0.075/1M tokens, optional fallback
ANTHROPIC_API_KEY=sk-ant-...  # For ADK orchestrator (claude-opus-4-7)

# Geo
GEONAMES_USERNAME=alpro1000
LUNAR_DEFAULT_TZ=Europe/Berlin

# Lemon Squeezy (set up in step 3 below)
LEMON_API_KEY=...
LEMON_STORE_ID=...
LEMON_WEBHOOK_SECRET=...
LEMON_VARIANT_PREMIUM=...
LEMON_VARIANT_PRO=...
LEMON_VARIANT_NATAL_PDF=...
LEMON_VARIANT_YEARLY=...

# Email
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=OneiroScope <noreply@oneiroscope.app>

# Swiss Ephemeris (optional — falls back to Moshier analytic)
SE_EPHE_PATH=/opt/render/project/src/ephe
```

### 1.3 Run database migrations (first deploy only)

`Render shell → backend service`:

```bash
# Alembic migration setup — Phase 6 added new columns; one-time
# initial bootstrap (after that use proper Alembic):
python -c "
import asyncio
from backend.core.database import init_db
asyncio.run(init_db())
"
```

For ongoing schema evolution use Alembic (`alembic upgrade head` in the
Render predeploy step — left as a TODO for the team's first migration).

### 1.4 Smoke check

```bash
curl https://oneiroscope-backend.onrender.com/health
# {"status":"healthy","service":"OneiroScope API","version":"...","ephemeris":{...}}

curl -X POST https://oneiroscope-backend.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"hunter2hunter2","language":"en"}'
# Should return {"access_token":"...", "user_id":"...", ...}
```

---

## 2. Frontend — Vercel

```bash
# 1. Vercel CLI / Dashboard: import the GitHub repo
# 2. Set the root directory to `frontend/`
# 3. Framework preset: Next.js (auto-detected)
# 4. Environment variables:
NEXT_PUBLIC_API_URL=https://oneiroscope-backend.onrender.com
NEXT_PUBLIC_LUNAR_API_URL=https://oneiroscope-backend.onrender.com
NEXT_PUBLIC_LEMON_STORE_NAME=oneiroscope  # for direct checkout links
LUNAR_DEFAULT_TZ=UTC
```

### 2.1 Custom domain

1. Vercel → Domains → add `oneiroscope.app` and `www.oneiroscope.app`.
2. DNS → CNAME `www` → `cname.vercel-dns.com`; A `@` → `76.76.21.21`.
3. After SSL provisions (5-30 minutes), set
   `NEXT_PUBLIC_API_URL=https://api.oneiroscope.app` and CNAME
   `api` → Render service URL.
4. Update Render `ALLOWED_ORIGINS` to include both domains.

---

## 3. Lemon Squeezy (Merchant of Record)

### 3.1 Account setup

1. Sign up at https://www.lemonsqueezy.com (no business required).
2. Provide personal SEPA bank details for payouts (EU SEPA, US ACH, or
   Wise multi-currency).
3. Verify email + 2FA on.

### 3.2 Create the store + products

In the Lemon dashboard:

1. **Store** → create "OneiroScope". Note the **store ID** (numeric).
2. **Products** → New Product → Subscription:
   - **Premium Monthly**: $9.99 / mo, EUR/USD, 7-day free trial
     (optional). Create a **variant** — note its ID.
   - **Pro Monthly (BYOK)**: $5.99 / mo. Variant ID.
3. **Products** → New Product → Single Payment:
   - **Detailed Natal PDF**: $19. Variant ID.
   - **Yearly Forecast**: $29. Variant ID.

Copy each variant ID into Render env vars (`LEMON_VARIANT_PREMIUM` etc.).

### 3.3 Webhook setup

1. **Settings → Webhooks → New webhook**:
   - URL: `https://api.oneiroscope.app/api/v1/billing/webhook`
   - Signing secret: generate one, copy to Render `LEMON_WEBHOOK_SECRET`.
   - Events: subscribe to all `subscription_*` and `order_created`.
2. Test the webhook delivery: Lemon dashboard → Webhooks → Send test.
   Check Render logs for `Lemon webhook signature verification` success.

### 3.4 API key

**Settings → API** → create a server key. Render
`LEMON_API_KEY=lsq_<key>`.

### 3.5 Tax & VAT

Lemon Squeezy auto-collects EU VAT (one-stop shop), US sales tax, GST.
You will receive a monthly tax breakdown for your accountant. **No
действий с твоей стороны** для compliance.

### 3.6 Russian customers

Lemon accepts most Russian-issued cards as long as the card supports
international payments. If you want to maximize RU conversion, also
mention **crypto** in the checkout description — Lemon supports BTC/ETH
via Coinbase Commerce.

---

## 4. Resend (transactional email)

1. Sign up at https://resend.com, free tier = 100 emails/day, 3k/mo.
2. Verify your domain (DNS records — SPF, DKIM, DMARC).
3. Create an API key → Render `RESEND_API_KEY`.
4. Set `RESEND_FROM_EMAIL=OneiroScope <noreply@oneiroscope.app>`.

---

## 5. Domain + DNS summary

| Subdomain | Target | Provider |
|---|---|---|
| `oneiroscope.app` | A → Vercel | Vercel |
| `www.oneiroscope.app` | CNAME → Vercel | Vercel |
| `api.oneiroscope.app` | CNAME → Render | Render |
| `noreply@oneiroscope.app` | MX/SPF/DKIM → Resend | Resend |

---

## 6. Monitoring

- **Render** — built-in logs and metrics; set up email alerts on
  deploys + 5xx rate.
- **Sentry** — already in `backend/requirements.txt`. Add
  `SENTRY_DSN=...` to Render env to start receiving error events.
- **Uptime** — Render Health check pings `/health` every 30s; set up
  a free external monitor (BetterStack, UptimeRobot) for redundancy.
- **Cost** — `cost_tracker` records per-provider per-agent LLM spend
  to Redis; expose `/api/v1/admin/cost` (TODO — Phase 6.G) once auth
  has admin role distinction.

---

## 7. Recurring ops

- **Daily**: Render auto-deploys on `main` merge; CI gates with
  `mcp-smoke.yml` (14 tests). The pre-existing `build-and-validate`
  job is documented in `§5` of `docs/soul.md` as a known issue.
- **Weekly**: review Lemon dashboard for chargebacks / refunds; review
  Resend for bounced emails.
- **Monthly**: review Render usage (resize if cold start matters), pull
  Lemon tax report for accountant.

---

## 8. Costs (steady state, MVP traffic ≤ 1k MAU)

| Item | Cost |
|---|---|
| Render backend | $7/mo (free for 750h then $7) |
| Render Postgres | $7/mo (free 90 days) |
| Render Redis | Free 25 MB |
| Vercel frontend | Free (Hobby plan) |
| Resend | $20/mo |
| DeepL Pro | $30/mo |
| Lemon Squeezy | Free (5% + 50¢ per transaction) |
| Domain | $12/yr |
| **Total** | **≈ $65/mo** + transaction fees on sales |

Mobile app stores: $99/yr Apple Developer + $25 one-time Google Play.

---

## 9. Mobile app deployment

See `docs/MOBILE.md` for the Capacitor wrap, TestFlight upload, and
Google Play closed track procedure.
