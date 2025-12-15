# OneiroScope Repository Audit

## Repo Map
- **Frontend (Next.js 14, App Router)**
  - Pages: `frontend/app/[locale]/...` with calendar SSR entry in `app/[locale]/(calendar)/calendar/page.tsx` (fetches backend lunar API via `getLunarDay`).
  - API proxy: `frontend/app/api/lunar/route.ts` calls backend and returns 502 with mock flag on failure.
  - I18n: `frontend/i18n/request.ts`, `frontend/middleware.ts`; translations in `frontend/messages/*`.
  - Styling: Tailwind via `frontend/tailwind.config.ts`, PostCSS `frontend/postcss.config.js`, global styles `frontend/styles/globals.css`.
  - Clients: `frontend/lib/lunar-server.ts` (SSR) and `frontend/lib/lunar-client.ts` (CSR) build URLs through `frontend/lib/lunar-endpoint.ts`.

- **Backend (FastAPI)**
  - Entry: `backend/app/main.py` mounts routers `/api/v1/lunar`, `/api/v1/astrology`, `/api/v1/dreams`, `/health`.
  - Config: `backend/core/config.py` (env, CORS), `database.py` (async engine), `logging.py`.
  - Lunar engine: `backend/services/lunar/engine.py` (Swiss Ephemeris, provenance) + content tables `backend/services/lunar/content.py` using `backend/data/lunar_tables.json`.
  - Astrology: orchestrator `backend/services/astrology/service.py`, ephemeris wrapper `ephemeris.py`, geocoder `geocoder.py`, interpreter/LLM glue.
  - Dreams: analyzer/service in `backend/services/dreams/*`.
  - API layer: `backend/api/v1/*`.
  - Tests: `backend/tests/*` (currently stale imports to old module layout).

- **Infra**
  - Render blueprint: `render.yaml` (backend web service + frontend web service + Postgres + Redis).
  - Local Compose: `docker-compose.yml` (Postgres + Redis + Redis Commander).
  - CI: `.github/workflows/*.yml` (frontend tests, UI smoke, inventory, setup).

## Findings

### P0 (blockers)
| Issue | Evidence | Impact | Fix | Acceptance Test |
| --- | --- | --- | --- | --- |
| Astrology endpoints await a synchronous geocoder, raising `TypeError: object GeoLocation can't be used in 'await' expression` | `backend/services/astrology/service.py` lines 63-68, 133-138, 179-184 call `await self.geocoder.geocode(...)` but `geocoder.geocode` is sync in `backend/services/astrology/geocoder.py` lines 59-86 | All astrology routes 500 on first geocode (natal chart, horoscope with location, event forecast), blocking feature and QA | Make `Geocoder.geocode` async (wrap sync call in threadpool) or drop `await` and run in executor; add regression test for successful geocode | Hitting POST `/api/v1/astrology/natal-chart` with valid payload returns 201 and JSON body (not 500); unit test exercising service passes |
| Backend tests reference non-existent modules (`backend.services.astrology.engine.*`), causing `ModuleNotFoundError` on `pytest` | `backend/tests/test_astrology_quality.py` imports `backend.services.astrology.engine.aspects` etc. (lines 5-10) while no `engine/` package exists | CI/backend test runs fail immediately, preventing build green status and masking regressions | Update tests to current module paths or replace with new quality checks; align fixtures with `backend/services/astrology/*` | `pytest backend/tests` runs without import errors and asserts pass in CI |

### P1
| Issue | Evidence | Impact | Fix | Acceptance Test |
| --- | --- | --- | --- | --- |
| Render backend service runs in `ENVIRONMENT=development` (config default) leading to auto `init_db()` against production Postgres on startup | `backend/core/config.py` defaults `ENVIRONMENT="development"`; `backend/app/main.py` lines 24-31 auto-call `init_db()` when `ENVIRONMENT == "development"` | On Render, every deploy runs metadata creation with async engine; risk of long startup or schema drift vs Alembic | Set `ENVIRONMENT=production` in Render env vars and guard `init_db` for dev only; document migration path | Render deploy logs show startup without `Initializing database...` and DB schema managed via Alembic |
| CORS origin normalization may double-prefix protocol if env already includes scheme from Render | `backend/core/config.py` lines 16-34: prepends `https://` when origin lacks protocol; Render `RENDER_EXTERNAL_URL` already has `https://` but OK; however ALLOWED_ORIGINS default includes `http://localhost` only | Potential misconfiguration if ALLOWED_ORIGINS set to host without protocol or multiple values; not fatal but risk of SSR fetch failures | Provide explicit example in env docs; sanitize duplicates and ensure Render env sets full URL | OPTIONS preflight from frontend succeeds; manual curl with Origin header returns 200 |

### P2/P3 (tech debt)
| Issue | Evidence | Impact | Fix | Acceptance Test |
| --- | --- | --- | --- | --- |
| Lunar API lacks explicit ephemeris-path validation/alert when Swiss ephemeris files missing | `_resolve_ephe_path` in `backend/services/lunar/engine.py` uses env if present but no logging when defaulting to Moshier | Silent downgrade in precision; provenance shows mode but ops may miss it | Log warning when ephemeris path absent; expose mode in health check | Health endpoint shows ephemeris mode; log entry visible in startup |
| Frontend lunar month load has no retry/backoff; any single backend 502 shows generic error | `frontend/components/LunarWidget.tsx` lines 42-83 catch and show error | UX degradation during transient backend blips | Add retry with limit and surface `source/provenance` to user | Storybook story covers error→retry flow |

## Render/Deploy Checklist
- Backend: ensure `ENVIRONMENT=production`, provide `DATABASE_URL` + `DATABASE_URL_SYNC`, `REDIS_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS` = frontend `RENDER_EXTERNAL_URL` (full https), ephemeris path envs if bundling Swiss files.
- Frontend: build with `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_LUNAR_API_URL` from backend `RENDER_EXTERNAL_URL`; keep `LUNAR_DEFAULT_TZ` set.
- Commands: backend `pip install -r backend/requirements.txt` then `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`; frontend `npm install --include=dev && npm run build`.
- Health paths: `/health`, `/ready`, `/live`.

## Lunar Correctness Checklist
- Endpoint exists at `/api/v1/lunar` and returns varying `lunar_day`/`phase_angle` for different dates (see `backend/tests/test_lunar_endpoint.py`).
- No mock fallback in backend; provenance includes `ephemeris_engine` and hashed ephemeris files when provided (`backend/services/lunar/engine.py`).
- Content tables served from `backend/data/lunar_tables.json` via `get_lunar_day_text`; locale fallback to `en` only when locale missing.

## Security & Env Notes
- SECRET_KEY required for auth but no rotation; store in Render secrets.
- Geocoder currently uses Nominatim without rate limiting keys; consider configured provider credentials.
- LLM keys optional but should be absent in repo (.env example only).

## Roadmap
- **Phase 0 – Build green on Render/CI**: Fix geocoder await bug; repair backend tests to actual modules; set `ENVIRONMENT=production` in Render. *Acceptance:* `pytest backend/tests` passes; Render deploy boots without DB init logs and astrology endpoints respond 2xx.
- **Phase 1 – Lunar correctness / anti-mock**: Add ephemeris-path warning + health exposure; add integration test comparing two dates; add retry in LunarWidget. *Acceptance:* health shows engine mode; UI month table varies per date; tests enforce non-constant lunar_day.
- **Phase 2 – Astrology hardening**: Add strict geocode provenance + rate limits; validate timezone lookup errors; cover orbs/applying-separating tests against current code. *Acceptance:* geocode failures return 400 with codes; aspects tests aligned with actual modules.
- **Phase 3 – QA gates & CI**: Introduce CI job running backend pytest + frontend lint/test; add provenance assertions for lunar responses. *Acceptance:* CI pipeline green across lint/test; regression test ensures `source=backend` and provenance present.

## Next Actions (Top 5)
1. Refactor astrology geocoder to async-safe and verify endpoints return 2xx.
2. Update backend tests to current module layout to restore pytest usability.
3. Set Render backend `ENVIRONMENT=production` and document migration/seed flow.
4. Add ephemeris-mode logging/health output to catch silent precision downgrades.
5. Improve frontend lunar month fetch resilience (retry/backoff + provenance display).
