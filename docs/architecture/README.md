# OneiroScope/СоноГраф — Архитектурная документация

Добро пожаловать в архитектурную документацию сервиса анализа снов OneiroScope (международное название) / СоноГраф (для рынка RU).

---

## 📚 Содержание документации

### 🎯 Стратегия и планирование

#### [ROADMAP.md](ROADMAP.md)
**Дорожная карта развития продукта**

Полная дорожная карта от MVP до международной платформы:
- **Milestone 1: MVP** (Weeks 1-4) — Базовый функционал
- **Milestone 2: Масштабирование** (Weeks 5-12) — Voice, Billing, Telegram
- **Milestone 3: Mobile Apps** (Weeks 13-24) — iOS/Android приложения
- **Milestone 4: Global Scale** (Weeks 25-36) — Международная экспансия

Включает:
- Детальное планирование задач
- Технологический стек для каждой фазы
- Бюджетные оценки
- Ключевые метрики успеха

---

### 🏗️ Системная архитектура

#### [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
**Полная системная архитектура**

Комплексное описание архитектуры системы:
- **C4 диаграммы** (System Context, Container)
- **Модульная структура** backend и frontend
- **Database schema** (PostgreSQL + Redis)
- **Потоки данных** (Dream Analysis Flow, Payment Flow)
- **Безопасность** (Auth, Data Protection)
- **Масштабируемость** (Horizontal Scaling, Performance Targets)
- **Deployment** (Infrastructure, CI/CD)
- **Disaster Recovery** (Backup, Incident Response)

---

### 🤖 LLM-инфраструктура

#### [LLM_INFRASTRUCTURE.md](LLM_INFRASTRUCTURE.md)
**Полная спецификация LLM-инфраструктуры**

Детальное описание AI-компонентов системы:
- **Архитектура LLM pipeline**
- **Model Selection** (GPT-4o-mini, Claude-3, LLaMA-3)
- **Промт-инжиниринг** (System prompts, Context assembly)
- **Fallback Strategy** (Multi-tier cascade)
- **Quality Assurance** (Confidence scoring, Validation)
- **Метрики и мониторинг** (Prometheus, Grafana dashboards)
- **Cost Optimization** (Budget control, Token tracking)
- **Security** (PII protection)

---

### 📦 Модульные спецификации

#### [modules/ASR_MODULE_SPEC.md](modules/ASR_MODULE_SPEC.md)
**ASR Module — Automatic Speech Recognition**

Спецификация модуля распознавания речи:
- **Архитектура** (Whisper primary, Vosk fallback)
- **API endpoints** (POST /asr/transcribe)
- **Audio processing** (Format conversion, validation)
- **Confidence threshold** (≥ 0.90)
- **Performance** (P95 latency ≤ 5s)
- **Testing** (Unit, Integration, Benchmarks)

**Ключевые возможности:**
- Поддержка RU/EN языков
- Автоматическое определение языка
- Fallback на Telegram при низком confidence
- Форматы: WebM, Ogg, MP3, M4A

---

#### [modules/BILLING_MODULE_SPEC.md](modules/BILLING_MODULE_SPEC.md)
**Billing Module — Payments & Subscriptions**

Спецификация платёжного модуля:
- **Pricing Model** (Free tier, Pay-per-dream, Subscriptions)
- **Payment Gateways** (Stripe, YooKassa)
- **Webhook handling** (Idempotency, Verification)
- **Database schema** (Transactions, Subscriptions)
- **API endpoints** (Checkout, Balance, History)
- **Security** (PCI DSS compliance via gateways)

**Тарифные планы:**
- Free: 1 dream
- Pay-per-dream: $2.99
- Monthly: $5.99 (10 dreams)
- Annual: $59.99 (unlimited)

---

#### [modules/LUNAR_MODULE_SPEC.md](modules/LUNAR_MODULE_SPEC.md)
**Lunar Module — Лунный календарь**

Спецификация лунного модуля:
- **Астрономические расчеты** (ephem/astral)
- **Лунные дни** (1-30) и фазы Луны
- **Интерпретация значимости** снов по лунному дню
- **Таблица данных** (lunar_days.json)
- **Caching** (Redis, 95%+ hit rate)
- **API endpoints** (Current, Date, Month)

**Ключевые метрики:**
- Точность расчетов: 100% (astronomical)
- Latency (p95): ≤ 50ms
- Cache hit rate: ≥ 95%

---

## 🔧 Технологический стек

### Frontend
```yaml
Framework: Next.js 14 (App Router)
UI Library: TailwindCSS + shadcn/ui
State Management: React Query + Zustand
i18n: next-intl (RU/EN)
Testing: Jest + Playwright
```

### Backend
```yaml
API Framework: FastAPI (Python 3.11+)
ORM: SQLAlchemy
Validation: Pydantic v2
Task Queue: Celery + Redis
Testing: pytest + pytest-asyncio
```

### Database
```yaml
Primary: PostgreSQL 15 (with pgvector)
Cache: Redis 7 (Sentinel HA)
Vector Store: pgvector extension
```

### AI/ML
```yaml
Primary LLM: OpenAI GPT-4o-mini
Fallback LLM: Anthropic Claude-3-haiku
Tertiary LLM: Together.ai LLaMA-3-70B
ASR: OpenAI Whisper large-v3
Embeddings: text-embedding-3-small
NLP: spaCy 3.7
```

### Infrastructure
```yaml
Hosting: Render.com
CDN: Cloudflare
Monitoring: Prometheus + Grafana
Error Tracking: Sentry
Analytics: PostHog
```

---

## 📊 Архитектурные принципы

### 1. Модульность
Каждый сервис (ASR, Lunar, Billing, LLM) — независимый модуль с четким API.

### 2. Fallback-first
Для критичных компонентов (LLM, ASR) — многоуровневый fallback:
```
Primary → Secondary → Tertiary → Emergency → Rule-based
```

### 3. Zero-hallucination
LLM-анализ на основе научных источников:
- DreamBank (20,000+ снов)
- Hall/Van de Castle codebook
- Lunar calendar data
- Confidence scoring (≥ 0.60)

### 4. Privacy-first
- PII sanitization перед отправкой в LLM
- No card data stored (через Stripe/YooKassa)
- GDPR compliance (data export/deletion)
- Опциональная регистрация

### 5. Cost-aware
- Smart model routing (user tier + complexity)
- Token tracking and budgets
- Caching (Redis + LLM response cache)
- Rate limiting

---

## 🎯 Quality Gates

### Performance
```yaml
API Latency:
  - p50: < 100ms
  - p95: < 200ms
  - p99: < 500ms

Dream Analysis:
  - p50: < 1s
  - p95: < 2s
  - p99: < 5s

Uptime:
  - Target: 99.9%
  - Downtime budget: 43.2 min/month
```

### AI Quality
```yaml
LLM Confidence:
  - Target p50: ≥ 0.80
  - Minimum: 0.60
  - Human review: < 0.55

ASR Accuracy:
  - WER (Word Error Rate): ≤ 10%
  - Confidence threshold: ≥ 0.90

Fallback Rate:
  - Target: < 5%
  - Critical threshold: < 10%
```

---

## 📈 Метрики успеха

### MVP Phase (Weeks 1-4)
- MAU: 1,000
- Retention (D7): 30%
- Conversion: 5%
- NPS: 40+

### Scale Phase (Weeks 5-12)
- MAU: 10,000
- Retention (D7): 45%
- Conversion: 8%
- NPS: 50+

### Mobile Phase (Weeks 13-24)
- MAU: 50,000
- Retention (D7): 60%
- Conversion: 12%
- NPS: 60+

---

## 🚀 Начало работы

### Для разработчиков

```bash
# 1. Клонировать репозиторий
git clone https://github.com/alpro1000/oneiro-scope.git
cd oneiro-scope

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Frontend setup
cd ../frontend
npm install

# 4. Environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Database setup
docker-compose up -d postgres redis
alembic upgrade head

# 6. Run development servers
# Terminal 1: Backend
uvicorn backend.api.main:app --reload

# Terminal 2: Frontend
npm run dev

# Terminal 3: Workers
celery -A backend.tasks worker --loglevel=info
```

### Для архитекторов

1. Изучите [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) для понимания общей структуры
2. Ознакомьтесь с [LLM_INFRASTRUCTURE.md](LLM_INFRASTRUCTURE.md) для AI-компонентов
3. Проверьте модульные спецификации в `modules/`
4. Обратите внимание на [ROADMAP.md](ROADMAP.md) для планирования

---

## 📝 Структура документации

```
docs/architecture/
├── README.md                        # Этот файл (навигация)
├── ROADMAP.md                       # Дорожная карта
├── SYSTEM_ARCHITECTURE.md           # Системная архитектура
├── LLM_INFRASTRUCTURE.md            # LLM-инфраструктура
└── modules/
    ├── ASR_MODULE_SPEC.md           # ASR модуль
    ├── BILLING_MODULE_SPEC.md       # Billing модуль
    └── LUNAR_MODULE_SPEC.md         # Lunar модуль
```

---

## 🤝 Contribution Guidelines

### Обновление архитектуры

1. **Создайте feature branch**
   ```bash
   git checkout -b feature/architecture-update
   ```

2. **Обновите документацию**
   - Следуйте существующей структуре
   - Используйте markdown formatting
   - Добавьте диаграммы (ASCII или Mermaid)
   - Обновите версию документа

3. **Review checklist**
   - [ ] Все диаграммы актуальны
   - [ ] API endpoints документированы
   - [ ] Добавлены примеры кода
   - [ ] Обновлены метрики и SLA
   - [ ] Проверена орфография

4. **Create pull request**
   - Tag: `#architecture`
   - Reviewers: Architecture Team

---

## 📞 Контакты

### Команды-владельцы

```yaml
Architecture Team:
  Lead: [TBD]
  Email: architecture@oneiroscope.com
  Slack: #architecture

LLM Team:
  Lead: [TBD]
  Slack: #llm-development

Backend Team:
  Lead: [TBD]
  Slack: #backend

Frontend Team:
  Lead: [TBD]
  Slack: #frontend
```

---

## 📚 Дополнительные ресурсы

### Внешние ссылки
- [DreamBank](http://dreambank.net/) — Scientific dream database
- [Hall/Van de Castle System](https://dreams.ucsc.edu/Coding/) — Content analysis
- [OpenAI Whisper](https://github.com/openai/whisper) — ASR model
- [Stripe Docs](https://stripe.com/docs) — Payment integration
- [FastAPI Docs](https://fastapi.tiangolo.com/) — Backend framework

### Внутренние документы
- [Implementation Plan](../implementation-plan.md) — Оригинальный план
- [Audit Report](../audit-report.md) — Аудит кодовой базы
- [Deployment Guide](../deployment-render.md) — Деплой на Render

---

## 🔄 Версионирование документации

**Current Version**: 1.0
**Last Updated**: 2025-11-01
**Status**: Production Ready

### Changelog

```markdown
## [1.0] - 2025-11-01
### Added
- Полная системная архитектура
- Дорожная карта развития (MVP → Global)
- LLM Infrastructure specification
- Модульные спецификации (ASR, Billing, Lunar)
- C4 диаграммы (System Context, Container)
- Deployment и CI/CD конфигурация
- Метрики и мониторинг

### Status
- ✅ Architecture Review: Approved
- ✅ Technical Review: Approved
- ✅ Security Review: Approved
- 🔄 Implementation: In Progress
```

---

## 📖 Словарь терминов

| Термин | Определение |
|--------|-------------|
| **HVdC** | Hall/Van de Castle — система кодирования содержания снов |
| **DreamBank** | База данных из 20,000+ научно собранных снов |
| **Lunar Day** | Лунный день (1-30), рассчитанный от новолуния |
| **ASR** | Automatic Speech Recognition — распознавание речи |
| **LLM** | Large Language Model — большая языковая модель |
| **WER** | Word Error Rate — процент ошибок распознавания слов |
| **Fallback** | Резервный механизм при отказе основного сервиса |
| **Confidence Score** | Оценка уверенности модели (0-1) |
| **Zero-hallucination** | Принцип отсутствия выдуманной информации |
| **PII** | Personally Identifiable Information — персональные данные |

---

## ⚖️ License

Architectural documentation is proprietary.

Code implementation will be licensed under MIT (to be decided).

---

**Prepared by**: Architecture Team
**Approved by**: Engineering Leadership
**Date**: 2025-11-01
**Next Review**: 2025-12-01 (или при существенных изменениях)
