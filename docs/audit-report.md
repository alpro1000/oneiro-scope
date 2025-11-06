# ONEIROSCOP+LUNAR — Audit of `lunar-landing`

## Repository snapshot
- **Type**: full-stack application with a FastAPI backend, React/Next.js frontend, and a Python ETL toolkit.
- **Primary services**: lunar phase + dream guidance API (`backend/app/main.py`), composable web client (`frontend/`), automated data refresh (`etl/`).
- **Automation**: multi-stage GitHub Actions (`.github/workflows/`) for linting/tests, ETL verification, and deployment checks.

## Architecture overview
### Backend — FastAPI
- `backend/app/main.py` exposes `/lunar` endpoints backed by deterministic moon phase calculations and localized copy decks.
- FastAPI is wrapped with permissive CORS to allow requests from the Next.js frontend and external partners.
- Python dependencies are managed in `backend/requirements.txt`; the service is deployed on Render using `render.yaml` with containerized release images.

### Frontend — React / Next.js
- `frontend/` houses a Next.js 14 application with scriptable npm workflows (`package.json`).
- UI combines lunar calendar widgets, dream interpretations, and locale-aware content using Tailwind CSS and Storybook-powered design tokens.
- Unit tests run with Jest and Testing Library (`npm run test:unit`); end-to-end coverage uses Playwright (`npm run test:e2e`).

### Data & ETL
- The `etl/` package standardizes ingestion pipelines (`etl_dreams.py`) driven by YAML configuration (`sources_config.yml`) and symbol taxonomy (`symbols_map.json`).
- Raw partner drops and manual uploads are staged inside `etl/input/`, now tracked as a directory with `.gitkeep` for reproducible layouts.
- Dependencies reside in `etl/requirements.txt`; orchestration is triggered via CI and manual runs documented in `README.md`.

### Continuous Integration / Delivery
- `.github/workflows/frontend-tests.yml` provisions Node 20, installs frontend dependencies in `frontend/`, and runs unit + Playwright suites.
- Additional workflows cover backend lint/test hooks and ETL smoke checks to guard data freshness before deployment.
- Artifacts feed into Render previews; main branch merges trigger container image rebuilds defined in `render.yaml`.

### Hosting — Render
- Render deploys the FastAPI backend as a web service and serves the statically built Next.js frontend via managed static hosting.
- Environment variables for API origins and feature flags are centralized in Render dashboard according to deployment runbooks.

## Key risks & opportunities
1. **Cross-service observability**: Add unified logging/metrics (e.g., OpenTelemetry) spanning FastAPI, ETL, and frontend edge functions.
2. **Data validation**: Expand ETL schema checks and provenance tracking to ensure curated dream datasets remain trustworthy.
3. **Testing depth**: Grow integration coverage that exercises backend+frontend flows plus regression snapshots for lunar calculations.
4. **Deployment automation**: Introduce blue/green deploys on Render once traffic increases to reduce downtime during ETL-driven updates.
5. **Localization pipeline**: Formalize translation management so the dual-locale copy stays consistent across API responses and UI strings.
