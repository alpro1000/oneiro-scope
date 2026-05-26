# Steering — Repository Structure

## Layering

```
┌─ Skills (.claude/skills/*)              ← user-invocable in Claude Code
│  /natal /horoscope /dream /lunar
│  /deploy-cycle /validate-prod /cost-report /research-symbol
├─ ADK Agent (agents/)                    ← orchestrator, Claude Agent SDK
│  oneiro_agent.py + prompts/
├─ MCP Server (backend/mcp/)              ← canonical tool surface
│  server.py + tools/{astrology,dreams,lunar,geo}.py
├─ FastAPI (backend/app/main.py + api/v1) ← HTTP surface (web UI + 3rd parties)
└─ Services (backend/services/)           ← implementation
   astrology/, dreams/, lunar/
```

**Strict rule:** Agents and skills consume MCP tools. They do NOT call FastAPI HTTP or services directly. MCP tools may internally call services (same process, no HTTP hop).

## Top-level directory layout

```
oneiro-scope/
├── agents/                       # ADK Claude Agent SDK
│   ├── oneiro_agent.py
│   ├── cli.py
│   └── prompts/
├── backend/
│   ├── app/main.py               # FastAPI entry
│   ├── api/v1/                   # HTTP routes
│   │   ├── astrology.py
│   │   ├── dreams.py
│   │   ├── lunar.py
│   │   └── health.py
│   ├── core/                     # config, logging, llm_provider, cost_tracker
│   ├── mcp/                      # MCP server (NEW — Phase 1)
│   │   ├── server.py
│   │   └── tools/
│   │       ├── astrology.py
│   │       ├── dreams.py
│   │       ├── lunar.py
│   │       └── geo.py
│   ├── middleware/               # rate_limit, etc.
│   ├── services/                 # implementation
│   │   ├── astrology/{service,ephemeris,natal_chart,transits,geocoder,ai/...}
│   │   ├── dreams/{service,analyzer,ai/...}
│   │   └── lunar/{engine,content}
│   └── tests/                    # pytest
├── frontend/                     # Next.js app
│   ├── app/[locale]/{page,astrology,dreams,(calendar)/calendar}
│   ├── lib/{astrology,dreams,lunar}-client.ts
│   └── messages/{en,ru}.json
├── docs/
│   ├── PLAN.md                   # current task plan
│   ├── soul.md                   # cross-session memory (§9 = session log)
│   ├── steering/{tech,structure,product}.md
│   └── architecture/             # deeper diagrams / specs
├── .claude/
│   ├── skills/                   # SKILL.md per skill
│   └── settings.local.json
├── .github/workflows/            # CI
├── render.yaml                   # deploy
└── docker-compose.yml
```

## File naming conventions

- Python: `snake_case.py`. Test files `test_*.py`.
- Skills: `.claude/skills/<slug>/SKILL.md` (uppercase, no extension prefix).
- Steering docs: `docs/steering/<topic>.md` lowercase.
- Session reports: `docs/SESSION_*_<YYYY-MM-DD>*.md` (legacy).

## Where things live

- **Add a planet to astrology:** `backend/services/astrology/knowledge_base/planets.json` + ephemeris constant in `ephemeris.py`.
- **Add a dream symbol:** `backend/services/dreams/knowledge_base/symbols.json` (use `/research-symbol` skill to help). **Russian keywords must be roots, not inflected forms** — the analyzer compiles `\bkeyword\w*\b`, so the keyword has to be a literal prefix of the surface form. Use `границ` (covers границ-а/-ы/-у/-ой), `вторг` (covers вторгся/вторгается), `выброс` (covers выбросил/выбросить/выбросив). Long noun keywords like `нарушение` won't match the verb `нарушил`.
- **Add a new MCP tool:** create function in `backend/mcp/tools/<area>.py`, decorate, register in `backend/mcp/server.py`.
- **Add a translation:** `frontend/messages/{en,ru}.json`. Both must be updated.
- **Add an env var:** `backend/core/config.py` (Pydantic Settings) + `render.yaml` envVars block + `.env.example` + this file (if structural).

## MCP tool taxonomy

Tools grouped by file:

- `tools/astrology.py` — `calculate_natal_chart`, `generate_horoscope`, `forecast_event`, `get_retrograde_planets`, `list_event_types`.
- `tools/dreams.py` — `analyze_dream`, `list_dream_symbols`, `list_archetypes`, `list_hvdc_categories`.
- `tools/lunar.py` — `get_lunar_day`, `get_lunar_period`.
- `tools/geo.py` — `search_city`, `validate_birth_data`.
