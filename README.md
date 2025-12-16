# OneiroScope / СоноГраф

Полноценный full-stack сервис для астрологии, лунного календаря и анализа снов. Фронтенд (Next.js 14) и бэкенд (FastAPI) работают в связке через реальные API: лунный календарь, астрологические интерпретации и HVdC-анализ снов, дополненные LLM-интерпретациями с каскадом провайдеров.

## Возможности
- **Лунный календарь**: точные расчёты фаз и лунных дней, рекомендации по дню и символика для снов.
- **Астрология**: натальная карта, гороскоп, прогнозы и профили планет/домов (реальные API, без моков).
- **Анализ снов**: Hall/Van de Castle контент-анализ, архетипы Юнга, словарь символов и LLM-интерпретации.
- **Голосовой ввод**: веб-распознавание речи на фронтенде, интеграция с формой снов.
- **LLM failover**: универсальный провайдер (Groq → Gemini → Together → OpenAI → Anthropic) с rule-based fallback.

## Архитектура
- **Frontend**: Next.js App Router, локализация `next-intl`, UI-компоненты (Accordion, motion), клиентские SDK для всех сервисов.
- **Backend**: FastAPI с маршрутами `/api/v1/lunar`, `/api/v1/astrology`, `/api/v1/dreams`, health endpoints и middleware (CORS, gzip, логирование).
- **Данные и сервисы**: PostgreSQL + Redis (Docker Compose), шина LLM-провайдеров, базы знаний для астрологии и снов.
- **Инфраструктура**: `render.yaml` blueprint поднимает Postgres, Redis, backend и frontend на Render; локальная разработка через Docker Compose или standalone.

### Новые интеграции (DReAMy + pyswisseph)
- Семантическое обогащение на базе [DReAMy](https://github.com/lorenzoscottb/DReAMy) (эмбеддинги, токенизация, тематические теги).
- Астрономические метаданные через [pyswisseph](https://github.com/astrorigin/pyswisseph) (фазы Луны и расчёты по дате).
- Источник атрибуции для интеграций: `config/sources_registry.json`.

#### Запуск обогащённого ETL
```bash
pip install -r requirements.txt
python etl/pipeline.py            # сохранит data/dreams_enriched.parquet
python etl/pipeline.py --check    # прогон без сохранения
pytest tests/test_integration_dreamy_swisseph.py
```

## Быстрый старт
### Требования
- Node.js 18+, npm
- Python 3.11+
- Docker + Docker Compose (для Postgres/Redis)

### Локальный запуск
1. **Бэкенд**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # укажите ключи LLM и БД
   cd .. && docker-compose up -d postgres redis
   cd backend && uvicorn backend.app.main:app --reload
   ```
   API: http://localhost:8000/docs

2. **Фронтенд**
   ```bash
   cd frontend
   npm ci
   cp .env.example .env.local  # пропишите NEXT_PUBLIC_LUNAR_API_URL и ключи LLM, если используете SSR-запросы
   npm run dev
   ```
   UI: http://localhost:3000

3. **Данные**
   - ETL и примерные наборы лежат в `data/` и `backend/services/*/knowledge_base`.
   - Для точных астрономических расчётов в продакшене установите Swiss Ephemeris (`pyswisseph`).

## Тесты
- Frontend unit-тесты: `cd frontend && npm test`
- Frontend lint: `cd frontend && npm run lint`
- (Backend тесты будут добавлены вместе с БД-хранилищем снов/гороскопов.)

## Деплой на Render
Полный пошаговый blueprint-гайд: [docs/deployment-render.md](docs/deployment-render.md).

## Документация
- Архитектура и дорожная карта: `docs/architecture/`
- LLM-провайдеры и конфигурация: `docs/LLM_PROVIDERS.md`
- Расширенный план внедрения: `docs/implementation-plan.md`
