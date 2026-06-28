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

## Фаза 6 — Monetization + multilingual GA + mobile apps

**Pivoted 2026-06-14:** owner is solo founder in EU, no юр.лицо. Adopting **Lemon Squeezy as Merchant of Record (MoR)** — Lemon Squeezy is the seller of record, handles EU VAT (one-stop shop), US sales tax, KYC, chargebacks, refunds. We just call their API and read webhooks. Stripe / YooKassa **NOT used**. RU customers can pay via Lemon Squeezy (cards work through MoR).

Audience: **EU primary** (DE/ES/FR/EN) + RU via MoR. Mobile: **iOS + Android** via Capacitor wrap of the Next.js frontend (one codebase, native shells).

ASR (Whisper/Vosk) **остаётся** — owner builds the web/mobile frontend; voice input is mobile UX.

### Тарифная сетка

| Tier | Цена | Что входит |
|---|---|---|
| **Free** (web/mobile) | $0 | 1 натальная карта (всего) + 1 гороскоп/день + лунный календарь без лимитов |
| **Premium** | $9.99 / €9.99 / 999₽ / мес | Unlimited гороскопы, все event-forecasts, unlimited анализ снов, экспорт PDF |
| **Pro (BYOK)** | $5.99 / €5.99 / 599₽ / мес | Premium + пользователь подключает свои LLM-ключи — для экономии у тех, у кого свой Anthropic/OpenAI billing |
| **One-time** | $19-29 | Детальная натал-карта с PDF + аудио-нарративом, годовой персональный прогноз |
| **MCP (BYOK)** | $0 | MCP-сервер для Claude Desktop / Cursor, всё бесплатно — пользователь платит за свой Claude |

Lemon Squeezy auto-converts USD/EUR; локально показываем валюту по гео-IP.

### Фаза 6.A — Auth foundation
- [ ] `backend/models/user.py` — добавить `password_hash`, `name`, `lemon_customer_id` к существующей таблице.
- [ ] `backend/api/v1/auth.py` — POST `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`.
- [ ] Использовать существующий `backend/core/security.py` (JWT, bcrypt уже готовы).
- [ ] `Depends(get_current_user_from_db)` — возвращает `User` ORM, не payload dict.
- [ ] Tests: register flow, login, JWT expiry, /me.
- [ ] Email verification — отложить до Resend интеграции в Фазе 6.H.

### Фаза 6.B — Subscription & quota DB
- [ ] `backend/models/subscription.py` — добавить `provider` (`lemon`/`stripe`/`yookassa` enum, default `lemon`), `lemon_subscription_id`, `lemon_variant_id`. Снять старый CheckConstraint.
- [ ] `backend/models/user_llm_key.py` — `UserLLMKey(user_id, provider, encrypted_key)` Fernet-шифрование.
- [ ] `backend/services/billing/quotas.py` — `Tier` enum (`FREE`/`PREMIUM`/`PRO`), `assert_quota(user, kind)` → 402 при превышении (kind = `natal_chart`/`horoscope`/`dream_analysis`/`event_forecast`).
- [ ] Подключить квоты к astrology + dreams endpoints через `Depends`.
- [ ] Tests: free квоты, premium без лимитов, pro равен premium.

### Фаза 6.C — Lemon Squeezy integration (MoR)
- [ ] `backend/services/billing/lemon_provider.py` — Checkout API, Customer API, webhook signature verification.
- [ ] Products в Lemon Dashboard (manual setup): Premium-monthly, Pro-monthly, one-time reports. Variant IDs в env.
- [ ] `POST /api/v1/billing/checkout` — создаёт checkout URL для variant_id, прокидывает user_email и custom_data={user_id}.
- [ ] `POST /api/v1/billing/webhook` — HMAC-SHA256 signature verification, обрабатывает `subscription_created`, `subscription_updated`, `subscription_cancelled`, `subscription_expired`, `order_created` (one-time).
- [ ] `POST /api/v1/billing/portal` — генерирует Customer Portal link (отмена/смена через Lemon).
- [ ] Idempotency — каждый webhook payload имеет `meta.event_id`; кладём в `processed_webhook_events` чтобы не дублировать.
- [ ] Tests: webhook signature, idempotency, subscription lifecycle, refund.

### Фаза 6.D — *(пропущена)*
Stripe + YooKassa выпиливаются. Все Subscription.stripe_subscription_id / yookassa_subscription_id оставляем для backward-compat данных, но новые подписки только через Lemon.

### Фаза 6.E — Pro/BYOK tier
- [ ] `backend/services/byok/keys.py` — Fernet save/load шифрованных ключей пользователя; ключ деривируется из `SECRET_KEY`.
- [ ] `POST /api/v1/users/me/llm-keys` — сохранить ключ для provider (`anthropic`/`openai`/`gemini`/`groq`).
- [ ] `DELETE /api/v1/users/me/llm-keys/<provider>` — отозвать.
- [ ] `UniversalLLMProvider` — опциональный `for_user: User` параметр в `__init__`; если есть BYOK ключи → подменяем `api_keys` dict; cost_tracker помечает запись `agent` тегом `byok` (или сохраняем как обычно, метаданные в namespace).
- [ ] Pro-tier checks: при Pro подписке у пользователя должен быть хотя бы один BYOK ключ.
- [ ] Tests: encrypt/decrypt round-trip, provider override priority, Pro без ключа → 403.

### Фаза 6.F — i18n RU/EN/DE/ES/FR
- [ ] **Frontend** (next-intl): `frontend/messages/{de,es,fr}.json` стартовый перевод от DeepL Pro API + ручная проверка контента. `i18n/request.ts` + `middleware.ts` — добавить локали. Accept-Language auto-detect.
- [ ] **MCP tools**: расширить `locale` валидацию до `ru|en|de|es|fr` в `astrology.py`, `dreams.py`, `lunar.py` (сейчас принимает любую строку, нужна валидация).
- [ ] **Astrology prompts** (`backend/services/astrology/ai/prompt_templates.py`): параметризовать по locale; добавить DE/ES/FR ветки.
- [ ] **Dream prompts** (`backend/services/dreams/ai/prompts/*.json`): добавить ветки `de/es/fr` к существующим `ru/en`.
- [ ] **Lunar tables** (`backend/data/lunar_tables.json`): добавить ключи `de/es/fr` к 31 лунному дню (human translator — астрологический контекст).
- [ ] **Dream symbols** (`backend/services/dreams/knowledge_base/symbols.json`): добавить `interpretation_{de,es,fr}` к 56 символам.
- [ ] **Language detection** (`backend/services/dreams/analyzer.py::_detect_language`): расширить до 5 языков через `lingua-language-detector`.
- [ ] **GeoNames fallback DB** (`backend/utils/geonames_resolver.py`): добавить ключи на DE/ES/FR для крупных городов (Berlin/Madrid/Paris/Roma + транслитерации).
- [ ] Tests: каждый из 5 локалей → MCP tool + endpoint возвращает корректный язык.

### Фаза 6.G — Frontend: pricing + checkout + account + mobile
- [ ] `frontend/app/[locale]/pricing/page.tsx` — 5 языков, валюта по гео-IP.
- [ ] `frontend/app/[locale]/account/page.tsx` — текущая подписка, история, BYOK keys, кнопка Portal.
- [ ] `frontend/app/[locale]/{login,register}` — клиенту страницы с email/password формами.
- [ ] Auto-redirect to Lemon Checkout URL после клика Buy.
- [ ] Playwright тесты: register → login → checkout (Lemon test mode) → success page.

### Фаза 6.H — Email transactional (Resend)
- [ ] `backend/services/email/resend_provider.py` — `send(to, subject, html)` через Resend API.
- [ ] Шаблоны (`backend/services/email/templates/{locale}/`): welcome, email-verify, password-reset, subscription-receipt, payment-failed, subscription-cancelled.
- [ ] Tests: рендеринг каждого шаблона на каждом локали.

### Фаза 6.I — Compliance & GDPR
- [ ] `GET /api/v1/users/me/data-export` → ZIP со всеми чартами/снами/подписками/транзакциями.
- [ ] `DELETE /api/v1/users/me` → soft-delete (status="pending_deletion") + cron-job hard-purge через 30 дней.
- [ ] Cookie banner в frontend (EU обязателен).
- [ ] Privacy Policy + ToS шаблоны на 5 языках.
- [ ] Retention: пользователь сам выбирает срок хранения dream-text (поле `retention_days` на User).

### Фаза 6.J — Mobile apps (iOS + Android via Capacitor)
- [ ] `mobile/` — Capacitor проект, оборачивает existing Next.js (статичный экспорт).
- [ ] `capacitor.config.ts` — `webDir: '../frontend/out'`, `appId: 'app.oneiroscope'`.
- [ ] Native plugins: `@capacitor/preferences` (token storage), `@capacitor/share`, `@capacitor/push-notifications`.
- [ ] iOS: Xcode сборка, App Store Connect submission.
- [ ] Android: Android Studio сборка, Google Play Console submission.
- [ ] In-App Purchases — Apple/Google требуют свой IAP для подписок (30% take). Решение: web-checkout через браузер до approval'а, потом native IAP с branching.

### Definition of Done (Фаза 6)
- Пользователь из 🇪🇺/🇺🇸/🇷🇺/любая страна регистрируется → выбирает Premium/Pro → платит через Lemon Squeezy Checkout → получает unlimited доступ.
- Pro/BYOK путь работает: пользователь добавляет Anthropic-ключ, его LLM-запросы идут через его ключ.
- MCP-сервер остаётся бесплатным (не требует auth, BYOK для tech-пользователей через Claude Desktop).
- Quota enforcement: free-юзер видит 402 при превышении.
- 5 локалей покрыты тестами e2e.
- Mobile apps опубликованы в App Store и Google Play (или хотя бы TestFlight + Closed Track).
- Deployment guide (`docs/DEPLOYMENT.md`) + Mobile guide (`docs/MOBILE.md`) написаны.

### Open questions (resolved 2026-06-14)
1. ~~Юр.лицо для YooKassa~~ → **Lemon Squeezy MoR** — не нужно.
2. ~~Stripe-аккаунт страна~~ → **выпилен**.
3. Email-провайдер → **Resend** (минималистично, $20/мес).
4. Переводчик → **DeepL Pro для UI** + human review для lunar/symbols.
5. Free-tier лимит → **1 натал на аккаунт** + 1 гороскоп/день; reset гороскопов на полночь UTC.

---

## ✅ Фаза 7 — Strategic Life Cycle Analyst pivot

После peer-review: пивот из «ещё один AI-гороскоп» в **Strategic Life Cycle Analyst** — decision-support tool с многослойной evidence matrix, никаких детерминированных предсказаний. Astrology — один из аналитических слоёв, не источник истины. Полные обоснования: `docs/STRATEGIC_ANALYST.md`.

### ✅ 7.A — Strategic substrate (`backend/services/strategic/`)
- [x] `layers.py` — 8 epistemic Layer enum + Source + Insight + EvidenceMatrix + auto-derived Confidence.
- [x] `no_determinism.py` — regex-валидатор «will/будет/случится» + softener + hedge prefixes + allowed-phrase list.
- [x] Тесты: 24 кейса (валидаторы, hedge prefixes, confidence derivation, color codes).

### ✅ 7.B — Deterministic astronomy MCP tools
- [x] `backend/services/astrology/astrocartography.py` — relocate() + scan_cities() для астрокартографических расчётов с весами.
- [x] `backend/services/astrology/transits_engine.py` — find_transits() для точных дат транзитов (local-minimum detection).
- [x] `backend/services/astrology/solar_return.py` — solar_return() для SR на любой локации (arc-min precision через 2-stage search).
- [x] MCP-tools: `compute_transits`, `astrocartography_scan`, `solar_return_chart` в `backend/mcp/tools/strategic_astro.py`.
- [x] Зарегистрированы в `backend/mcp/server.py` (теперь 16 tools).
- [x] Тесты: 10 кейсов (включая известную Jupiter ☌ natal Saturn 11.09.2026, SR Omiš Sun→House 8).

### ✅ 7.C — Strategic Analyst agent + переписанные промпты
- [x] `agents/prompts/strategic_system.md` — главный промпт парадигмы (8 layers, hard rules, обязательная Evidence Matrix в ответе, fixed closing).
- [x] `agents/prompts/astrology_system.md` — переписан под Strategic Analyst posture (наследует hard rules).
- [x] `agents/prompts/dream_system.md` — переписан под Strategic Analyst posture (no diagnosis, reflection prompts вместо predictions).
- [x] `agents/specialists/strategic_agent.py` — `StrategicAnalystAgent` с 12 tools (синтез поверх всех данных).
- [x] `agents/orchestrator.py` — добавлен `strategic` intent router (RU + EN keywords); strategic wins over domain при пересечении.
- [x] Тесты: 12 кейсов роутинга + проверка обязательных секций в промптах.

### ✅ 7.D — Документация
- [x] `docs/STRATEGIC_ANALYST.md` — design rationale, architecture diagram, code map, market positioning матрица.
- [x] PLAN.md обновлён (этот блок).
- [x] soul.md §9 — session log.

### Метрики Phase 7
- **183 passed, 6 skipped** (было 139 + 44 новых) в backend suite.
- Tools registered: **16** (было 13 + 3 strategic).
- Specialists: **4** (было 3 + StrategicAnalystAgent).
- Все новые файлы добавлены в `mcp-smoke.yml` CI.

---


## Definition of Done

- `python -m backend.mcp.server` запускается, регистрирует ≥8 tools
- Claude Desktop / Cursor может подключиться по stdio и вызвать `natal_chart`
- `python -m agents.cli natal "1990-05-15 12:00 Moscow"` возвращает структурированную натал-карту
- `/natal` skill работает в Claude Code
- `pytest backend/tests/test_mcp_smoke.py` зелёный
- Все изменения в `claude/eager-noether-5UQJR`, PR не создаётся пока не попросят
