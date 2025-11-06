# OneiroScope Backend

FastAPI-based backend для сервиса анализа снов OneiroScope/СоноГраф.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15 (через Docker)
- Redis 7 (через Docker)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/alpro1000/lunar-landing.git
cd lunar-landing/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env
# Edit .env with your API keys

# 5. Start database services
cd ..
docker-compose up -d postgres redis

# 6. Run database migrations
cd backend
alembic upgrade head

# 7. Start development server
python -m backend.app.main
# Or: uvicorn backend.app.main:app --reload
```

Server will start at http://localhost:8000

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📁 Project Structure

```
backend/
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   └── env.py               # Alembic environment
├── api/                     # API endpoints
│   └── v1/
│       ├── health.py        # Health checks
│       ├── lunar.py         # Lunar calendar
│       ├── dreams.py        # Dream analysis (TODO)
│       ├── asr.py           # Speech-to-text (TODO)
│       └── billing.py       # Payments (TODO)
├── app/                     # FastAPI application
│   └── main.py              # App entry point
├── core/                    # Core utilities
│   ├── config.py            # Settings
│   ├── database.py          # Database setup
│   ├── logging.py           # Logging config
│   └── security.py          # Auth utilities
├── models/                  # SQLAlchemy models
│   ├── user.py
│   ├── dream.py
│   ├── subscription.py
│   └── transaction.py
├── services/                # Business logic (TODO)
│   ├── lunar/               # Lunar calculations
│   ├── llm/                 # LLM integration
│   ├── asr/                 # Speech recognition
│   └── billing/             # Payment processing
├── tasks/                   # Celery tasks (TODO)
└── tests/                   # Tests (TODO)
```

## 🔧 Configuration

### Environment Variables

Required:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

Optional:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
STRIPE_SECRET_KEY=sk_...
```

See `.env.example` for full list.

## 🗄️ Database

### Run Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Database Schema

```sql
users
  - id (uuid, pk)
  - email (unique)
  - telegram_id (unique)
  - free_dream_used (boolean)
  - dream_balance (integer)

dreams
  - id (uuid, pk)
  - user_id (fk → users.id)
  - text (text)
  - language (varchar)
  - source (varchar)

dream_analyses
  - id (uuid, pk)
  - dream_id (fk → dreams.id)
  - interpretation (text)
  - confidence (float)
  - lunar_day (int)

subscriptions
  - id (uuid, pk)
  - user_id (fk → users.id)
  - plan_id (varchar)
  - status (varchar)

transactions
  - id (uuid, pk)
  - user_id (fk → users.id)
  - amount_cents (integer)
  - status (varchar)
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Run specific test
pytest tests/test_lunar.py -v
```

## 📊 API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - With DB/Redis checks
- `GET /ready` - Readiness probe
- `GET /live` - Liveness probe

### Lunar (v1)
- `GET /api/v1/lunar/current` - Current lunar day
- `GET /api/v1/lunar/date/{date}` - Lunar day for date

### Dreams (Coming Soon)
- `POST /api/v1/dreams/analyze` - Analyze dream
- `GET /api/v1/dreams/{id}` - Get dream by ID
- `GET /api/v1/dreams/history` - User's dream history

### ASR (Coming Soon)
- `POST /api/v1/asr/transcribe` - Transcribe audio to text

### Billing (Coming Soon)
- `POST /api/v1/billing/checkout` - Create checkout session
- `GET /api/v1/billing/balance` - User balance
- `POST /api/v1/webhooks/stripe` - Stripe webhooks

## 🔐 Authentication

Uses JWT tokens:

```python
from backend.core.security import create_access_token, get_current_user

# Create token
token = create_access_token({"sub": user_id})

# Protected endpoint
@app.get("/protected")
async def protected(user = Depends(get_current_user)):
    return {"user_id": user["user_id"]}
```

## 📝 Development

### Code Quality

```bash
# Format code
black backend/

# Lint
ruff check backend/

# Type check
mypy backend/
```

### Adding New Endpoint

1. Create router in `api/v1/`:
```python
# api/v1/example.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def example():
    return {"message": "Hello"}
```

2. Register in `app/main.py`:
```python
from backend.api.v1 import example

app.include_router(example.router, prefix="/api/v1", tags=["Example"])
```

### Adding New Model

1. Create model in `models/`:
```python
# models/example.py
from backend.core.database import Base
from sqlalchemy import Column, String

class Example(Base):
    __tablename__ = "examples"
    id = Column(String, primary_key=True)
```

2. Import in `models/__init__.py`

3. Create migration:
```bash
alembic revision --autogenerate -m "add example table"
alembic upgrade head
```

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t oneiroscope-backend .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  oneiroscope-backend
```

### Render.com

```yaml
# render.yaml
services:
  - type: web
    name: oneiroscope-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: oneiroscope-db
          property: connectionString
```

## 📚 Documentation

- [Architecture](../docs/architecture/SYSTEM_ARCHITECTURE.md)
- [LLM Infrastructure](../docs/architecture/LLM_INFRASTRUCTURE.md)
- [Roadmap](../docs/architecture/ROADMAP.md)

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit PR

## 📄 License

[To be decided]

## 🆘 Support

- GitHub Issues: https://github.com/alpro1000/lunar-landing/issues
- Documentation: `/docs`

---

**Status**: 🚧 MVP Development (Week 1)
**Version**: 0.1.0
**Last Updated**: 2025-11-01
