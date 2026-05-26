# OneiroScope — план перевода на MCP + ADK + Skills

**Branch:** `claude/eager-noether-5UQJR`
**Started:** 2026-05-26
**Goal:** Полный production-цикл — MCP-сервер поверх существующего FastAPI, ADK-агент-оркестратор, набор skills для Claude Code, дисциплина sessions.

---

## Фазы

### ✅ Фаза 0 — Дисциплина и фундамент
- [x] `docs/PLAN.md` — этот файл, единый источник прогресса
- [x] `docs/soul.md` — личный контекст проекта (§1 identity, §2 active projects, §3 rules, §9 session log)
- [x] `docs/steering/tech.md` — архитектурные решения по технологиям
- [x] `docs/steering/structure.md` — структура репо, MCP/ADK слои
- [x] `docs/steering/product.md` — продуктовые принципы
- [x] `CLAUDE.md` — mandatory-block наверху файла (чтобы новые сессии читали первым)
- [x] `.claude/settings.local.json` — разрешения для bash/git/pytest

### Фаза 1 — MCP-сервер (`backend/mcp/`)
- [ ] `backend/mcp/__init__.py`
- [ ] `backend/mcp/server.py` — FastMCP server, stdio + HTTP transports
- [ ] `backend/mcp/tools/astrology.py` — natal_chart, horoscope, event_forecast, retrograde_planets
- [ ] `backend/mcp/tools/dreams.py` — dream_analyze, dream_symbols
- [ ] `backend/mcp/tools/lunar.py` — lunar_day, lunar_period
- [ ] `backend/mcp/tools/geo.py` — city_search, validate_birth_data
- [ ] `backend/mcp/README.md` — установка, запуск, подключение к Claude Desktop
- [ ] `backend/tests/test_mcp_smoke.py` — smoke-тест что tools регистрируются

### Фаза 2 — ADK-агент (`agents/`)
- [ ] `agents/__init__.py`
- [ ] `agents/oneiro_agent.py` — Claude Agent SDK, system prompt, tool-loop
- [ ] `agents/prompts/oneiro_system.md` — системный промпт "астролог-исследователь"
- [ ] `agents/cli.py` — CLI-обёртка (`python -m agents.cli natal "1990-05-15 Moscow"`)

### Фаза 3 — Skills (`.claude/skills/`)
- [ ] `.claude/skills/natal/SKILL.md`
- [ ] `.claude/skills/horoscope/SKILL.md`
- [ ] `.claude/skills/dream/SKILL.md`
- [ ] `.claude/skills/lunar/SKILL.md`
- [ ] `.claude/skills/deploy-cycle/SKILL.md`
- [ ] `.claude/skills/validate-prod/SKILL.md`
- [ ] `.claude/skills/cost-report/SKILL.md`
- [ ] `.claude/skills/research-symbol/SKILL.md`

### Фаза 4 — Production-фиксы
- [ ] `render.yaml` — `ENVIRONMENT=production`, добавить MCP-сервис
- [ ] `backend/core/cost_tracker.py` — учёт LLM-затрат в Redis
- [ ] `backend/api/v1/health.py` — добавить ephemeris mode в health-ответ
- [ ] `.github/workflows/mcp-smoke.yml` — CI-smoke для MCP-сервера
- [ ] Dockerfile для MCP-сервера

---

## Definition of Done

- `python -m backend.mcp.server` запускается, регистрирует ≥8 tools
- Claude Desktop / Cursor может подключиться по stdio и вызвать `natal_chart`
- `python -m agents.cli natal "1990-05-15 12:00 Moscow"` возвращает структурированную натал-карту
- `/natal` skill работает в Claude Code
- `pytest backend/tests/test_mcp_smoke.py` зелёный
- Все изменения в `claude/eager-noether-5UQJR`, PR не создаётся пока не попросят
