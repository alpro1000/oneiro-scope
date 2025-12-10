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

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

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
