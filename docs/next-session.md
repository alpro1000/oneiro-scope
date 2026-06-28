# next-session.md — Handoff snapshot

> **English TL;DR:** Single-page snapshot for the next Claude Code
> session. State, what works, what's broken, next priorities, context
> that's easy to lose. Updated at the end of every substantial session
> alongside `soul.md §9`.

**Дата последнего обновления:** 2026-06-28
**Последняя ветка работы:** `claude/hard-archetypes-cloudrun` (merged PR #122)
**Текущий main HEAD:** `b0eba32` (Phase 8 hard archetypes + Cloud Run guide)

---

## Состояние проекта (high-level)

| Слой | Статус | Где живёт |
|---|---|---|
| **MCP server** | ✅ 23 tools зарегистрированы | `backend/mcp/server.py` |
| **ADK agents** | ✅ 4 specialists + 1 orchestrator | `agents/specialists/`, `agents/orchestrator.py` |
| **Strategic Analyst posture** | ✅ promtps + Insight types + no-determinism | `agents/prompts/strategic_system.md`, `backend/services/strategic/` |
| **Hard archetype tables** | ✅ MC/Sun/Houses/Aspects/Dignities (Phase 8) | `backend/services/astrology/archetypes/` |
| **Auth + Billing** | ✅ Lemon Squeezy MoR (Phase 6) | `backend/api/v1/{auth,billing,users}.py` |
| **BYOK + Quotas** | ✅ Fernet-encrypted per-user keys + 402 quotas | `backend/services/{byok,billing/quotas}.py` |
| **Cloud Run + Vertex AI** | ✅ ADC auto-detect via K_SERVICE | `backend/core/llm_provider.py`, `docs/deployment/CLOUD_RUN.md` |
| **Backend test suite** | ✅ 263 passed, 6 skipped | `backend/tests/` |
| **Frontend** | ⚠ существует, не интегрирован с Phase 6+ auth/billing | `frontend/` (Next.js 14) |
| **Mobile (Capacitor)** | ⚠ guide есть, проект не создан | `docs/MOBILE.md` |

---

## Что точно работает (verified)

- Натальная карта через `calculate_natal_chart` (Swiss Ephemeris MOSEPH).
- Транзиты через `compute_transits` (точность до дня).
- Solar Return через `solar_return_chart` (arc-min precision, любая локация).
- Astrocartography через `astrocartography_scan` (relocated chart angles).
- Archetype-таблицы: 7 MCP tools (`mc_in_sign`, `sun_in_sign`, `house_meaning`, `aspect_meaning`, `planet_dignity`, `zodiac_sign`, `list_archetype_topics`).
- Strategic Analyst-агент с 19 tools.
- Smoke CI зелёный.

## Что НЕ работает / pre-existing red

- **`build-and-validate` CI** — pre-existing failure. Документировано в `docs/soul.md §5`. Не блокирует merge (mergeable_state: unstable, не blocked).
- **Frontend ↔ Backend auth integration** — auth-endpoints есть, но frontend (`frontend/app/[locale]/`) ещё не использует их для логина/checkout.
- **Vertex AI / Cloud Run живой деплой** — гайд написан (`docs/deployment/CLOUD_RUN.md`), но реального деплоя через Cloud Build нет. Нужен GCP-аккаунт owner'а.

---

## Следующие приоритеты (порядок)

### P0 — что блокирует production-deploy

1. **End-to-end smoke на Cloud Run staging.** Развернуть один Cloud Run сервис, проверить что Vertex AI auto-detect срабатывает, что Lemon webhook сигнатура работает. Шаги в `docs/deployment/CLOUD_RUN.md`.
2. **Alembic migrations.** Текущие модели (User, Subscription, UserLLMKey) не имеют миграций — `init_db()` создаёт схему на ходу. Для prod нужна Alembic.

### P1 — что усиливает продукт

3. **`planet_in_house.py` archetype module.** 10 планет × 12 домов = 120 записей с цитатами (Sasportas, Tompkins). Завершает Phase 8 hard-archetype-набор.
4. **`transit_meanings.py`** — archetype-таблица для транзитов (Saturn □ Sun = midlife reappraisal, цитата Greene).
5. **Frontend pricing/checkout/account pages** (Phase 6.G — ещё не реализовано).
6. **DE/ES/FR переводы** для `lunar_tables.json` и `symbols.json` (нужен human native review).

### P2 — improvement

7. **End-to-end test Strategic Analyst-агента с реальным LLM-ключом.**
8. **Cloud Build `cloudbuild.yaml`** в корне репо для CI/CD.
9. **`forbidden_topics.py`** — единый список запрещённых тем + автотесты.

---

## Контекст, который легко потерять

- **Timezone USSR 1977 — UTC+3, НЕ UTC+4.** Декретное время, без DST до 1981 года. `zoneinfo` корректно обрабатывает; ручные расчёты — используй UTC+3.
- **Jupiter ☌ natal Saturn (для chart 1977-07-01 22:30 Запорожье) = 11 сентября 2026**, не август (это была моя ошибка с timezone).
- **MCP-tool `calculate_natal_chart`** не загружает chart из DB при `natal_chart_id` (TODO в `backend/api/v1/astrology.py:130`). Персонализированные гороскопы пока работают только если chart передан напрямую в `service.generate_horoscope()`.
- **Cloud Run scale-to-zero + Swiss Ephemeris cold start ~200ms.** Учитывай при тестировании первого запроса.
- **Strategic intent router выигрывает у domain router** при пересечении ключевых слов (намеренно, см. `agents/orchestrator.py::classify_intent`).
- **Archetype-таблицы используют традиционные правители** (Mars/Scorpio, Saturn/Aquarius, Jupiter/Pisces) для dignity-подсчёта. Modern (Pluto/Uranus/Neptune) — только для справки.

---

## Open architectural decisions ждущие owner'а

1. **Цена premium tier:** $9.99 vs $14.99 vs $24.99/мес? Зависит от того, как позиционируем Strategic Analyst (Co-Star competitor vs life-coaching premium).
2. **Web frontend deploy:** Vercel или Cloud Run? `render.yaml` уже описывает Render, `CLOUD_RUN.md` описывает Cloud Run.
3. **Mobile-first vs web-first для Q3 2026.** Mobile через Capacitor готов (гайд), но добавляет Apple Developer ($99/yr) + Google Play ($25 один раз).
4. **Тестовый Lemon Squeezy аккаунт** — заведён ли? Тестовые product variant IDs нужны для CI smoke.

---

## Discipline reminder

Конец сессии = добавь запись в `docs/soul.md §9`. Это **последний Gate**.
Если эта сессия архитектурно меняет что-то — добавь ADR в `soul.md §6`.

> «Сначала читаешь весь репо. Потом определяешь naming. Потом пишешь.»
