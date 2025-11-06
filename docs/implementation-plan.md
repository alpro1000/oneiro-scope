# ONEIROSCOP-LUNAR Delivery Plan

## Guiding principles
- **Modularity**: separate concerns into frontend, backend, data, AI, integrations, and infrastructure packages.
- **Evidence-based interpretations**: prioritize Hall/Van de Castle (HVdC) methodology with transparent confidence metrics and HITL tooling.
- **Progressive enhancement**: deliver lunar calendar + HVdC MVP before advanced features (Perplexity search, astrology, monetization).
- **Compliance & provenance**: record licenses, data sources, and processing lineage in metadata tables.

## Phase-by-phase roadmap
Each phase lists major tasks, suggested technologies, and prerequisites.

### Phase 0 — Repository audit & restructuring (Week 0)
- Produce `audit_report.md` (done) and create architecture RFC summarizing target system boundaries.
- Reorganize repo into monorepo layout:
  - `frontend/` (Next.js + TailwindCSS + shadcn/ui).
  - `backend/` (FastAPI or NestJS) with modular routers.
  - `services/etl/` (Python ETL package with Poetry).
  - `infrastructure/` (Dockerfiles, Terraform if needed).
- Configure shared linting/formatting (`ruff`, `prettier`, `eslint`) and Git hooks via `lefthook`.
- Prereq: none (starting point).

### Phase 1 — Lunar engine & calendar UI (Week 1)
- Implement lunar calculation microservice (`backend/lunar`) using `astral` or `pyephem`; expose `GET /lunar?date=` with cache layer (Redis/Supabase Functions).
- Build `frontend/app/(calendar)/page.tsx` with componentized LunarWidget:
  - Default view: today’s lunar data, CTA to expand accordion month grid.
  - Support localization via `next-intl`.
  - Integrate design tokens via CSS variables sourced from `frontend/styles/tokens.css`.
- Add Jest/Playwright tests for accordion interactions.
- Dependencies: Phase 0 repo restructuring.

### Phase 2 — Data ingestion & normalization (Weeks 1–2)
- Package ETL as `services/etl` with submodules per source (DreamBank, SDDb, Dryad, Donders, Monash, UCSC).
- Implement configuration-driven pipelines (YAML → Pydantic models → orchestrated by `prefect` or `dagster` for scheduling).
- Normalize outputs into unified schema (`dream_entry` table) with metadata (source, license, demographics, language, ingestion timestamp).
- Persist raw + normalized data in PostgreSQL (SQLAlchemy migrations) and optionally Parquet on object storage.
- Dependencies: Phase 0 (structure), optional Phase 1 (shared tokens not required).

### Phase 3 — HVdC codebook & annotation (Weeks 2–3)
- Encode HVdC taxonomy into `services/hvdc/codebook.json` with versioning and provenance notes.
- Build automatic pre-annotation pipeline:
  - Text preprocessing (`spaCy`, `stanza`).
  - Rule-based detectors + zero-shot LLM classification (OpenAI function calling) → produce draft HVdC tags.
  - Confidence scoring; queue low-confidence cases for human review (HITL).
- Store annotations in PostgreSQL tables (`dream_annotation`, `hvdc_metric`).
- Provide evaluation notebooks (Jupyter) measuring Cohen’s κ / Krippendorff’s α on labeled subset.
- Dependencies: Phase 2 data schema.

### Phase 4 — Dream analysis API (Weeks 3–4)
- Implement `POST /sleep/analyze` in backend:
  - Accept dream text, optional metadata, language.
  - Pipeline: text normalization → HVdC pre-annotation → statistics vs norms → LLM interpretation template → compile response payload (HVdC profile, interpretation, recommendations).
  - Persist user submission + results if authenticated.
- Add `GET /sleep/{dream_id}` and `POST /sleep/upload` for user archives.
- Integrate rate limiting (FastAPI + Redis) and tracing (OpenTelemetry).
- Dependencies: Phases 2–3.

### Phase 5 — Conversational UI & chat orchestration (Weeks 4–5)
- Build chat experience using Next.js App Router + server actions; maintain message history in Supabase/Postgres.
- Provide quick action buttons (“Analyze dream”, “Today’s lunar day”, “Daily forecast”).
- Implement voice input component leveraging Web Speech API (browser) with fallback to backend Whisper transcription endpoint (`POST /speech-to-text`).
- Add streaming responses via Server-Sent Events or WebSockets.
- Dependencies: Phases 1 and 4.

### Phase 6 — Telegram integration (Week 5)
- Develop bot using `python-telegram-bot` or `grammY` (TypeScript).
- Commands: `/start`, `/lunar [date]`, `/analyze`, `/voice` (handles audio via Whisper).
- Link Telegram user IDs to platform accounts; reuse backend APIs via authenticated tokens.
- Dependencies: Phases 4–5.

### Phase 7 — Perplexity & research enrichment (Weeks 5–6)
- Abstract search connector service with provider interface (`services/search`): implementations for Perplexity API and fallback local knowledge base.
- Implement scheduled jobs to enrich HVdC symbols with latest research summaries; cache results with citations.
- Display research snippets in chat sidebar and export pipeline.
- Dependencies: Phases 2–5.

### Phase 8 — User profiles, storage & monetization (Weeks 6–7)
- Implement authentication (Supabase Auth or Auth0) with OAuth + Telegram link.
- Build user dashboard (`frontend/app/(dashboard)`) for dream history, saved interpretations, subscription status.
- Integrate payment provider (Stripe for global, YooMoney for RU) with webhook processing (`backend/payments`).
- Generate PDF reports via `weasyprint`/`react-pdf` and email delivery.
- Dependencies: Phases 4–5 (analysis), Phase 6 (optional Telegram linking).

### Phase 9 — Astrology extension (Weeks 7–8, optional)
- Wrap `Swiss Ephemeris` or `astral` calculations into modular service.
- Provide `GET /astrology/transit` and integrate optional toggle in chat UI.
- Ensure separation so astrology features can be disabled for scientific-only deployments.
- Dependencies: Phase 1 lunar engine, Phase 5 chat UI.

### Phase 10 — Affiliate & recommendations (Week 8)
- Create recommendation service ingesting partner catalogs (CSV/API) into `partner_offer` table.
- Expose `/recommend?topic=` with filters (locale, price, availability) and A/B testing flags.
- Surface context-aware recommendations in chat responses.
- Dependencies: Phases 4–5.

### Phase 11 — Design system & UX polish (Continuous, major push Weeks 3–8)
- Define design tokens in `frontend/styles/tokens.css` and sync with Figma using `tokens-studio`.
- Component library: buttons, chat bubbles, accordion cards, lunar glyphs.
- Accessibility audits (axe-core, Lighthouse) and motion guidelines (Framer Motion for subtle transitions).
- Dependencies: Phase 0 restructuring; informs all UI phases.

### Phase 12 — Testing & quality gates (Continuous)
- Unit: pytest for backend, vitest/jest for frontend.
- Integration: Playwright end-to-end flows (calendar toggle, dream analysis chat, payments).
- Performance: Locust/Artillery load tests ensuring <5s analysis time under concurrency.
- Data quality: Great Expectations suite for ETL outputs.
- Dependencies: start after Phase 1 prototypes; run continuously in CI.

### Phase 13 — DevOps & deployment (Continuous, final hardening Weeks 6–9)
- Containerize services with Docker; orchestrate via `docker-compose` (dev) and `Kubernetes`/`Render` for prod.
- GitHub Actions pipelines: lint → test → build → deploy (frontend to Vercel, backend to Railway/Render, ETL to scheduled jobs).
- Observability: integrate Sentry, Prometheus metrics, structured logging (OpenTelemetry).
- Backups: nightly Postgres snapshots, object storage versioning.
- Dependencies: relies on stabilizing backend/frontend modules (Phases 1–10).

## Task dependency graph (high level)
- Phase 0 → Phase 1, Phase 2, Phase 11.
- Phase 1 → Phase 5, Phase 9.
- Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6.
- Phase 2 & Phase 4 → Phase 7, Phase 8, Phase 10.
- Phase 5 → Phase 7, Phase 8, Phase 9, Phase 10.
- Phases 1–10 feed into Phase 11 (design), Phase 12 (testing), Phase 13 (DevOps).

## Technology recommendations
- **Frontend**: Next.js 14, React Server Components, TailwindCSS, Radix UI, Framer Motion, Zustand for local state.
- **Backend**: FastAPI + SQLAlchemy + Pydantic v2, Celery/RQ for background jobs, Redis cache, PostgreSQL primary store.
- **AI & NLP**: spaCy (linguistics), Transformers (HuggingFace) for classification, OpenAI GPT-4o-mini for interpretations, Whisper large-v2 for speech.
- **Data orchestration**: Prefect 2.x, dbt for analytical models, Great Expectations for validation.
- **Search integrations**: Perplexity API, Serper.dev fallback, custom crawler obeying robots.txt with `requests-html` or `playwright` for JS-heavy pages.
- **Infrastructure**: Docker, GitHub Actions, Vercel (frontend), Render/Railway (backend), Supabase (auth/storage), Sentry (monitoring).

## Risk mitigation strategies
- Capture source licenses and user consent metadata in database; block ingestion when license missing.
- Implement review workflow for low-confidence HVdC annotations; maintain audit logs.
- Add rate limiting and caching for external API calls (Perplexity, astronomy).
- Provide offline fallback datasets to keep lunar calculations and dream analysis functional without external services.
- Establish security baselines (OWASP ASVS checks, dependency scanning, secrets management via GitHub Actions OIDC + cloud KMS).
