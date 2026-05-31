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

### ✅ Фаза 1 — MCP-сервер (`backend/mcp/`)
- [x] `backend/mcp/__init__.py`
- [x] `backend/mcp/server.py` — FastMCP server, stdio + HTTP transports
- [x] `backend/mcp/tools/astrology.py` — natal_chart, horoscope, event_forecast, list_event_types, list_horoscope_periods
- [x] `backend/mcp/tools/dreams.py` — analyze_dream, list_dream_symbols, list_archetypes, list_hvdc_categories
- [x] `backend/mcp/tools/lunar.py` — get_lunar_day, get_lunar_period
- [x] `backend/mcp/tools/geo.py` — search_city, validate_birth_data
- [x] `backend/mcp/README.md` — установка, запуск, подключение к Claude Desktop
- [x] `backend/tests/test_mcp_smoke.py` — 9 smoke-тестов, все зелёные

### ✅ Фаза 2 — ADK-агент (`agents/`)
- [x] `agents/__init__.py`
- [x] `agents/oneiro_agent.py` — Claude Agent SDK, спавн MCP как stdio child
- [x] `agents/prompts/oneiro_system.md` — системный промпт (science-first, cost-aware)
- [x] `agents/cli.py` — `python -m agents.cli "<prompt>"`
- [x] `backend/tests/test_agent_smoke.py` — 5 smoke-тестов, все зелёные

### ✅ Фаза 3 — Skills (`.claude/skills/`)
- [x] `.claude/skills/README.md`
- [x] `.claude/skills/natal/SKILL.md`
- [x] `.claude/skills/horoscope/SKILL.md`
- [x] `.claude/skills/dream/SKILL.md`
- [x] `.claude/skills/lunar/SKILL.md`
- [x] `.claude/skills/deploy-cycle/SKILL.md`
- [x] `.claude/skills/validate-prod/SKILL.md`
- [x] `.claude/skills/cost-report/SKILL.md`
- [x] `.claude/skills/research-symbol/SKILL.md`

### Фаза 4 — Production-фиксы
- [x] `render.yaml` — `ENVIRONMENT=production` (verified already set)
- [x] `backend/api/v1/health.py` — ephemeris mode (SWIEPH/MOSEPH) в /health
- [x] `backend/requirements.txt` — `mcp[cli]` + `claude-agent-sdk`
- [x] `.github/workflows/mcp-smoke.yml` — CI smoke для MCP/agent
- [x] `backend/core/cost_tracker.py` — учёт LLM-затрат, Redis + memory fallback, подключён в `UniversalLLMProvider.generate()`, 7 тестов
- [ ] Dockerfile для MCP-сервера (deferred — backend Dockerfile covers it)
- [ ] Отдельный Render service для MCP HTTP (deferred — embedded in backend works)

---

## Фаза 5 — ADK super-orchestrator + specialist agents

Переход от единого `OneiroAgent` (все 13 tools в одном промпте) к роутеру со специализированными суб-агентами. Чище контекст, доменная экспертиза, параллелизм мульти-доменных запросов, точечный cost-tracking.

```
SuperOrchestrator (router)
   ├─► AstrologyAgent  (natal/horoscope/forecast + geo)
   ├─► DreamAgent      (analyze + symbols/archetypes/hvdc)
   └─► LunarAgent      (get_lunar_day/period)
              ▼
        MCP server (13 tools)
```

### ✅ Фаза A — базовый класс агента
- [x] `agents/base.py` — `BaseOneiroAgent(name, system_prompt_path, allowed_tools, model, max_turns)`; общий `run()`; `_qualify()` идемпотентный.
- [x] `OneiroAgent` → тонкая обёртка вокруг `BaseOneiroAgent` для backward-compat CLI.

### ✅ Фаза B — специализированные суб-агенты
- [x] `agents/specialists/astrology_agent.py` — 7 tools (natal/horoscope/forecast/list_* + geo).
- [x] `agents/specialists/dream_agent.py` — 4 tools (analyze + list_*).
- [x] `agents/specialists/lunar_agent.py` — 2 tools (get_lunar_day/period).
- [x] `agents/prompts/{astrology,dream,lunar}_system.md` — доменные промпты.
- [x] `backend/tests/test_specialist_agents.py` — 10 тестов, все зелёные. Полный suite: 78 passed, 6 skipped.
- [x] Specialist-тесты включены в `mcp-smoke.yml`.

### Фаза C — супер-оркестратор
- [ ] `agents/orchestrator.py` — `SuperOrchestrator`:
  - **Intent router** — классификатор (LLM или keyword-rules) → `{astrology, dream, lunar}` (один или несколько).
  - **Fan-out** — `asyncio.gather` параллельно по выбранным специалистам.
  - **Context passing** — результат натальной карты (`sun/moon/asc`) прокидывается в Dream/Horoscope как контекст.
  - **Merge** — собирает итоговый ответ в языке пользователя.
- [ ] `agents/cli.py` — флаг `--orchestrate` (default ON для мульти-доменных запросов).
- [ ] `backend/tests/test_orchestrator.py` — роутинг (моки), мульти-доменный merge, изоляция tool-наборов.

### Фаза D — наблюдаемость стоимости
- [ ] `backend/core/cost_tracker.py` — добавить тег `agent` в ключ (`oneiro:cost:<provider>:<agent>:<day>:...`).
- [ ] Прокинуть `agent_name` через `UniversalLLMProvider` (опциональный параметр, default `None` → ключ без тега, backward-compat).
- [ ] Лог роутинга в оркестраторе: `[router] intent=<...> agents=[astrology,lunar]`.

---

## Definition of Done

- `python -m backend.mcp.server` запускается, регистрирует ≥8 tools
- Claude Desktop / Cursor может подключиться по stdio и вызвать `natal_chart`
- `python -m agents.cli natal "1990-05-15 12:00 Moscow"` возвращает структурированную натал-карту
- `/natal` skill работает в Claude Code
- `pytest backend/tests/test_mcp_smoke.py` зелёный
- Все изменения в `claude/eager-noether-5UQJR`, PR не создаётся пока не попросят
