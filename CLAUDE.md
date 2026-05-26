# CLAUDE.md - OneiroScope Project Guide

> **🔴 MANDATORY BLOCK — READ FIRST (every new session)**
>
> Before doing anything else in this repo:
>
> 1. Read `docs/soul.md` — cross-session memory: §1 identity, §2 active contexts, §5 known issues, §9 latest session log.
> 2. Read `docs/PLAN.md` if it exists — current task plan with checkboxes; continue from the first unchecked item.
> 3. Read `docs/steering/{tech,structure,product}.md` if your task touches architecture, layering, or product principles.
> 4. Hard rule: **agents and skills consume MCP tools** (`backend/mcp/`), they do not call FastAPI services or HTTP routes directly. FastAPI = HTTP surface; MCP = canonical tool surface; agent/skills = consumers.
> 5. At the end of any substantial session: append a new entry to `docs/soul.md §9` (Session log) — date, branch, what changed, decisions. This is the final Gate of every task.
> 6. Develop on the branch named in the task prompt. Never push to a different branch without explicit permission.
>
> If any of these files are missing, create them from the templates referenced in `docs/PLAN.md` Phase 0 before continuing.

---

## Project Overview

**OneiroScope** - комплексный эзотерический сервис, объединяющий научный подход к астрологии и анализу снов с лунным календарём.

### Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- Pydantic v2 (strict contracts)
- Swiss Ephemeris (астрономические расчёты)
- Claude API (AI интерпретации)
- Redis (кэширование, опционально)

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion
- next-intl (i18n: RU/EN)

**Infrastructure:**
- Docker / Docker Compose
- Render.com (deployment target)

---

## Project Structure

```
oneiro-scope/
├── backend/
│   ├── app/
│   │   └── main.py              # FastAPI app entry point
│   ├── api/v1/
│   │   ├── health.py            # Health check endpoint
│   │   ├── lunar.py             # Lunar calendar API
│   │   ├── astrology.py         # Astrology API
│   │   └── dreams.py            # Dreams API
│   ├── services/
│   │   ├── lunar/               # Lunar calendar service
│   │   ├── astrology/           # Astrology service
│   │   │   ├── service.py       # Main orchestrator
│   │   │   ├── ephemeris.py     # Swiss Ephemeris wrapper
│   │   │   ├── natal_chart.py   # Birth chart calculations
│   │   │   ├── transits.py      # Transit calculations
│   │   │   ├── geocoder.py      # Location geocoding
│   │   │   ├── contracts.py     # Strict I/O contracts
│   │   │   ├── ai/              # Claude AI integration
│   │   │   └── knowledge_base/  # Planets, houses, aspects JSON
│   │   └── dreams/              # Dream analysis service
│   │       ├── service.py       # Main orchestrator
│   │       ├── analyzer.py      # Hall/Van de Castle analysis
│   │       ├── schemas.py       # Pydantic models
│   │       ├── ai/              # Claude AI interpreter
│   │       └── knowledge_base/  # Symbols JSON
│   └── core/
│       ├── config.py            # Settings
│       ├── database.py          # DB connection
│       └── logging.py           # Logging config
├── frontend/
│   ├── app/
│   │   └── [locale]/
│   │       ├── page.tsx         # Home page
│   │       ├── astrology/       # Astrology page
│   │       ├── dreams/          # Dreams page
│   │       └── calendar/        # Lunar calendar
│   ├── components/
│   │   └── VoiceInput.tsx       # Voice input component
│   ├── lib/
│   │   ├── astrology-client.ts  # Astrology API client
│   │   ├── dreams-client.ts     # Dreams API client
│   │   └── lunar-client.ts      # Lunar API client
│   └── messages/
│       ├── en.json              # English translations
│       └── ru.json              # Russian translations
├── docker-compose.yml
├── render.yaml                  # Render deployment config
└── docs/
    └── architecture/
```

---

## API Endpoints

### Astrology Service (`/api/v1/astrology`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/natal-chart` | Calculate natal chart from birth data |
| GET | `/horoscope` | Get horoscope for period (daily/weekly/monthly/yearly) |
| POST | `/event-forecast` | Forecast event favorability |
| GET | `/event-types` | List supported event types |
| GET | `/retrograde` | Get retrograde planets for date |
| GET | `/cities/search` | Search cities for autocomplete (supports RU/EN, multilingual) |

**City Search Autocomplete:**
The `/cities/search` endpoint provides intelligent city search with:
- GeoNames API integration (30,000 free requests/day)
- Automatic transliteration for Russian queries (Моск → Moscow)
- Fallback to 90+ popular cities database when API unavailable
- Returns city name, country, coordinates, and formatted display string

### Lunar Service (`/api/v1/lunar`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lunar` | Get lunar day info for date (supports timezone parameter) |
| GET | `/timezones` | Get list of popular timezones for lunar calendar |

**Timezone Support:**
The lunar calendar now supports timezone selection for accurate lunar day calculation. Default timezone: `Europe/Moscow`.

### Dreams Service (`/api/v1/dreams`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Analyze dream using Hall/Van de Castle methodology |
| GET | `/categories` | List Hall/Van de Castle content categories |
| GET | `/symbols` | List common dream symbols with interpretations |
| GET | `/archetypes` | List Jungian archetypes |

### Lunar Service (`/api/v1/lunar`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get lunar day info for date |

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up --build
```

---

## Environment Variables

```env
# Backend
ENVIRONMENT=development
DEBUG=true

# LLM Providers (configure at least one, or use fallback mode)
# Providers are tried in order of cost (cheapest first):
GROQ_API_KEY=gsk-...              # FREE tier, very fast (recommended!)
GEMINI_API_KEY=...                # $0.075 per 1M tokens (cheapest paid!)
TOGETHER_API_KEY=...              # $0.20 per 1M tokens
OPENAI_API_KEY=sk-...             # GPT-4o-mini: $0.15 per 1M tokens
ANTHROPIC_API_KEY=sk-ant-...      # Claude Haiku: $0.25 per 1M tokens

# Database
DATABASE_URL=sqlite:///./oneiroscope.db
REDIS_URL=redis://localhost:6379  # Optional

# GeoNames API (for geocoding)
# Register free account at https://www.geonames.org/login
# Free tier: 30,000 requests/day
GEONAMES_USERNAME=your_geonames_username
GEONAMES_LANG=ru

# Lunar Calendar
# Default timezone for lunar day calculations (matches Russian lunar calendars)
LUNAR_DEFAULT_TZ=Europe/Moscow

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Render deployment env vars

When deploying via `render.yaml`, the frontend and backend must exchange full HTTPS URLs using
`RENDER_EXTERNAL_URL` to keep SSR from calling `localhost`:

- `NEXT_PUBLIC_API_URL`, `ASTROLOGY_API_URL`, `DREAMS_API_URL`, `LUNAR_API_URL`, and
  `NEXT_PUBLIC_LUNAR_API_URL` should all come from the backend service `RENDER_EXTERNAL_URL`.
- `ALLOWED_ORIGINS` on the backend should point to the frontend `RENDER_EXTERNAL_URL`.

After updating envs on Render, trigger **Clear build cache & Deploy** for the frontend so the
`NEXT_PUBLIC_*` values are baked into the build.

### LLM Provider Cost Comparison

| Provider | Model | Cost (per 1M tokens) | Speed | Quality |
|----------|-------|---------------------|-------|---------|
| **Groq** | llama-3.1-8b-instant | **FREE** | ⚡ Very Fast | ⭐⭐⭐ Good |
| **Gemini** ⭐ | gemini-1.5-flash | **$0.075** | ⚡ Very Fast | ⭐⭐⭐⭐ Very Good |
| Together AI | Meta-Llama-3.1-8B | $0.20 | ⚡ Fast | ⭐⭐⭐ Good |
| OpenAI | gpt-4o-mini | $0.15 | 🚀 Fast | ⭐⭐⭐⭐ Very Good |
| Anthropic | claude-3-haiku | $0.25 | 🚀 Fast | ⭐⭐⭐⭐ Very Good |

**Recommendation:** Start with **Groq** (free tier) for development. For production, **Gemini** offers the best value!

---

## Scientific Methodology

### Astrology Service
- **Swiss Ephemeris**: Astronomical calculations with <1 arc second accuracy
- **Natal Chart**: Planet positions, houses (Placidus), aspects
- **Transits**: Current planet positions vs natal chart
- **Event Forecast**: Favorability based on transits, Moon phase, retrogrades

### Dreams Service
- **Hall/Van de Castle**: Content analysis system (Case Western Reserve University, 1966)
- **DreamBank/DreamBase**: Research corpus comparison & normative data
- **REM/NREM Models**: Neurocognitive theory of sleep and dream function
- **Jungian Archetypes**: Shadow, Anima/Animus, Self, Hero, Transformation
- **Lunar Context**: Dream significance by lunar day and circadian influence
- **AI Interpreter v2.1**: JSON-based bilingual prompts with validation & confidence scoring

---

## Key Design Decisions

1. **Strict Contracts**: All API uses Pydantic models with validation
2. **Fallback Logic**: AI services have rule-based fallbacks when API unavailable
3. **Bilingual**: Full RU/EN support throughout
4. **Mobile-First**: Responsive design for mobile/tablet
5. **Voice Input**: Web Speech API for hands-free input
6. **Caching**: Redis/memory caching for natal charts

---

## Common Tasks

### Adding a new symbol to dreams knowledge base
Edit `backend/services/dreams/knowledge_base/symbols.json`

### Adding a new event type for forecasting
Edit `backend/services/astrology/schemas.py` - `EventType` enum

### Adding translations
Edit `frontend/messages/en.json` and `frontend/messages/ru.json`

---

## Testing

```bash
# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend && npm test
```

---

## Deployment

Target: **Render.com**

See `render.yaml` for configuration. Deploy requires:
1. PostgreSQL database
2. Redis (optional, for caching)
3. Environment variables set in Render dashboard

## Repo Audit Summary
- Полный аудит выполнен (frontend, backend, infra, CI, scripts). Полный отчёт: [docs/REPO_AUDIT.md](docs/REPO_AUDIT.md).
- Архитектура: Next.js 14 (App Router, next-intl), FastAPI backend с Swiss Ephemeris, Render blueprint (backend+frontend+Postgres+Redis).
- P0: Astrology endpoints ломаются на `await` синхронного geocoder → 500; backend pytest не запускается из-за импортов в несуществующие модули.
- P1: Render запускает backend в `ENVIRONMENT=development` → авто `init_db()` в проде; CORS требует явных origin со схемой.
- Лунный сервис реальный (Swiss Ephemeris/Moshier), без моков; фронт делает SSR-фетч через `getLunarDay` и клиентский догруз месяца.
- Проверить env: `NEXT_PUBLIC_*` от backend `RENDER_EXTERNAL_URL`, `LUNAR_DEFAULT_TZ`, `ALLOWED_ORIGINS`, секреты LLM/SECRET_KEY.

## Repo Map
- Frontend: `frontend/app/[locale]/(calendar)/calendar/page.tsx` (SSR lunar fetch), API proxy `frontend/app/api/lunar/route.ts`, i18n `frontend/i18n/request.ts` + `middleware.ts`, styles `frontend/tailwind.config.ts` + `styles/globals.css`, lunar clients `frontend/lib/lunar-server.ts` / `lunar-client.ts` / `lunar-endpoint.ts`.
- Backend: entry `backend/app/main.py`; routes `/api/v1/lunar`, `/api/v1/astrology`, `/api/v1/dreams`, `/health`; lunar engine `backend/services/lunar/engine.py` + tables `backend/data/lunar_tables.json`; astrology orchestrator `backend/services/astrology/service.py` + `geocoder.py`; dreams `backend/services/dreams/*`; settings `backend/core/config.py`.
- Infra/CI: `render.yaml` (backend/frontend/DB/Redis), `docker-compose.yml`, workflows in `.github/workflows/*`.

## Findings

### 🔴 P0 - CRITICAL (Found & Fixed 2025-12-30)
| Issue | Evidence | Impact | Fix | Status |
| --- | --- | --- | --- | --- |
| **LunarEngine class не существовал** | `backend/services/astrology/service.py:31` импортирует `LunarEngine`, но класса не было в `backend/services/lunar/engine.py` | ImportError при запуске astrology service → полный отказ сервиса | ✅ Создан класс `LunarEngine` с методами `get_lunar_day()` и `get_lunar_info_for_period()` | **FIXED** |
| **Гороскоп возвращал моки** | `backend/services/astrology/interpreter.py:569-574` использовал хардкод: `sections["love"] = "Благоприятный период..."` | Все гороскопы неинформативные, пользователи получают одинаковый текст | ✅ Переписан `_template_interpret_horoscope()` для использования `lunar_tables.json` | **FIXED** |
| **Один промпт для всех периодов** | `prompt_templates.py` имел только `HOROSCOPE_PROMPT` без разбивки по daily/weekly/monthly/yearly | Дневные/недельные/месячные/годовые гороскопы одинаковые по структуре | ✅ Добавлены 4 специализированных промпта | **FIXED** |

### P0 - CRITICAL (Previously Fixed)
| Issue | Evidence | Impact | Fix | Acceptance |
| --- | --- | --- | --- | --- |
| `await self.geocoder.geocode(...)` в AstrologyService при синхронном geocoder | `backend/services/astrology/service.py` lines 63-68, 133-138, 179-184; `backend/services/astrology/geocoder.py` lines 59-86 | Все astrology-эндпоинты падают 500 при первом запросе | Сделать geocode async-safe (executor) или убрать `await`; покрыть тестом | `/api/v1/astrology/natal-chart` отдаёт 201 с телом |
| Backend pytest импортирует отсутствующие `backend.services.astrology.engine.*` | `backend/tests/test_astrology_quality.py` lines 5-10 | `pytest backend/tests` валится на ImportError → CI красная | Переписать тесты под текущий модульный путь или заменить проверками актуальных сервисов | `pytest backend/tests` проходит без ImportError |

### P1/P2/P3
- P1: Render по умолчанию `ENVIRONMENT=development` ⇒ `init_db()` в проде; выставить `ENVIRONMENT=production` и управлять схемой через Alembic.
- P2: Нет логов/health-индикации режима ephemeris (SWIEPH vs MOSEPH); добавьте предупреждение при отсутствии файлов.
- P3: LunarWidget не ретраит загрузку месяца; любой 502 даёт простой error-блок вместо graceful retry.

## Render/Deploy Checklist
- Backend: `ENVIRONMENT=production`, `DATABASE_URL`/`DATABASE_URL_SYNC`, `REDIS_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS=<frontend RENDER_EXTERNAL_URL>`, ephemeris path env при наличии файлов.
- Frontend: `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_LUNAR_API_URL` = backend `RENDER_EXTERNAL_URL`, `LUNAR_DEFAULT_TZ=UTC`.
- Commands: backend `pip install -r backend/requirements.txt` → `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`; frontend `npm install --include=dev && npm run build`.

## Lunar Correctness Checklist
- `/api/v1/lunar` возвращает фазу/день с provenance (ephemeris_engine, jd_ut, timezone); данные варьируются по датам (см. `backend/tests/test_lunar_endpoint.py`).
- Контент тянется из `backend/data/lunar_tables.json` через `get_lunar_day_text` с fallback на en, без моков.
- SSR использует `getLunarDay` (tz из `LUNAR_DEFAULT_TZ`), клиент догружает месяц через `fetchLunarDayClient`.

## Security & Env Notes
- Хранить SECRET_KEY/LLM ключи в секретах Render, не в git.
- Geocoder Nominatim без ключа/лимита — добавить провайдер/квоты при проде.
- CORS: передавать origins со схемой; ALLOWED_ORIGINS по умолчанию только localhost.

## Session History

| Date | Branch | Summary |
|------|--------|---------|
| 2025-12-17 | `claude/analyze-fix-frontend-PXk9Y` | GeoNames API, timezone selector, lunar fix |
| 2025-12-18 | `claude/session-documentation-zdu0p` | Language switcher, pytest fixes |
| 2025-12-23 | `claude/oneiroscope-continuation-5S4v3` | DreamBank integration, language auto-detection, JSON prompts |
| 2025-12-23 | `claude/dream-interpreter-setup-nK52c` | Dream interpreter v2.1 upgrade (REM/NREM, prohibited list, validation) |
| 2025-12-24 | `claude/dream-interpreter-setup-nK52c` | Narrative-first semantic engine, contextual validation, 7 modern symbols |
| 2025-12-30 | `claude/timezone-geonames-integration-mDyCI` | AstroReasoner integration, structured natal chart interpretations, enhanced LLM prompts |
| 2025-12-30 | `claude/update-documentation-En0hK` | 🔴 CRITICAL FIXES: LunarEngine class, removed horoscope mocks, added period-specific prompts |
| **2025-12-30** | `claude/update-documentation-En0hK` | **✨ Dream databases analysis + Horoscope improvements (specialized prompts, ×2 detail, natal chart integration)** |

See `docs/SESSION_SUMMARY_*.md` for details.

## Status (Updated 2025-12-30 - Session 2)

### Completed (Latest Session - Part 2)
- [x] **📊 ANALYSIS**: Analyzed 4 dream databases (DreamBank, DREAMS, krank, dreamento) - full report in `docs/DREAM_DATABASES_ANALYSIS_2025-12-30.md`
- [x] **✨ HOROSCOPE IMPROVEMENTS**: Specialized prompts for each period (daily/weekly/monthly/yearly)
- [x] **✨ HOROSCOPE IMPROVEMENTS**: Increased detail ×2 (600-1000 words, max_tokens=4000)
- [x] **✨ HOROSCOPE IMPROVEMENTS**: Full personalization via natal chart (Sun/Moon/Ascendant)
- [x] **✨ HOROSCOPE IMPROVEMENTS**: Event forecasts now use natal chart data
- [x] **✅ TESTING**: All 15 astrology tests passed (provenance, quality, lunar, integration)
- [x] **📚 DOCUMENTATION**: Comprehensive guides (HOROSCOPE_IMPROVEMENTS, SESSION_SUMMARY)

### Completed (Previous Session - Part 1)
- [x] **🔴 CRITICAL FIX**: LunarEngine class created in `backend/services/lunar/engine.py:231-284`
- [x] **🔴 CRITICAL FIX**: Removed mock data from horoscope interpreter
- [x] **🔴 CRITICAL FIX**: Added real lunar_tables.json integration for horoscope generation
- [x] **✨ ENHANCEMENT**: Added 4 specialized prompt templates (daily/weekly/monthly/yearly)
- [x] **📚 DOCUMENTATION**: Created comprehensive architecture docs (ASTROLOGY_ARCHITECTURE_2025-12-30.md)

### Completed (Previous Sessions)
- [x] **P0**: Geocoder async fix (GeoNames API)
- [x] **P0**: Backend pytest passing (13 passed, 6 skipped)
- [x] **P0**: Frontend tests passing (7 passed)
- [x] Timezone selector UI (19 timezones)
- [x] Language switcher RU/EN
- [x] GeoNames configured on Render (`alpro1000`)
- [x] **DreamBank**: Hall/Van de Castle norm comparison integrated
- [x] **Symbols**: Expanded from 15 to 56 dream symbols (+7 modern)
- [x] **Language Detection**: Auto-detect RU/EN in dream text
- [x] **JSON Prompts**: Bilingual prompt system for LLM
- [x] **Interpreter v2.1**: REM/NREM models, DreamBase, prohibited list, 4-step validation, confidence scoring
- [x] **Narrative-First Approach**: LLM analyzes full dream semantics before trusting symbols
- [x] **Contextual Validation**: Programmatic filtering of false positives (house from car door)
- [x] **Modern Symbols**: surveillance, boundaries, control, escape_liberation, privacy, autonomy, technology
- [x] **Test Suite**: 14 regression tests for dream interpreter (9/14 passing - 64%)
- [x] **Documentation**: Full v2.1 architecture spec (550 lines)
- [x] **AstroReasoner Integration**: Enhanced LLM prompts for astrology interpretations
- [x] **Structured Natal Chart**: 6 detailed sections (personality, strengths, challenges, relationships, career, life_purpose)
- [x] **Context-Aware Horoscopes**: Personalized forecasts based on natal chart data

### Pending (Priority Order)
1. [ ] **P0**: Deploy horoscope improvements to staging Render
2. [ ] **P0**: A/B test new vs old horoscopes (measure engagement)
3. [ ] **P1**: Create PR for merge to main
4. [ ] **P1**: Verify production deploy
5. [ ] **P1**: `ENVIRONMENT=production` on Render
6. [ ] **P2**: Consider upgrading DreamBank to krank CSV format (~2 hours)
7. [ ] **P3**: Ephemeris health check logging
8. [ ] **P3**: LunarWidget retry logic

## Roadmap
- Phase 0 (builds green): ✅ DONE - geocoder await fixed, backend tests passing
- Phase 1 (lunar correctness): Partially done - timezone selector added, retry pending
- Phase 2 (astrology hardening): GeoNames integrated, rate limit/provenance pending
- Phase 3 (dreams enhancement): ✅ DONE - DreamBank norms, language detection, JSON prompts
- Phase 3 (QA/CI): Tests green locally, CI pipeline setup pending

## Next Actions (Updated 2025-12-30 - Session 2)

### Immediate (P0)
1) **Deploy на staging**: Развернуть улучшения гороскопов на Render staging
2) **A/B тест**: Сравнить новые (600-1000 слов) vs старые (300-500 слов) гороскопы
3) **Метрики**: Измерить engagement (reading time, scroll depth, return rate)
4) **User feedback**: Собрать обратную связь первых пользователей

### High Priority (P1)
1) Создать PR из `claude/update-documentation-En0hK` в main
2) После merge проверить production deploy на Render
3) Выставить `ENVIRONMENT=production` на Render
4) Мониторинг LLM costs (4000 tokens per request)

### Phase 2 - Astrology Frontend Integration
1) **Structured Interpretation UI**: Display 6 sections in tabs (personality, strengths, challenges, relationships, career, life_purpose)
2) **Natal Chart Persistence**: Save to localStorage for reuse in horoscopes
3) **Personalized Horoscopes**: Pass natal_chart_id to horoscope requests
4) **Transit Visualization**: Show current transits vs natal planets

### Phase 3 - Dream Interpreter Enhancements
1) **JSON Output Schema**: Add confidence, tone, semantic_sources metadata
2) **Lemmatization**: Integrate pymorphy2 for Russian morphological analysis
3) **Test Coverage**: Expand to 100% pass rate (currently 64%)
4) **A/B Testing**: Deploy v2.1 to production, collect user feedback

### Backlog
- [ ] Добавить retry логику в LunarWidget
- [ ] Добавить health/log для режима ephemeris

## Astrology Service Architecture (Updated 2025-12-30)

```
POST /api/v1/astrology/natal-chart
         │
         ▼
┌─────────────────────────────────────────┐
│      Geocoder.geocode(birth_place)      │
│   • GeoNames API (alpro1000)            │
│   • Transliteration (Москва → Moscow)   │
│   • Fallback to 90+ cities DB           │
│   • Returns: lat, lon, timezone         │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│    NatalChartCalculator.calculate()     │
│   • SwissEphemeris (SWIEPH/MOSEPH)      │
│   • Planet positions (13 planets)       │
│   • Houses (Placidus system)            │
│   • Aspects (0°, 60°, 90°, 120°, 180°)  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  AstroReasoner.interpret_natal_chart()  │
│   • Enhanced LLM prompts                │
│   • Birth context (date/time/place)     │
│   • Multi-provider LLM support          │
│   • Fallback to template interpretation │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ AstroInterpreter.interpret_structured() │
│   • Parses 6 sections:                  │
│     - personality (Sun + Ascendant)     │
│     - strengths (talents, aspects)      │
│     - challenges (growth areas)         │
│     - relationships (Venus, 7th house)  │
│     - career (MC, 10th house)           │
│     - life_purpose (Nodes)              │
└─────────────────────────────────────────┘
         │
         ▼
    NatalChartResponse
    (planets, houses, aspects, interpretation,
     structured_interpretation, provenance)
```

## Dream Analysis Architecture (Updated 2025-12-23)

```
POST /api/v1/dreams/analyze
         │
         ▼
┌─────────────────────────────────────────┐
│        _preprocess_dream_text()         │
│   • Remove repeated chars (ссс→сс)      │
│   • Normalize whitespace                │
│   • _detect_language() → ru/en          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         DreamAnalyzer.analyze()         │
│   • 50 symbols (symbols.json)           │
│   • Content analysis (H/VdC)            │
│   • Emotion + themes + archetypes       │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│    DreamBankLoader.compare_to_norms()   │
│   • hvdc_norms.json (1966 study)        │
│   • Male/Female character ratio         │
│   • Aggression/Friendliness index       │
│   • Typicality score 0-100%             │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│       DreamInterpreter (LLM) v2.1       │
│   • JSON prompt (auto-locale)           │
│   • dream_interpreter_system.json       │
│   • 4-step validation (meaningful?)     │
│   • Prohibited: эзотерика, гадание      │
│   • Confidence indicators               │
│   • REM/NREM + DreamBase methodology    │
│   • Fallback to inline prompts          │
└─────────────────────────────────────────┘
         │
         ▼
    DreamAnalysisResponse
    (symbols, content, norm_comparison,
     interpretation, recommendations)
```
