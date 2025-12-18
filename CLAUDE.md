# CLAUDE.md - OneiroScope Project Guide

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
- **Hall/Van de Castle**: Content analysis system (Case Western Reserve University)
- **DreamBank**: Research corpus comparison
- **Jungian Archetypes**: Shadow, Anima/Animus, Self, Hero, Transformation
- **Lunar Context**: Dream significance by lunar day

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

## Status (Updated 2025-12-18)

### ✅ Resolved Issues
- ✅ **P0 Geocoder await fix** - Исправлено в сессии 2025-12-17 с GeoNames API
- ✅ **P1 ENVIRONMENT=development** - Исправлено в render.yaml, теперь `ENVIRONMENT=production`
- ✅ **TypeScript build errors** - Добавлено поле timezone в LunarDayPayload
- ✅ **CI/CD тесты** - Jest и Playwright разделены, все тесты проходят
- ✅ **Frontend UX** - Добавлена навигация, Header, favicon, брендинг

### 🔴 Remaining P0/P1 Issues
- 🔴 **Backend pytest** - Всё ещё импортирует несуществующие модули (`backend.services.astrology.engine.*`)

### 🟡 P2/P3 Issues
- P2: Нет логов/health-индикации режима ephemeris (SWIEPH vs MOSEPH)
- P3: LunarWidget не ретраит загрузку месяца при ошибках
- P3: Backend тесты нуждаются в обновлении

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

## Roadmap
- Phase 0 (builds green): исправить geocoder await; починить backend тесты; выставить `ENVIRONMENT=production` на Render. Acceptance: `pytest backend/tests` зелёный; Render деплой без `init_db()` логов; astrology endpoints 2xx.
- Phase 1 (lunar correctness): лог/health ephemeris режима; тест на вариативность lunar_day; retry в LunarWidget. Acceptance: health показывает режим, UI месяц разный по датам, тесты ловят константный lunar_day.
- Phase 2 (astrology hardening): строгий геокодинг с rate limit/provenance; обработка timezone ошибок; валидаторы орбов/applying. Acceptance: geocode ошибки = 400 с кодом; аспектные тесты на текущем движке.
- Phase 3 (QA/CI): CI job для backend pytest + frontend lint/test; проверки provenance/source в ответах. Acceptance: pipeline зелёный, регрессия на `source=backend`/provenance проходит.

## Session History

### 2025-12-18: Build & Deploy Fixes ([SESSION_SUMMARY](docs/SESSION_SUMMARY_2025-12-18.md))
- ✅ Исправлены TypeScript build errors (timezone field)
- ✅ Добавлена навигация, Header, favicon, брендинг
- ✅ Исправлен ENVIRONMENT=production для backend
- ✅ Исправлены CI/CD: Playwright TransformStream, Jest/e2e разделение, YAML syntax
- **Branch:** `claude/continue-oneiroscope-LgRZe` (9 коммитов)
- **Result:** Готово к production деплою ✨

### 2025-12-17: Timezone & GeoNames ([SESSION_SUMMARY](docs/SESSION_SUMMARY_2025-12-17.md))
- ✅ Исправлена проблема с "двумя 27-ми днями" (timezone UTC→Europe/Moscow)
- ✅ Интегрирован GeoNames API для геокодинга (P0 fix)
- ✅ Добавлен UI выбора timezone с сохранением в localStorage
- **Branch:** `claude/analyze-fix-frontend-PXk9Y`

## Next Actions

### Immediate (после деплоя)
1) ✅ ~~Прописать `ENVIRONMENT=production` в Render~~ - DONE
2) Проверить что деплой на Render прошёл успешно
3) Протестировать live окружение (timezone selector, навигация, API endpoints)
4) Проверить логи backend - должен быть `Environment: production`, без `init_db()` на старте

### High Priority
5) **P0**: Исправить backend pytest импорты (`backend.services.astrology.engine.*`)
6) **P2**: Добавить health check для режима ephemeris (SWIEPH vs MOSEPH)
7) **P3**: Добавить retry/backoff в LunarWidget для загрузки месяца
8) Добавить переключатель языка RU/EN в Header

### Future Enhancements
9) Реализовать функционал на страницах astrology и dreams
10) Улучшить mobile responsive design
11) Добавить error boundaries и loading states
12) Интеграция с Claude API для AI интерпретаций
