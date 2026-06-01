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

### ✅ Фаза C — супер-оркестратор
- [x] `agents/orchestrator.py` — `SuperOrchestrator`:
  - **Intent router** — keyword-rules (детерминированно, без extra LLM-вызова) → `{astrology, dream, lunar}` (один или несколько).
  - **Fan-out** — `asyncio.gather` параллельно по выбранным специалистам.
  - **Merge** — single-domain поток как есть; multi-domain — с заголовками `## Domain`.
  - **Lazy instantiation** — специалист создаётся только при первом dispatch.
- [x] `agents/cli.py` — `SuperOrchestrator` по умолчанию; `--generalist` для старого пути.
- [x] `backend/tests/test_orchestrator.py` — роутинг (13 кейсов + fallback), single/multi-domain dispatch, isolation, lazy init.
- [ ] **Deferred**: context passing (`natal_chart_id` между специалистами) — требует persistence слой (§5 known issue).

### ✅ Фаза D — наблюдаемость стоимости
- [x] `backend/core/cost_tracker.py` — ключ `oneiro:cost:<provider>:<agent>:<day>:<suffix>`. `report(agent=...)` фильтрует, `group_by_agent=True` даёт breakdown.
- [x] `BaseOneiroAgent` — прокидывает `ONEIRO_AGENT_NAME=self.name` в env MCP-чайлда → пересекает process boundary без extra инфраструктуры.
- [x] `record()` явный `agent=` арг побеждает env var (для прямых вызовов сервисов).
- [x] Логирование роутинга в оркестраторе: `[orchestrator] intent=<msg> agents=[...]`.

---

## Фаза 6 — Monetization + multilingual GA

Переход от бесплатного MVP к коммерческому продукту с **двумя путями доступа** (hybrid):

1. **BYOK (free MCP)** — пользователь подключает MCP-сервер к Claude Desktop / Cursor с собственными LLM-ключами. Бесплатно, loss-leader для community/SEO.
2. **Web с подпиской** — auth, тарифы, оплата. Аудитория: **RU / EN / DE / ES / FR**.

ASR (Whisper/Vosk) **остаётся** — голосовой ввод нужен на собственном вебе для мобильных пользователей.

### Тарифная сетка (черновик)

| Tier | Цена | Что входит |
|---|---|---|
| **Free** (web) | $0 | 1 натальная карта (всего) + 1 гороскоп/день + лунный календарь без лимитов |
| **Premium** | $9 / €9 / 799₽ / мес | Unlimited гороскопы, все типы event-forecasts, unlimited анализ снов, экспорт PDF |
| **Pro (BYOK)** | $5 / €5 / 499₽ / мес | Premium + пользователь предоставляет свои LLM-ключи (мы не несём LLM-cost) — для тех, у кого свой OpenAI/Anthropic billing |
| **One-time** | $19-29 | Детальная натал-карта с аудио-нарративом, годовой персональный прогноз |
| **MCP (BYOK)** | $0 | MCP-сервер для Claude Desktop / Cursor, всё бесплатно — пользователь платит за свой Claude |

Валюты обязательно по региону: USD/EUR/RUB. CHF/GBP — по запросу.

### Фаза 6.A — Auth foundation
- [ ] `backend/models/user.py` — Pydantic + SQLAlchemy `User` (id, email, hashed_password, locale, created_at, email_verified_at).
- [ ] `backend/api/v1/auth.py` — POST `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/verify-email`, `/auth/reset-password`.
- [ ] JWT (access + refresh), `python-jose` уже в requirements.
- [ ] `Depends(get_current_user)` для защищённых эндпоинтов; обновить TODO в `backend/api/v1/astrology.py:59,102,175,...`.
- [ ] Email verification — Resend / SendGrid / Mailgun (минимально один провайдер).
- [ ] Tests: register/login flow, JWT expiry, refresh, rate-limit на брутфорс.
- [ ] Alembic миграция `users` таблицы.

### Фаза 6.B — Subscription & quota DB
- [ ] `backend/models/subscription.py` — `Subscription(user_id, tier, status, provider, provider_subscription_id, current_period_end, currency)`.
- [ ] `backend/models/usage.py` — `Usage(user_id, kind, count, period_start)` — счётчики для квот free-уровня.
- [ ] `backend/services/billing/quotas.py` — `assert_quota(user, kind)` → 402 Payment Required при превышении.
- [ ] Подключить квоты к astrology/dreams эндпоинтам (natal-chart + horoscope + analyze_dream).
- [ ] Tests: free-user квоты, premium-user без лимитов, переход на новый период (cron-job / on-demand reset).

### Фаза 6.C — Stripe integration (международный рынок: EN/DE/ES/FR)
- [ ] `backend/services/billing/stripe_provider.py` — Checkout sessions, Customer Portal, webhook handler.
- [ ] Products & Prices в Stripe Dashboard: Premium-monthly, Premium-yearly, Pro-monthly, One-time reports. Все в USD + EUR с конвертацией Stripe.
- [ ] `POST /api/v1/billing/stripe/checkout` → возвращает `checkout_url`.
- [ ] `POST /api/v1/billing/stripe/webhook` — `customer.subscription.{created,updated,deleted}`, `invoice.paid`, `invoice.payment_failed` → обновляет `Subscription` запись.
- [ ] `POST /api/v1/billing/stripe/portal` → возвращает Customer Portal URL (отмена/смена тарифа делегируется Stripe).
- [ ] Tests: webhook signature verification, idempotency (повторные webhook events), period rollover.
- [ ] **Note:** Stripe не работает с RU-картами с 2022 — обязателен YooKassa параллельно.

### Фаза 6.D — YooKassa integration (RU-рынок)
- [ ] `backend/services/billing/yookassa_provider.py` — recurring payments через YooKassa (Сбер).
- [ ] Рекуррентные платежи: создание `payment` с `save_payment_method=true`, затем автосписания.
- [ ] `POST /api/v1/billing/yookassa/checkout` → возвращает `payment_url` (форма YooKassa).
- [ ] `POST /api/v1/billing/yookassa/webhook` — `payment.succeeded`, `payment.canceled`, `refund.succeeded`.
- [ ] Tests: webhook signature, idempotency.
- [ ] **Note:** YooKassa требует юр.лицо или ИП в РФ. Если нет — альтернативы: Robokassa, Tinkoff Acquiring, или crypto-провайдер (NowPayments) для обхода санкций.

### Фаза 6.E — Pro/BYOK tier
- [ ] `backend/models/user_keys.py` — `UserLLMKey(user_id, provider, encrypted_key)` — Fernet-шифрование на `SECRET_KEY`.
- [ ] `POST /api/v1/users/me/llm-keys` — сохранить ключ.
- [ ] `UniversalLLMProvider` — поддержать per-user override ключа (новый `user_id`-aware режим).
- [ ] При активной Pro-подписке `cost_tracker` не пишет в shared bucket, а в `user_id`-namespace (информационно).
- [ ] Тарифный логика: Pro = Premium фичи + own keys → меньшая ежемесячная цена.

### Фаза 6.F — i18n DE / ES / FR (расширение существующего RU/EN)
- [ ] **Frontend** (next-intl):
  - [ ] `frontend/messages/{de,es,fr}.json` — переводы всех ключей из `en.json`. Использовать профессионального переводчика или DeepL Pro API (НЕ Google Translate для production-копии).
  - [ ] `frontend/i18n/request.ts` — добавить `de`, `es`, `fr` в `locales`.
  - [ ] `frontend/middleware.ts` — locale routing (`/de/...`, `/es/...`, `/fr/...`).
  - [ ] `Accept-Language` auto-detect на первом визите.
- [ ] **Backend**:
  - [ ] `backend/services/dreams/ai/prompts/*.json` — добавить ветки `de/es/fr` к существующим `ru/en`.
  - [ ] `backend/services/astrology/ai/prompt_templates.py` — параметризовать промпты по `locale` (сейчас bilingual ru/en строки в Python).
  - [ ] `backend/data/lunar_tables.json` — добавить ключи `de/es/fr` (нужен переводчик с астрологическим контекстом).
  - [ ] `backend/services/dreams/knowledge_base/symbols.json` — добавить `interpretation_{de,es,fr}` к 56 символам.
  - [ ] `_detect_language()` в `backend/services/dreams/analyzer.py` — расширить до 5 языков (langdetect / lingua-language-detector).
- [ ] **MCP tools**:
  - [ ] `locale` параметр расширить enum до `ru|en|de|es|fr`.
- [ ] **GeoNames**: `GEONAMES_LANG` env уже есть, fallback DB — расширить транслитерации (Berlin/Берлин/Berlín/Berlin — все ключи). 
- [ ] Tests: каждый из 5 языков → каждый endpoint возвращает корректный язык.

### Фаза 6.G — Frontend: pricing + checkout + account
- [ ] `frontend/app/[locale]/pricing/page.tsx` — 5 языков, USD/EUR/RUB по гео-IP (Cloudflare / Vercel `request.geo`).
- [ ] `frontend/app/[locale]/account/page.tsx` — текущая подписка, история платежей, BYOK key management, отмена → Stripe Customer Portal / YooKassa.
- [ ] `frontend/app/[locale]/login` + `register` + `verify-email` + `reset-password`.
- [ ] Auto-redirect to Stripe/YooKassa по region (детект на `request.geo.country`).
- [ ] Тесты Playwright: full checkout flow (Stripe test mode), регистрация → email-verify → подписка → cancel.

### Фаза 6.H — Email transactional
- [ ] `backend/services/email/provider.py` — Resend или SendGrid (Resend дешевле и проще).
- [ ] Шаблоны (multilingual): welcome, email-verify, password-reset, subscription-receipt, payment-failed, subscription-cancelled.
- [ ] Email templates в 5 языках (`backend/services/email/templates/{lang}/...`).
- [ ] Tests: рендеринг шаблонов на каждом языке.

### Фаза 6.I — Compliance & data ops
- [ ] GDPR data export — `GET /api/v1/users/me/data-export` → ZIP со всеми чартами/снами/историей.
- [ ] GDPR data delete — `DELETE /api/v1/users/me` → soft-delete + hard-purge через 30 дней.
- [ ] Cookie banner (нужен для EU аудитории — DE/ES/FR).
- [ ] Privacy Policy + Terms of Service (5 языков).
- [ ] Webhook + cron на retention снов/чартов: пользователь сам выбирает срок хранения dream-text (privacy-чувствительные данные).

### Definition of Done (Фаза 6)
- Пользователь из 🇷🇺/🇺🇸/🇩🇪/🇪🇸/🇫🇷 может зарегистрироваться, оплатить Premium через Stripe (или YooKassa для RU), получить unlimited доступ ко всем сервисам в своём языке.
- Pro/BYOK путь работает: пользователь добавляет свой Anthropic-ключ, его запросы идут через его ключ.
- MCP-сервер остаётся бесплатным (не требует auth) — отдельный config-флаг `MCP_REQUIRE_AUTH=false` (default).
- Quota enforcement: free-юзер видит 402 при превышении лимитов, с CTA «upgrade to Premium».
- `cost_tracker` показывает per-user-mode + per-tier breakdown в `/api/v1/admin/cost`.
- Все 5 языков покрыты тестами e2e (Playwright или Cypress).

### Open questions перед началом Фазы 6
1. **Юр.лицо для YooKassa** — есть ли ИП/ООО в РФ? Если нет — RU-pay через Robokassa (мягче по требованиям) или crypto-провайдер?
2. **Stripe Account** — какая страна? От этого зависит payout (нужен local bank account).
3. **Email-провайдер** — Resend (минималистично, дешевле) vs SendGrid (зрелее, дороже)?
4. **Переводчик контента** — DeepL Pro API для UI ($/месяц) или ручной перевод? Для lunar-tables / dream-symbols обязателен носитель языка — это **не** машинный перевод.
5. **Free-tier лимиты** — 1 натал на всю жизнь жёстко, или 1/месяц? Влияет на conversion.

---

## Definition of Done

- `python -m backend.mcp.server` запускается, регистрирует ≥8 tools
- Claude Desktop / Cursor может подключиться по stdio и вызвать `natal_chart`
- `python -m agents.cli natal "1990-05-15 12:00 Moscow"` возвращает структурированную натал-карту
- `/natal` skill работает в Claude Code
- `pytest backend/tests/test_mcp_smoke.py` зелёный
- Все изменения в `claude/eager-noether-5UQJR`, PR не создаётся пока не попросят
