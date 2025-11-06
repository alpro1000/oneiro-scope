# OneiroScope/СоноГраф — Дорожная карта развития

## Обзор

Дорожная карта описывает эволюцию сервиса анализа снов от MVP до полнофункциональной платформы с мобильными приложениями и масштабируемой инфраструктурой.

---

## 🎯 Milestone 1: MVP (Weeks 1-4)

**Цель**: Запустить минимально жизнеспособный продукт с базовым функционалом анализа снов

### MVP Scope

#### ✅ Core Features
- **Ввод снов**: текстовая форма (web)
- **LLM-анализ**: интеграция с OpenAI GPT-4o-mini
- **Лунный календарь**: расчет лунного дня и значимости сна
- **Базовая интерпретация**: архетипы, настроение, символы
- **Freemium модель**: 1 бесплатный анализ, далее блокировка с предложением оплаты

#### 🏗️ Technical Stack
```yaml
Frontend:
  - Framework: Next.js 14 (App Router)
  - UI: TailwindCSS + shadcn/ui
  - State: React Query + Zustand
  - i18n: next-intl (RU/EN)

Backend:
  - API: FastAPI (Python 3.11+)
  - Database: PostgreSQL 15
  - Cache: Redis 7
  - LLM: OpenAI GPT-4o-mini
  - Lunar: pyephem/astral

Infrastructure:
  - Hosting: Render (web service + PostgreSQL)
  - CDN: Vercel Edge (frontend)
  - Monitoring: Sentry
```

#### 📋 MVP Tasks

**Week 1: Foundation**
- [ ] Настроить монорепо структуру
- [ ] Развернуть базовый FastAPI сервер
- [ ] Настроить PostgreSQL + миграции (Alembic)
- [ ] Создать базовую Next.js структуру
- [ ] Настроить i18n (RU/EN)

**Week 2: Lunar Engine + LLM Integration**
- [ ] Реализовать модуль расчета лунных дней (`backend/services/lunar`)
- [ ] Создать таблицу значений лунных дней (JSON/DB)
- [ ] Интегрировать OpenAI API с retry logic
- [ ] Создать промт-инжиниринг для анализа снов
- [ ] Реализовать endpoint `POST /api/v1/dreams/analyze`

**Week 3: Frontend + User Flow**
- [ ] Создать форму ввода сна
- [ ] Реализовать компонент отображения анализа
- [ ] Добавить лунный виджет
- [ ] Реализовать freemium логику (1 бесплатный анализ)
- [ ] Настроить аналитику (Plausible/PostHog)

**Week 4: Polish + Launch**
- [ ] E2E тестирование (Playwright)
- [ ] Оптимизация производительности
- [ ] SEO оптимизация
- [ ] Подготовка landing page
- [ ] Soft launch + мониторинг

#### 🎯 MVP Success Criteria
- ✅ P95 latency анализа < 2s
- ✅ Поддержка RU/EN
- ✅ 99% uptime
- ✅ Первые 100 пользователей могут получить анализ
- ✅ 0 критических багов в production

---

## 🚀 Milestone 2: Масштабирование (Weeks 5-12)

**Цель**: Расширить функционал, добавить монетизацию и интеграции

### Phase 2.1: Voice Input (Weeks 5-6)

#### Features
- ASR (Automatic Speech Recognition) через Whisper
- Веб-интерфейс для записи голоса
- Мобильный-friendly аудио ввод
- Telegram bot для голосовых сообщений

#### Technical Details
```yaml
ASR Stack:
  - Model: OpenAI Whisper large-v3
  - Fallback: Vosk (offline)
  - Format: WebM/Ogg/MP3
  - Max duration: 3 minutes
  - Language detection: automatic (RU/EN)

Backend:
  - Endpoint: POST /api/v1/dreams/transcribe
  - Storage: Temporary (auto-delete after 24h)
  - Queue: Celery + Redis for async processing
```

#### Tasks
- [ ] Интегрировать Whisper API
- [ ] Создать endpoint для загрузки аудио
- [ ] Реализовать фронтенд компонент записи
- [ ] Добавить прогресс-индикатор транскрибации
- [ ] Настроить Telegram bot для голоса

### Phase 2.2: Monetization (Weeks 6-8)

#### Features
- Stripe/YooKassa интеграция
- Два тарифа:
  - **Pay-per-use**: $2.99 за анализ
  - **Subscription**: $5.99/мес за 10 анализов
- Личный кабинет с историей платежей
- Email уведомления

#### Technical Details
```yaml
Payment Stack:
  - Global: Stripe Checkout + Webhooks
  - Russia: YooKassa API
  - Database: payment_transactions, subscriptions tables
  - Idempotency: request_id tracking

Pricing Model:
  - Free tier: 1 dream analysis
  - Pay-per-dream: $2.99 USD
  - Monthly: $5.99 USD (10 dreams)
  - Annual: $59.99 USD (unlimited)
```

#### Tasks
- [ ] Настроить Stripe/YooKassa аккаунты
- [ ] Создать payment endpoints
- [ ] Реализовать webhook handlers
- [ ] Создать subscription management UI
- [ ] Настроить email notifications (SendGrid/Resend)
- [ ] Добавить invoice генерацию

### Phase 2.3: Telegram Integration (Weeks 7-8)

#### Features
- Полнофункциональный Telegram bot
- Команды: `/start`, `/analyze`, `/lunar`, `/history`, `/subscribe`
- Inline кнопки для навигации
- Rich formatting для ответов
- Аутентификация через Telegram ID

#### Technical Details
```yaml
Bot Stack:
  - Framework: python-telegram-bot 20.x
  - Deploy: Render background worker
  - Webhook: HTTPS endpoint
  - Rate limiting: 3 requests/minute per user

Commands:
  - /start - Приветствие + регистрация
  - /analyze - Анализ сна (текст/голос)
  - /lunar - Текущий лунный день
  - /history - История анализов
  - /subscribe - Управление подпиской
  - /help - Справка
```

#### Tasks
- [ ] Создать Telegram bot через @BotFather
- [ ] Реализовать bot handlers
- [ ] Связать Telegram ID с user accounts
- [ ] Добавить inline keyboard navigation
- [ ] Реализовать payment через Telegram Stars
- [ ] Настроить webhook delivery

### Phase 2.4: Enhanced Analysis (Weeks 9-10)

#### Features
- DreamBank integration (научная база снов)
- Hall/Van de Castle coding system
- Статистический анализ архетипов
- Персонализированные рекомендации
- Отслеживание паттернов снов

#### Technical Details
```yaml
Analysis Stack:
  - NLP: spaCy 3.7 + custom pipeline
  - Embeddings: OpenAI text-embedding-3-small
  - Vector DB: PostgreSQL + pgvector
  - HVdC Codebook: JSON schema с ~100 категориями

Enhanced Output:
  - Архетипический профиль (% по категориям)
  - Сравнение с нормами (DreamBank)
  - Recurring symbols tracking
  - Emotional trajectory (time series)
```

#### Tasks
- [ ] Интегрировать DreamBank датасет
- [ ] Реализовать HVdC классификацию
- [ ] Создать embedding pipeline
- [ ] Добавить vector similarity search
- [ ] Построить статистические нормы
- [ ] Реализовать pattern detection

### Phase 2.5: User Experience (Weeks 10-12)

#### Features
- Персональный дашборд с аналитикой
- Dream journal (дневник снов)
- Экспорт в PDF
- Email дайджесты
- Social sharing (opengraph)
- PWA поддержка

#### Technical Details
```yaml
Dashboard:
  - Charts: Recharts/Chart.js
  - Export: react-pdf
  - Email: React Email templates
  - PWA: next-pwa plugin

Analytics Widgets:
  - Лунный календарь (interactive)
  - Частотность архетипов (bar chart)
  - Эмоциональный тренд (line chart)
  - Word cloud символов
  - Streak counter (дни подряд)
```

#### Tasks
- [ ] Создать dashboard layout
- [ ] Реализовать charts и visualizations
- [ ] Добавить PDF export
- [ ] Настроить email digest (weekly)
- [ ] Конфигурировать PWA manifest
- [ ] Добавить social meta tags

---

## 📱 Milestone 3: Mobile Apps (Weeks 13-24)

**Цель**: Нативные мобильные приложения для iOS/Android

### Phase 3.1: React Native Development (Weeks 13-18)

#### Features
- Кросс-платформенное React Native приложение
- Push notifications
- Offline-first архитектура
- Биометрическая аутентификация
- Интеграция с Health/HealthKit

#### Technical Stack
```yaml
Mobile:
  - Framework: React Native 0.73 + Expo
  - Navigation: React Navigation 6
  - State: Redux Toolkit + RTK Query
  - Storage: WatermelonDB (offline)
  - Push: Expo Notifications

Native Modules:
  - Voice recording: expo-av
  - Biometrics: expo-local-authentication
  - Health: react-native-health (iOS) / Google Fit (Android)
```

#### Tasks
- [ ] Setup Expo managed workflow
- [ ] Создать navigation structure
- [ ] Портировать UI components
- [ ] Реализовать offline sync
- [ ] Добавить push notifications
- [ ] Интегрировать биометрию
- [ ] Тестирование на физических устройствах

### Phase 3.2: App Store Deployment (Weeks 19-20)

#### Tasks
- [ ] App Store Connect настройка
- [ ] Google Play Console настройка
- [ ] Подготовка screenshots и metadata
- [ ] Privacy policy и Terms of Service
- [ ] Beta testing (TestFlight + Internal Testing)
- [ ] Production release

### Phase 3.3: Platform-Specific Features (Weeks 21-24)

#### iOS Features
- [ ] Widgets (iOS 14+)
- [ ] Siri Shortcuts
- [ ] Apple Sign In
- [ ] iCloud sync

#### Android Features
- [ ] Home screen widgets
- [ ] Google Assistant actions
- [ ] Google Sign In
- [ ] Android backup

---

## 🌐 Milestone 4: Global Scale (Weeks 25-36)

**Цель**: Международная экспансия и enterprise features

### Phase 4.1: Multi-Language Support (Weeks 25-28)

#### Languages
- Tier 1: EN, RU (MVP)
- Tier 2: ES, FR, DE, PT (Week 26)
- Tier 3: ZH, JA, KO, AR (Week 28)

#### Technical
```yaml
i18n Stack:
  - Translation: Crowdin API
  - Content: markdown-based per locale
  - LLM: GPT-4 multilingual mode
  - Lunar calendar: localized names
```

### Phase 4.2: Enterprise Features (Weeks 29-32)

#### Features
- B2B API access
- White-label deployment
- Advanced analytics dashboard
- Team accounts
- SSO (SAML/OIDC)

### Phase 4.3: ML/AI Enhancements (Weeks 33-36)

#### Features
- Fine-tuned dream analysis model
- Predictive analytics (dream trends)
- Anomaly detection (sleep disorders indicators)
- Collaborative filtering (similar dreamers)

#### Technical
```yaml
ML Stack:
  - Training: Modal.com / RunPod
  - Model: LLaMA 3 70B fine-tuned
  - Vector DB: Pinecone / Weaviate
  - Monitoring: Weights & Biases
```

---

## 📊 Key Metrics

### MVP Phase
- MAU: 1,000
- Retention (D7): 30%
- Conversion: 5%
- NPS: 40+

### Scale Phase
- MAU: 10,000
- Retention (D7): 45%
- Conversion: 8%
- NPS: 50+

### Mobile Phase
- MAU: 50,000
- Retention (D7): 60%
- Conversion: 12%
- NPS: 60+

### Global Phase
- MAU: 200,000+
- Retention (D7): 65%
- Conversion: 15%
- NPS: 65+

---

## 💰 Budget Estimates

### MVP (Months 1-2)
- Development: $15,000
- Infrastructure: $200/month
- LLM API: $500/month
- Total: ~$16,400

### Scale (Months 3-6)
- Development: $40,000
- Infrastructure: $800/month
- LLM API: $2,000/month
- Payment processing: 2.9% + $0.30
- Total: ~$51,200

### Mobile (Months 7-12)
- Development: $60,000
- Infrastructure: $2,000/month
- App Store fees: $99/year (Apple) + $25 one-time (Google)
- Total: ~$72,124

### Global (Year 2)
- Development: $120,000
- Infrastructure: $8,000/month
- Enterprise: Custom pricing
- Total: ~$216,000+

---

## 🎯 Next Steps

1. **Week 1**: Kickoff MVP development
2. **Week 4**: MVP soft launch
3. **Week 8**: Public launch + marketing
4. **Week 12**: Scale features complete
5. **Week 24**: Mobile apps in stores
6. **Week 36**: Global expansion complete

---

**Document Version**: 1.0
**Last Updated**: 2025-11-01
**Owner**: Architecture Team
