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
- 5/14 dream interpreter tests failing (64% pass rate).
- `ENVIRONMENT=production` not yet set on Render (still `development` → triggers `init_db()` in prod).
- LLM cost tracking middleware structure exists but counter not wired.
- Ephemeris mode (SWIEPH vs MOSEPH) not logged in `/health`.
- LunarWidget no retry on 502.

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
