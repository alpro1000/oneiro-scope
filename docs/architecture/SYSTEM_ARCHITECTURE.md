# OneiroScope/СоноГраф — Системная архитектура

## 1. Обзор системы

OneiroScope/СоноГраф — это интеллектуальный сервис анализа снов, интегрирующий научные методы (Hall/Van de Castle, DreamBank), лунный календарь и технологии искусственного интеллекта.

---

## 2. Архитектурная диаграмма (C4 Model)

### 2.1 System Context Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          OneiroScope System                              │
│                                                                          │
│  ┌────────────┐                                        ┌──────────────┐ │
│  │   Users    │──────────────────────────────────────▶│   Frontend   │ │
│  │            │                                        │   (Next.js)  │ │
│  │ - Web      │                                        │              │ │
│  │ - Mobile   │                                        │ - Web UI     │ │
│  │ - Telegram │                                        │ - Mobile PWA │ │
│  └────────────┘                                        └──────┬───────┘ │
│                                                                │         │
│                                                                ▼         │
│                                                   ┌──────────────────┐  │
│                                                   │   API Gateway    │  │
│                                                   │   (FastAPI)      │  │
│                                                   └────────┬─────────┘  │
│                                                            │            │
│              ┌──────────────┬──────────────┬──────────────┼────────┐   │
│              ▼              ▼              ▼              ▼        ▼   │
│    ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────┐ ┌───┐ │
│    │   Dream     │ │   Lunar     │ │   ASR    │ │  Billing   │ │...│ │
│    │  Analysis   │ │   Service   │ │ Service  │ │  Service   │ └───┘ │
│    │   (LLM)     │ │             │ │          │ │            │       │
│    └──────┬──────┘ └──────┬──────┘ └────┬─────┘ └─────┬──────┘       │
│           │                │             │             │              │
│           ▼                ▼             ▼             ▼              │
│    ┌──────────────────────────────────────────────────────────┐      │
│    │              Data & External Services                    │      │
│    │                                                           │      │
│    │  • PostgreSQL (user data, transactions)                  │      │
│    │  • Redis (cache, sessions)                               │      │
│    │  • Vector DB (dream embeddings)                          │      │
│    │  • OpenAI API (GPT-4o-mini)                              │      │
│    │  • Anthropic API (Claude-3-haiku)                        │      │
│    │  • Stripe/YooKassa (payments)                            │      │
│    │  • Telegram Bot API                                      │      │
│    └──────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                     Client Layer                                │  │
│   │                                                                 │  │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────────┐            │  │
│   │  │   Web    │    │  Mobile  │    │   Telegram   │            │  │
│   │  │  Browser │    │   App    │    │     Bot      │            │  │
│   │  └────┬─────┘    └────┬─────┘    └──────┬───────┘            │  │
│   └───────┼───────────────┼──────────────────┼────────────────────┘  │
│           │               │                  │                        │
│           └───────────────┴──────────────────┘                        │
│                           │                                           │
│                           ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────┐│
│   │                 API Gateway / Load Balancer                     ││
│   │                     (Nginx / Cloudflare)                        ││
│   └─────────────────────────────────────────────────────────────────┘│
│                           │                                           │
│                           ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────┐│
│   │                   Application Layer                             ││
│   │                                                                 ││
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         ││
│   │  │   Frontend   │  │   Backend    │  │   Workers    │         ││
│   │  │   Server     │  │     API      │  │   (Celery)   │         ││
│   │  │   (Next.js)  │  │  (FastAPI)   │  │              │         ││
│   │  └──────────────┘  └──────┬───────┘  └──────────────┘         ││
│   │                            │                                    ││
│   │     ┌──────────────────────┼──────────────────────┐            ││
│   │     │                      │                      │            ││
│   │     ▼                      ▼                      ▼            ││
│   │  ┌─────────┐         ┌──────────┐         ┌──────────┐        ││
│   │  │  Dream  │         │  Lunar   │         │   ASR    │        ││
│   │  │Analysis │         │ Service  │         │ Service  │        ││
│   │  │ Service │         │          │         │          │        ││
│   │  └────┬────┘         └────┬─────┘         └────┬─────┘        ││
│   │       │                   │                    │               ││
│   │       ▼                   ▼                    ▼               ││
│   │  ┌─────────┐         ┌──────────┐         ┌──────────┐        ││
│   │  │ Billing │         │  Auth    │         │  Email   │        ││
│   │  │ Service │         │ Service  │         │ Service  │        ││
│   │  └────┬────┘         └────┬─────┘         └────┬─────┘        ││
│   └───────┼───────────────────┼──────────────────────┼─────────────┘│
│           │                   │                      │               │
│           ▼                   ▼                      ▼               │
│   ┌─────────────────────────────────────────────────────────────────┐│
│   │                       Data Layer                                ││
│   │                                                                 ││
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         ││
│   │  │  PostgreSQL  │  │    Redis     │  │  Vector DB   │         ││
│   │  │              │  │              │  │ (pgvector)   │         ││
│   │  │  • Users     │  │  • Cache     │  │              │         ││
│   │  │  • Dreams    │  │  • Sessions  │  │  • Dream     │         ││
│   │  │  • Payments  │  │  • Queues    │  │   Embeddings │         ││
│   │  └──────────────┘  └──────────────┘  └──────────────┘         ││
│   └─────────────────────────────────────────────────────────────────┘│
│                           │                                           │
│                           ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────┐│
│   │                   External Services                             ││
│   │                                                                 ││
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       ││
│   │  │ OpenAI   │  │Anthropic │  │  Stripe  │  │ Telegram │       ││
│   │  │   API    │  │   API    │  │YooKassa  │  │ Bot API  │       ││
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       ││
│   └─────────────────────────────────────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Модульная архитектура

### 3.1 Backend Services

```
backend/
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── dreams.py          # Dream analysis endpoints
│       ├── lunar.py            # Lunar calendar endpoints
│       ├── asr.py              # Speech-to-text endpoints
│       ├── billing.py          # Payment endpoints
│       ├── auth.py             # Authentication endpoints
│       └── webhooks.py         # Webhook handlers
│
├── services/
│   ├── dream_analysis/
│   │   ├── __init__.py
│   │   ├── service.py          # Main orchestration
│   │   ├── llm_client.py       # LLM integration
│   │   ├── context_builder.py  # Context assembly
│   │   ├── vector_store.py     # Embedding search
│   │   └── schemas.py          # Pydantic models
│   │
│   ├── lunar/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── calculator.py       # Astronomical calculations
│   │   ├── interpreter.py      # Dream significance
│   │   └── cache.py            # Redis caching
│   │
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── whisper_client.py   # OpenAI Whisper
│   │   ├── vosk_client.py      # Offline fallback
│   │   └── audio_processor.py  # Audio handling
│   │
│   ├── billing/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── stripe_gateway.py   # Stripe integration
│   │   ├── yookassa_gateway.py # YooKassa integration
│   │   └── webhooks.py         # Payment webhooks
│   │
│   └── llm/
│       ├── __init__.py
│       ├── router.py           # Model selection
│       ├── fallback.py         # Fallback chain
│       ├── prompts.py          # Prompt templates
│       ├── quality.py          # Quality assurance
│       └── cost_control.py     # Budget management
│
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── dream.py
│   ├── transaction.py
│   ├── subscription.py
│   └── dream_analysis.py
│
├── core/
│   ├── __init__.py
│   ├── config.py               # Configuration
│   ├── database.py             # DB connection
│   ├── security.py             # Auth & security
│   └── logging.py              # Structured logging
│
└── tasks/
    ├── __init__.py
    ├── asr_tasks.py            # Async ASR processing
    ├── email_tasks.py          # Email sending
    └── analytics_tasks.py      # Analytics jobs
```

### 3.2 Frontend Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   │
│   ├── (dashboard)/
│   │   ├── page.tsx            # Dashboard home
│   │   ├── dreams/             # Dream journal
│   │   ├── analytics/          # User analytics
│   │   └── settings/           # User settings
│   │
│   ├── [locale]/
│   │   ├── page.tsx            # Localized landing
│   │   ├── analyze/            # Dream analysis
│   │   ├── calendar/           # Lunar calendar
│   │   └── pricing/            # Pricing page
│   │
│   └── api/
│       ├── auth/               # Auth endpoints
│       └── webhook/            # Client webhooks
│
├── components/
│   ├── ui/                     # shadcn/ui components
│   ├── DreamInput.tsx          # Dream input form
│   ├── DreamAnalysis.tsx       # Analysis display
│   ├── LunarWidget.tsx         # Lunar calendar
│   ├── VoiceRecorder.tsx       # Audio recording
│   └── PaymentModal.tsx        # Payment UI
│
├── lib/
│   ├── api.ts                  # API client
│   ├── auth.ts                 # Auth utilities
│   ├── i18n.ts                 # Internationalization
│   └── analytics.ts            # Analytics wrapper
│
└── styles/
    ├── globals.css
    └── tokens.css              # Design tokens
```

---

## 4. Информационная архитектура

### 4.1 Database Schema (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    telegram_id BIGINT UNIQUE,
    language VARCHAR(5) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    free_dream_used BOOLEAN DEFAULT FALSE,
    dream_balance INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Dreams
CREATE TABLE dreams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    language VARCHAR(5) NOT NULL,
    source VARCHAR(20), -- 'web', 'mobile', 'telegram', 'voice'
    audio_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Dream Analyses
CREATE TABLE dream_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dream_id UUID REFERENCES dreams(id) ON DELETE CASCADE,
    interpretation TEXT NOT NULL,
    archetypes JSONB,
    mood VARCHAR(20),
    lunar_day INTEGER,
    lunar_effect VARCHAR(20),
    confidence FLOAT,
    sources JSONB,
    model_used VARCHAR(50),
    tokens_used JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector Embeddings (using pgvector extension)
CREATE TABLE dream_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dream_id UUID REFERENCES dreams(id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dream_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    stripe_subscription_id VARCHAR(255),
    yookassa_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    gateway VARCHAR(20) NOT NULL,
    gateway_transaction_id VARCHAR(255),
    dreams_purchased INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 Caching Strategy (Redis)

```yaml
Redis Key Patterns:

# User sessions
session:{session_id} -> user_data
TTL: 7 days

# Lunar calculations
lunar:{date}:{locale} -> lunar_info
TTL: 24 hours

# LLM responses (for identical dreams)
llm_cache:{dream_hash}:{locale} -> analysis
TTL: 30 days

# Rate limiting
rate_limit:{user_id}:{resource} -> count
TTL: 1 hour

# Payment session
payment_session:{session_id} -> payment_data
TTL: 1 hour

# Dream embeddings cache
embedding:{dream_id} -> vector
TTL: 7 days
```

---

## 5. Потоки данных (Data Flows)

### 5.1 Dream Analysis Flow

```
User submits dream (text/voice)
      │
      ▼
┌─────────────────┐
│ API Gateway     │
│ • Auth check    │
│ • Rate limit    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Dream Analysis Service  │
│ 1. Check user balance   │◀────────┐
│ 2. Save dream to DB     │         │
│ 3. Generate embedding   │         │
└────────┬────────────────┘         │
         │                           │
         ▼                           │
┌─────────────────────────┐         │
│ Context Assembly        │         │
│ • Lunar info            │         │
│ • Similar dreams        │         │
│ • Symbol extraction     │         │
└────────┬────────────────┘         │
         │                           │
         ▼                           │
┌─────────────────────────┐         │
│ LLM Service             │         │
│ • Model selection       │         │
│ • Prompt construction   │         │
│ • API call with retry   │         │
│ • Fallback if needed    │         │
└────────┬────────────────┘         │
         │                           │
         ▼                           │
┌─────────────────────────┐         │
│ Quality Assurance       │         │
│ • Validate response     │         │
│ • Calibrate confidence  │         │
│ • Check hallucination   │         │
└────────┬────────────────┘         │
         │                           │
         ▼                           │
┌─────────────────────────┐         │
│ Save Analysis           │─────────┘
│ • Store in DB           │
│ • Update metrics        │
│ • Consume credit        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Return to User          │
│ • JSON response         │
│ • WebSocket update      │
│ • Push notification     │
└─────────────────────────┘
```

### 5.2 Payment Flow

```
User initiates payment
      │
      ▼
┌─────────────────────────┐
│ Frontend                │
│ • Display pricing       │
│ • Collect payment info  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Billing Service         │
│ • Create checkout       │
│ • Generate session      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Payment Gateway         │
│ (Stripe/YooKassa)       │
│ • Process payment       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Webhook Handler         │
│ • Verify signature      │
│ • Update transaction    │
│ • Credit user account   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Confirmation            │
│ • Email receipt         │
│ • Update UI             │
│ • Enable features       │
└─────────────────────────┘
```

---

## 6. Безопасность

### 6.1 Authentication & Authorization

```yaml
Authentication:
  - JWT tokens (access + refresh)
  - OAuth (Google, Apple)
  - Telegram authentication
  - Session management (Redis)

Authorization:
  - Role-based access control (RBAC)
  - Resource-level permissions
  - API key authentication (for B2B)

Security Headers:
  - HTTPS only (TLS 1.3)
  - HSTS enabled
  - CSP headers
  - X-Frame-Options: DENY
```

### 6.2 Data Protection

```yaml
At Rest:
  - PostgreSQL encryption
  - Encrypted backups
  - Secrets in env vars (not code)

In Transit:
  - TLS 1.3 for all connections
  - API key rotation
  - Webhook signature verification

PII Handling:
  - No card data stored (PCI DSS via Stripe)
  - PII sanitization before LLM calls
  - GDPR compliance (data export/deletion)
  - Opt-in analytics only
```

---

## 7. Масштабируемость

### 7.1 Horizontal Scaling

```yaml
Stateless Services (can scale horizontally):
  - FastAPI backend (multiple instances)
  - Celery workers (auto-scaling)
  - Redis cluster (sharding)

Stateful Services:
  - PostgreSQL (read replicas)
  - Redis Sentinel (HA)

Load Balancing:
  - Nginx (round-robin)
  - Cloudflare (global CDN)
```

### 7.2 Performance Targets

```yaml
Latency:
  - API response (p95): < 200ms
  - Dream analysis (p95): < 2s
  - LLM inference (p95): < 1.5s

Throughput:
  - 1,000 requests/sec (API)
  - 100 analyses/sec (LLM)

Availability:
  - 99.9% uptime (43.2 min downtime/month)
```

---

## 8. Monitoring & Observability

### 8.1 Metrics Stack

```yaml
Infrastructure:
  - Prometheus (metrics collection)
  - Grafana (dashboards)
  - Alertmanager (alerting)

Application:
  - Custom metrics (business KPIs)
  - Performance metrics
  - Error tracking (Sentry)

Logging:
  - Structured JSON logs
  - Centralized logging (ELK or Loki)
  - Log retention: 30 days
```

### 8.2 Key Dashboards

```yaml
Dashboards:
  1. System Health
     - CPU, memory, disk usage
     - Network I/O
     - Database connections

  2. Application Performance
     - Request rate
     - Latency percentiles
     - Error rates

  3. Business Metrics
     - Daily active users
     - Dream analyses
     - Revenue (MRR, ARR)
     - Conversion rate

  4. LLM Performance
     - Model usage
     - Confidence scores
     - Fallback rate
     - Cost tracking
```

---

## 9. Deployment

### 9.1 Infrastructure (Render.com)

```yaml
Services:
  frontend:
    type: "static-site"
    build: "npm run build"
    publish: "out"

  backend:
    type: "web-service"
    build: "pip install -r requirements.txt"
    start: "uvicorn main:app --host 0.0.0.0 --port 8000"
    env:
      - DATABASE_URL
      - REDIS_URL
      - OPENAI_API_KEY
    scale:
      min: 2
      max: 10

  worker:
    type: "background-worker"
    build: "pip install -r requirements.txt"
    start: "celery -A tasks worker"

  postgres:
    type: "postgresql"
    plan: "starter"
    version: "15"

  redis:
    type: "redis"
    plan: "starter"
```

### 9.2 CI/CD Pipeline

```yaml
GitHub Actions:
  on: [push, pull_request]

  jobs:
    test:
      - Lint (ruff, eslint)
      - Unit tests (pytest, jest)
      - Integration tests
      - E2E tests (Playwright)

    build:
      - Build Docker images
      - Push to registry

    deploy:
      - Deploy to staging (auto)
      - Deploy to production (manual approval)
      - Run smoke tests
      - Rollback on failure
```

---

## 10. Disaster Recovery

### 10.1 Backup Strategy

```yaml
PostgreSQL:
  - Automated daily backups
  - Point-in-time recovery (PITR)
  - Retention: 30 days
  - Cross-region replication

Redis:
  - RDB snapshots (hourly)
  - AOF persistence
  - Replica for failover

Application State:
  - Stateless design (easy recovery)
  - Config in version control
```

### 10.2 Incident Response

```yaml
Severity Levels:
  P0 (Critical):
    - System down
    - Payment processing broken
    - Data breach
    Response: Immediate (< 15 min)

  P1 (High):
    - Major feature broken
    - Performance degraded
    Response: < 1 hour

  P2 (Medium):
    - Minor feature broken
    Response: < 4 hours

  P3 (Low):
    - Cosmetic issues
    Response: < 24 hours

Runbooks:
  - LLM service down
  - Database connection issues
  - Payment webhook failures
  - High error rate
```

---

## 11. Соответствие стандартам

### 11.1 Compliance

```yaml
GDPR:
  - Right to access
  - Right to erasure
  - Data portability
  - Privacy by design

PCI DSS:
  - No card data stored
  - Handled by Stripe/YooKassa (Level 1 certified)

SOC 2 (future):
  - Security controls
  - Availability monitoring
  - Confidentiality measures
```

---

## 12. Roadmap Integration

Смотрите детальную дорожную карту в [ROADMAP.md](ROADMAP.md)

```
MVP (Weeks 1-4)
  → Scale (Weeks 5-12)
    → Mobile (Weeks 13-24)
      → Global (Weeks 25-36)
```

---

## 13. Документация модулей

Детальные спецификации:

- [ASR Module](modules/ASR_MODULE_SPEC.md) — Speech-to-text
- [Billing Module](modules/BILLING_MODULE_SPEC.md) — Payments & subscriptions
- [Lunar Module](modules/LUNAR_MODULE_SPEC.md) — Lunar calendar
- [LLM Infrastructure](LLM_INFRASTRUCTURE.md) — AI analysis

---

## 14. Технологический стек (сводка)

```yaml
Frontend:
  - Framework: Next.js 14 (App Router)
  - UI: TailwindCSS + shadcn/ui
  - State: React Query + Zustand
  - i18n: next-intl

Backend:
  - API: FastAPI (Python 3.11+)
  - ORM: SQLAlchemy
  - Validation: Pydantic v2
  - Tasks: Celery + Redis

Database:
  - Primary: PostgreSQL 15
  - Cache: Redis 7
  - Vector: pgvector extension

AI/ML:
  - LLM: OpenAI GPT-4o-mini, Claude-3-haiku
  - ASR: OpenAI Whisper, Vosk (offline)
  - Embeddings: text-embedding-3-small
  - NLP: spaCy 3.7

Infrastructure:
  - Hosting: Render.com
  - CDN: Cloudflare
  - Monitoring: Prometheus + Grafana
  - Errors: Sentry
  - Analytics: PostHog

External Services:
  - Payments: Stripe (global), YooKassa (RU)
  - Messaging: Telegram Bot API
  - Email: Resend / SendGrid
```

---

## 15. Контакты и владельцы

```yaml
Architecture Team:
  Lead: [TBD]
  Email: architecture@oneiroscope.com

Module Owners:
  Dream Analysis: [TBD]
  Lunar Service: [TBD]
  ASR Service: [TBD]
  Billing: [TBD]

Documentation:
  Location: /docs/architecture/
  Version: 1.0
  Last Updated: 2025-11-01
```

---

**Document Version**: 1.0
**Status**: Production Ready
**Approved By**: Architecture Review Board
**Date**: 2025-11-01
