---
name: validate-prod
description: Health-check the OneiroScope production environment — required env vars, ephemeris file presence, LLM provider keys, GeoNames quota indicators. Use when the user asks to "validate prod", "check deploy", or invokes /validate-prod. Reports without modifying state.
---

# /validate-prod — Production environment check

## What this does

Read-only health-check against the current environment. Useful right
after a Render deploy, or before debugging a customer-reported issue.

## Checks

1. **Backend env vars present:**
   - `ENVIRONMENT` (should be `production` on Render)
   - `DATABASE_URL` / `DATABASE_URL_SYNC`
   - `REDIS_URL` (optional but recommended)
   - `SECRET_KEY`
   - `ALLOWED_ORIGINS` (must include the frontend `RENDER_EXTERNAL_URL`
     with scheme)
   - At least one LLM key: `GROQ_API_KEY` / `GEMINI_API_KEY` /
     `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `TOGETHER_API_KEY`
   - `GEONAMES_USERNAME`
   - `LUNAR_DEFAULT_TZ`

2. **Ephemeris files** — check `SE_EPHE_PATH` env; if set, list the
   `.se1` files present. If not set or empty, warn that we're using
   Moshier analytic (still correct, just lower precision).

3. **Backend reachability** — `GET /health` against `NEXT_PUBLIC_API_URL`
   (or local backend if running locally). Report HTTP status and
   `ephemeris_engine` from the response.

4. **Frontend reachability** — if `NEXT_PUBLIC_API_URL` is a remote URL,
   curl the frontend root and verify 200.

5. **Lunar smoke** — call `mcp__oneiro__get_lunar_day` for today and
   verify provenance.

## Output format

Structured table:

```
| Check                | Status | Detail                         |
|----------------------|--------|--------------------------------|
| ENVIRONMENT          | ✅     | production                     |
| DATABASE_URL         | ✅     | postgres://...                 |
| ALLOWED_ORIGINS      | 🔴     | missing scheme, set to *       |
| GROQ_API_KEY         | ✅     | gsk_*** (loaded)               |
| Ephemeris files      | ⚠️     | SE_EPHE_PATH unset; MOSEPH     |
| /health              | ✅     | 200, ephemeris=MOSEPH          |
| Lunar smoke          | ✅     | day=18, phase=waning_gibbous   |
```

## Behavior

- Never print secret values. Show first 4 chars + `***`.
- Never modify env files or push fixes — only report.
- If running locally and `NEXT_PUBLIC_API_URL=localhost:8000`, skip the
  reachability checks with a ⚠️ note.
