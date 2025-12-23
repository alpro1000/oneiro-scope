# OneiroScope Backend (FastAPI)

Бэкенд обслуживает лунный календарь, астрологию и анализ снов через единый FastAPI-приложение с LLM-failover и базами знаний.

## Возможности
- **Lunar API**: фазы Луны, лунные дни и рекомендации (локали RU/EN).
- **Astrology API**: натальная карта, профили планет и домов, гороскопы и прогнозы.
- **Dreams API**: HVdC-категории, архетипы Юнга, словарь символов и LLM-интерпретации.
- **Инфраструктура**: CORS+GZip middleware, health/readiness/live endpoints, логирование с метками времени.
- **Форматирование натала**: два пути вывода отчётов — типизированный `ChartFormatter` для сервисного слоя и облегчённый `format_natal_chart`
  для CLI/JSON-пейлоадов (см. `docs/ASTROLOGY_FORMATTERS.md`).

## Быстрый старт
### Зависимости
- Python 3.11+
- Docker + Docker Compose (PostgreSQL, Redis)

### Установка и запуск
```bash
# 1. Установить зависимости
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Настроить окружение
cp .env.example .env  # пропишите ключи LLM и секреты

# 3. Поднять БД и кэш (из корня репозитория)
cd .. && docker-compose up -d postgres redis

# 4. Запустить API
cd backend
uvicorn backend.app.main:app --reload
```

Документация: http://localhost:8000/docs

### Переменные окружения
Минимальный набор для работы API:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/oneiroscope
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/oneiroscope
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me
ALLOWED_ORIGINS=http://localhost:3000

# LLM каскад (указывать доступные ключи)
GROQ_API_KEY=...
GEMINI_API_KEY=...
TOGETHER_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

### Структура
```
backend/
├── app/main.py             # создание FastAPI, middleware, роутеры
├── api/v1/                 # публичные маршруты
│   ├── health.py           # /health, /ready, /live
│   ├── lunar.py            # лунный календарь
│   ├── astrology.py        # натальная карта, гороскопы, прогнозы
│   └── dreams.py           # анализ снов и справочники
├── core/                   # конфигурация и инфраструктура
│   ├── config.py           # pydantic Settings, cors origins
│   ├── database.py         # async engine + session, init/close
│   ├── logging.py          # логгер с JSON/extra метаданными
│   └── llm_provider.py     # единый интерфейс и каскад LLM
├── services/               # бизнес-логика
│   ├── lunar/              # расчёты фаз и лунных дней
│   ├── astrology/          # интерпретации и профили планет/домов
│   └── dreams/             # HVdC-анализ, архетипы, LLM-интерпретации
├── models/                 # ORM-модели (база под пользователей/сессии)
└── alembic/                # миграции (при включении БД-хранилищ)
```

### Тесты
(Добавляются вместе с персистентным хранилищем.) Сейчас основной контроль — ручные проверки API/интеграций.

## Полезные команды
- Пересоздать миграции: `alembic revision --autogenerate -m "init"`
- Применить миграции: `alembic upgrade head`
- Запустить с прод-логами: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --log-level info`
