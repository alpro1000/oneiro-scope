# OneiroScope — Soul

Personal/project memory file for cross-session continuity. Read by Claude Code at every session start (see mandatory block in `CLAUDE.md`).

---

## §1 Identity

- **Project:** OneiroScope — эзотерический сервис: научная астрология (Swiss Ephemeris) + анализ снов (Hall/Van de Castle, REM/NREM) + лунный календарь.
- **Repo:** `alpro1000/oneiro-scope`
- **Owner:** alpro1000 (alpro1000@gmail.com)
- **Stack:** Python 3.11 / FastAPI / Pydantic v2 backend, Next.js 14 (App Router, next-intl RU/EN) frontend, PostgreSQL + Redis, Render.com deploy.
- **Languages:** Code/comments — English. Product UI/content — RU + EN. Owner communicates in RU.

## §2 Active Projects / Contexts

### §2.1 OneiroScope (primary)
- Production target: Render.com (backend + frontend + Postgres + Redis blueprint).
- LLM providers (cost order): Groq (free) → Gemini ($0.075/1M) → Together → OpenAI → Anthropic.
- Default LLM env: `GROQ_API_KEY` or `GEMINI_API_KEY`. Fallback templates exist for all services.

### §2.2 Current branch
- `claude/eager-noether-5UQJR` — adding MCP server + ADK agent + skills layer.

### §2.3 Active freelance
*(none recorded — populate when relevant)*

### §2.4 KB sources
- Astrology: Swiss Ephemeris (SWIEPH binary files), `backend/services/astrology/knowledge_base/` (planets/houses/aspects JSON), `backend/data/lunar_tables.json`.
- Dreams: `backend/services/dreams/knowledge_base/symbols.json` (56 symbols, 7 modern), DreamBank Hall/Van de Castle norms `hvdc_norms.json`, prompts in `backend/services/dreams/ai/prompts/`.
- Geo: GeoNames API (username `alpro1000`, 30k req/day), 90+ city fallback DB.

## §3 Rules / Discipline

5 rules owner enforces (owner-side, NOT Claude Code's job):

1. **Pre-session:** Owner does nothing. Claude Code must read the mandatory block in `CLAUDE.md` within first 3 minutes of any session. If it doesn't — owner stops and reminds.
2. **Post-session:** Owner verifies Claude Code updated `docs/soul.md §9` (Session log). Last Gate of every task. If forgotten — owner asks: *"Update docs/soul.md §9 with this session log."*
3. **Architectural decisions** (new AI provider, DB switch, Core↔Kiosks pattern change, new MCP tool taxonomy): update `docs/steering/*.md` — usually `tech.md` or `structure.md`.
4. **New project / case / corpus:** update `§2.3` (Active freelance) or `§2.4` (KB sources) here.
5. **Project Knowledge sync (claude.ai online):** owner copies `soul.md` + `steering/*` into Project Knowledge on claude.ai weekly (or after major update). Claude Code (CLI/home) sees this via Git automatically.

**NOT discipline (skip):**
- Every commit → soul.md update: NO, only for substantial work.
- Updating tasks/specs: not mandatory if spec is finished — just archive the status header at the top.
- Versioning steering docs: only on major rewrite.

## §4 Code style / Conventions

- Backend: Pydantic v2 strict contracts, async services, no mocks in production code, fallback templates instead.
- LLM: provider abstraction via `UniversalLLMProvider`, cost-ordered selection, retry-with-fallback.
- Frontend: Server components for SSR data fetch, client components only when interactive. next-intl for all user-facing strings.
- Tests: pytest backend, jest frontend. No new feature ships without at least a smoke test.
- Commit messages: imperative ("add", "fix", "refactor"), no Claude Code session-id leak into commit body.

## §5 Known issues / Tech debt

- No user auth / natal chart persistence (TODOs in `backend/api/v1/astrology.py:59,102,175`).
- ~~5/14 dream interpreter tests failing (64% pass rate).~~ **Fixed 2026-05-26 in `claude/fix-dream-narrative-tests`** — 14/14 passing.
- ~~`ENVIRONMENT=production` not yet set on Render~~. Already set in `render.yaml` (verified 2026-05-26).
- ~~LLM cost tracking middleware structure exists but counter not wired~~. **Fixed 2026-05-26 PR #111** — `backend/core/cost_tracker.py` wired into `UniversalLLMProvider.generate()`.
- ~~Ephemeris mode (SWIEPH vs MOSEPH) not logged in `/health`~~. **Fixed 2026-05-26 PR #111** — and now also logged on app startup (PR #113).
- LunarWidget no retry on 502.
- **`build-and-validate` CI is red on every PR** (pre-existing). Diagnostic improvements landed in PR #113 (`pip install -v`, upgraded setuptools/wheel); next iteration should see the actual error trace. Not blocking — `mergeable_state` is `unstable` not `blocked`.

## §6 Architecture decisions log

See `docs/steering/tech.md` for technology choices and `docs/steering/structure.md` for layering.

Recent decisions:
- **2026-05-26** — Adopting MCP-first architecture. MCP server wraps existing FastAPI services as tools; ADK agent built on top; skills consume the agent. Rationale: reusable across Claude Desktop / Cursor / web Claude Code; one set of contracts.

## §7 Deployment notes

- Render blueprint: `render.yaml` (backend + frontend + Postgres + Redis).
- Env vars exchange via `RENDER_EXTERNAL_URL` (frontend ↔ backend).
- After updating `NEXT_PUBLIC_*` envs → **Clear build cache & Deploy** on frontend.
- LLM keys stored as Render secrets (`sync: false` in blueprint).

## §8 Open questions / Parking lot

- Should MCP server run as separate Render service or embedded in backend? → Leaning separate: cleaner cost/security boundary.
- Auth strategy for MCP HTTP transport? → JWT? OAuth? Bearer token from Render env initially.
- Cache strategy for natal charts before user-auth lands → Redis with content-hash key (birth_date+place+time).

---

## §9 Session log

### 2026-05-28 — claude/adk-specialists — ADK Phase A+B: base class + 3 specialist agents
**Goal:** Refactor the single `OneiroAgent` into a base class and stand up 3 domain-specialist agents (Astrology / Dream / Lunar) as Phase A+B of the SuperOrchestrator plan in `docs/PLAN.md`.

**Done:**
- `agents/base.py` — `BaseOneiroAgent` (name, system-prompt path, allowed_tools subset). Shared `run()` (streaming text deltas). Idempotent `_qualify()` (bare `tool` or `mcp__oneiro__tool` both work).
- `agents/oneiro_agent.py` — `OneiroAgent` is now a 30-line subclass of `BaseOneiroAgent` keeping all 13 tools; backward-compat CLI unaffected.
- `agents/specialists/{astrology,dream,lunar}_agent.py` — each declares a narrow tool subset:
  - astrology: 7 (natal/horoscope/forecast/list_* + geo helpers)
  - dream: 4 (analyze + list_*)
  - lunar: 2 (get_lunar_day/period)
- `agents/prompts/{astrology,dream,lunar}_system.md` — domain prompts (science-first, provenance shown, no prediction-as-fact, no esoteric/forbidden content).
- `backend/tests/test_specialist_agents.py` — 10 tests: import, tool-subset correctness, prompt content, name uniqueness, qualifier idempotence, generalist backward-compat. All green.
- Full backend suite: **78 passed, 6 skipped** (was 68 + 10 specialist). Specialist tests added to `mcp-smoke.yml`.
- `docs/PLAN.md` — Phase 5 added; A+B checked off.

**Next (Phase C+D, separate PR):** SuperOrchestrator (intent router + fan-out + context-passing + merge) + cost-tracker agent tag.

---

### 2026-05-28 — claude/cloud-llm-providers — Vertex AI + Bedrock providers, horoscope/dream test run, lunar-table path fix
**Goal:** Run sample daily/monthly/yearly horoscopes + a dream for birth data (01.07.1977 22:30 Запорожье), and add Vertex AI / Bedrock as LLM providers.

**Done:**
- **Vertex AI provider** (`backend/core/llm_provider.py`): Gemini via GCP regional endpoint. Auth via `VERTEX_ACCESS_TOKEN` or ADC (`google-auth`). Gated on `VERTEX_PROJECT` + creds.
- **Bedrock provider**: Claude via AWS `bedrock-runtime.invoke_model` (boto3, SigV4, sync call in executor). Gated on AWS creds + boto3 importable. Anthropic Messages schema + `anthropic_version: bedrock-2023-05-31`.
- Both added to the cost-ordered catalog (Vertex after Gemini, Bedrock after Anthropic) and to `_provider_configured()`; disable gracefully when unconfigured.
- `backend/tests/test_llm_providers_cloud.py` — 8 tests (gating + request construction with mocked httpx/boto3). Full backend suite 68 passed, 6 skipped.
- **Bug fix**: `backend/services/astrology/interpreter.py` loaded `lunar_tables.json` from `backend/services/data/` (wrong) instead of `backend/data/` — degraded ALL horoscope template content. Fixed the path (one more `dirname`).
- Deps: added optional `google-auth>=2.27`, `boto3>=1.34` to `backend/requirements.txt`.
- Docs: CLAUDE.md env section + provider table, `docs/steering/tech.md` provider list.

**Test run results (template fallback, no LLM keys in this env):**
- Natal chart 01.07.1977 22:30 Запорожье → Sun Cancer 9.83°, Moon Capricorn, Asc Aquarius, MC Sagittarius (MOSEPH analytic — no SWIEPH binaries locally). Geocoded via 90-city fallback (47.84, 35.20, Europe/Kyiv).
- Daily/monthly/yearly horoscopes: correct period boundaries; content brief+identical because template fallback only uses lunar day (LLM keys produce 600-1000 words/period).
- Dream analysis: symbols escape_liberation/house/animal, emotion happiness 0.65, archetypes liberation/self/instinct. Interpretation empty without LLM key.

**Notes:**
- Local env briefly had the `external/pyswisseph` stub shadowing real pyswisseph (from the build-CI work) — reinstalled real `pyswisseph==2.10.3.2` for accurate positions.
- Geocoder rejects "City, Country" suffix (", Украина" failed; bare "Запорожье" works). Candidate future fix: strip country segment before fallback lookup.

---

### 2026-05-26 — claude/fix-build-ci — Build CI hardening + startup ephemeris log
**Goal:** Get `build-and-validate` CI green (red on every PR since pre-existing) + add operator-friendly startup logs.

**Done (merged via PR #113):**
- `requirements.txt` / `etl/requirements.txt`: pin `numpy>=1.26,<3`, `pandas>=2.2,<3`, `pyarrow>=15`. Clean-venv install verified locally.
- `.github/workflows/build.yml`: upgrade `setuptools wheel build` alongside pip, switch to `pip install -v` (diagnostic), use `python -m pytest` for consistency with smoke workflow.
- `backend/app/main.py`: log ephemeris mode at startup (mirrors `/health`). INFO for SWIEPH, WARNING for MOSEPH fallback with `SE_EPHE_PATH` hint.

**Outcome:** `build-and-validate` **still red on PR #113** — root cause not visible without GHA log access. Verbose flag will surface the actual error on the next iteration. Smoke + inventory + dream tests all green.

**Decisions:**
- Did not chase further without log visibility. Pinned-version + diagnostic improvements are useful regardless of whether they fully resolve build-and-validate.
- Did NOT revert changes — all three are independently beneficial.

---

### 2026-05-26 — claude/fix-dream-narrative-tests — Dream interpreter v2.1 test fixes
**Goal:** Resolve the 6 known-failing tests in `test_dream_interpreter_narrative.py::TestContextualSymbolValidation` (noted as `§5` known issue; tracked as out-of-scope in the previous session).

**Done:**
- Added Russian keyword roots to `symbols.json` for `vehicle` (`автомобил`, `авто`, `машин`), `surveillance` (`слеж`, `следи`, `наблюд`), `boundaries` (`границ`, `наруш`, `вторг`), `escape_liberation` (`выброс`, `отброс`, `свобод`, `освобод`, `облегчен`). Root: the inflection-aware regex needs a literal prefix of the surface form.
- Restored strict reinforcement requirement for `surveillance` only — lone keywords like "camera" produced false positives. Other reinforcement-driven symbols stay soft.
- Added house exclusion for `(throw|выбросил…) … (window|окн)` — common in surveillance/escape dreams, the window is not a house symbol.

**Verified:** 14/14 dream narrative tests pass; full backend suite 60/60 (6 skipped). Updates §5 (5/14 → 0/14 failing).

**Decisions:**
- Did NOT change the Russian regex compilation (still `\bkeyword\w*\b`). Keyword roots were the lowest-risk fix.
- Strict reinforcement applied only to `surveillance`; widening it to others would regress legit detection cases.

---

### 2026-05-26 — claude/eager-noether-5UQJR — MCP + ADK + Skills foundation
**Goal:** Stand up MCP-server / ADK-agent / skills layer on top of existing FastAPI services + introduce discipline files (soul.md, steering/*, mandatory block in CLAUDE.md).

**Plan reference:** `docs/PLAN.md` (phases 0–4).

**Phase 0 completed:** Created `docs/PLAN.md`, `docs/soul.md` (this file), `docs/steering/{tech,structure,product}.md`, mandatory-block header in `CLAUDE.md`.

**Phase 1 completed — MCP server (`backend/mcp/`):**
- `server.py` runs FastMCP on stdio (default) or streamable-HTTP. 13 tools registered:
  astrology (calculate_natal_chart, generate_horoscope, forecast_event, list_event_types, list_horoscope_periods),
  dreams (analyze_dream, list_dream_symbols, list_archetypes, list_hvdc_categories),
  lunar (get_lunar_day, get_lunar_period),
  geo (search_city, validate_birth_data).
- `backend/tests/test_mcp_smoke.py` — 9 tests, all green.

**Phase 2 completed — ADK agent (`agents/`):**
- `OneiroAgent` spawns MCP server as stdio child; restricts allowed_tools to `mcp__oneiro__*` (no shell, no fs).
- System prompt enforces science-first, cost-aware tool chain, bilingual parity, provenance, no prediction-as-fact.
- `python -m agents.cli "<prompt>"` CLI entry.
- 5 agent smoke tests, all green.

**Phase 3 completed — Skills (`.claude/skills/`):**
- 8 SKILL.md files: `/natal`, `/horoscope`, `/dream`, `/lunar`, `/deploy-cycle`, `/validate-prod`, `/cost-report`, `/research-symbol`.
- README lists conventions; all skills consume `mcp__oneiro__*` only.
- Expanded `.claude/settings.local.json` with common dev permissions.

**Phase 4 partial:**
- `ENVIRONMENT=production` already set in `render.yaml` (verified).
- `/health` now returns `ephemeris` block (engine + path + first 5 files).
- `mcp[cli]>=1.2` + `claude-agent-sdk>=0.2` added to `backend/requirements.txt`.
- `.github/workflows/mcp-smoke.yml` runs 14 smoke tests on push/PR.
- Deferred: `cost_tracker.py` (needs middleware wiring), separate Render MCP service (embedded works), MCP Dockerfile (backend Dockerfile covers).

**Decisions:**
- MCP-first adopted: FastAPI services strict-typed → trivial adapters; one MCP server reusable from Claude Desktop, Cursor, agents, web Code.
- Agent restricted to MCP tools only — never invokes Bash/Write/Read directly, keeps domain scope clean.
- Skill layer never calls FastAPI HTTP — only MCP tools (rule in `docs/steering/structure.md`).
- Cost tracking deferred to next session: requires deeper LLM-provider middleware change.

**Out of scope this session:** user auth, natal-chart DB persistence, 5/14 failing dream interpreter tests, separate Render MCP service.

**Verified:** 14/14 smoke tests green (`pytest backend/tests/test_mcp_smoke.py backend/tests/test_agent_smoke.py`).

*(append new entries above this line on next session)*
