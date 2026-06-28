# next-session.md — Handoff snapshot

> **English TL;DR:** Single-page snapshot for the next Claude Code
> session. State, what works, what's broken, next priorities, context
> that's easy to lose. Updated at the end of every substantial session
> alongside `soul.md §9`.

**Дата последнего обновления:** 2026-06-28 (end of day)
**Последняя ветка работы:** `claude/memory-system-harmonization` (merged PR #123)
**Текущий main HEAD:** `af9aebf` (Phase 9 memory scaffold complete)

---

## 🎯 С чего начать следующую сессию

Просто следуй mandatory block из `CLAUDE.md` — он теперь ведёт через 8 файлов в правильном порядке:

```
1. docs/steering/conventions.md  ← как работаем (Karpathy, EARS, gates)
2. docs/steering/product.md      ← что строим
3. docs/steering/tech.md         ← стек, AI-провайдеры
4. docs/steering/structure.md    ← layout репо
5. docs/steering/domain.md       ← астрология+сны+дисклеймер
6. docs/soul.md                  ← §1-§10, последний журнал в §9
7. docs/PLAN.md                  ← phases 0-9, далее ↓
8. docs/next-session.md          ← этот файл (приоритеты ниже)
```

После чтения → выбери задачу из P0/P1/P2 ниже или жди указания owner'а.

---

## Состояние проекта (high-level, post Phase 9)

| Слой | Статус | Где живёт |
|---|---|---|
| **MCP server** | ✅ 24 tools зарегистрированы | `backend/mcp/server.py` |
| **ADK agents** | ✅ 4 specialists + 1 orchestrator | `agents/specialists/`, `agents/orchestrator.py` |
| **Strategic Analyst posture** | ✅ prompts + Insight types + no-determinism | `agents/prompts/strategic_system.md`, `backend/services/strategic/` |
| **Hard archetype tables** | ✅ MC/Sun/Houses/Aspects/Dignities + planet_in_house 10×12 (Phase 8) | `backend/services/astrology/archetypes/` |
| **Auth + Billing** | ✅ Lemon Squeezy MoR (Phase 6) | `backend/api/v1/{auth,billing,users}.py` |
| **BYOK + Quotas** | ✅ Fernet-encrypted per-user keys + 402 quotas | `backend/services/{byok,billing/quotas}.py` |
| **Cloud Run + Vertex AI** | ✅ ADC auto-detect via K_SERVICE | `backend/core/llm_provider.py`, `docs/deployment/CLOUD_RUN.md` |
| **Memory system** | ✅ Full STAVAGENT scaffold (Phase 9) | CLAUDE.md, soul.md §1-§10, steering/*, templates/, next-session.md |
| **Backend test suite** | ✅ 268 passed, 6 skipped | `backend/tests/` |
| **Frontend** | ⚠ Next.js существует, не интегрирован с Phase 6+ auth/billing | `frontend/` |
| **Mobile (Capacitor)** | ⚠ guide есть, проект не создан | `docs/MOBILE.md` |

---

## Что точно работает (verified locally)

- Натальная карта `calculate_natal_chart` (Swiss Ephemeris MOSEPH).
- Транзиты `compute_transits` (exact dates, тест на Jupiter ☌ natal Saturn = 11.09.2026 ✓).
- Solar Return `solar_return_chart` (arc-min precision, любая локация).
- Astrocartography `astrocartography_scan` (relocated chart angles, scored).
- Archetype-таблицы — 7 MCP tools, классические цитаты, confidence 0.9.
- Strategic Analyst agent с 19 tools, 8-layer evidence matrix.
- Disclaimer enforcement через `ensure_disclaimer()` для 5 локалей.
- Numeric confidence ladder (`LAYER_CONFIDENCE` table).
- Smoke CI зелёный.

## Что НЕ работает / pre-existing

- **`build-and-validate` CI** — pre-existing failure. См. `docs/soul.md §5`. Не блокирует merge (`mergeable_state: unstable`, не `blocked`).
- **Frontend ↔ Backend auth integration** — endpoints есть, frontend ещё не использует.
- **Vertex AI / Cloud Run живой деплой** — гайд написан, реального деплоя нет. Нужен GCP-аккаунт owner'а.

---

## Следующие приоритеты (порядок)

### P0 — что блокирует production deploy

1. **End-to-end smoke на Cloud Run staging.** По `docs/deployment/CLOUD_RUN.md`. Развернуть один сервис, проверить Vertex AI auto-detect, Lemon webhook signature.
2. **Alembic migrations.** User/Subscription/UserLLMKey модели не имеют миграций; `init_db()` создаёт схему на ходу. Для prod нужно настоящее версионирование.

### P1 — что усиливает продукт

3. ~~**`planet_in_house.py`** archetype module — 10 планет × 12 домов с цитатами Sasportas/Tompkins.~~ ✅ **DONE 2026-06-28 late** — composed table + MCP tool `planet_in_house` (tools 23→24), +5 tests. Phase 8 hard-archetype-набор завершён.
4. **`transit_meanings.py`** — archetype-таблица для транзитов (Saturn □ Sun = midlife reappraisal, цитата Greene).
5. **Frontend pricing/checkout/account pages** (Phase 6.G — не реализовано).
6. **DE/ES/FR переводы** для `lunar_tables.json` и `symbols.json` (human native review).

### P2 — improvement

7. **End-to-end test Strategic Analyst-агента с реальным LLM-ключом.**
8. **Cloud Build `cloudbuild.yaml`** в корне репо для CI/CD.
9. **`forbidden_topics.py`** — единый список запрещённых тем + автотесты.
10. **Capacitor mobile проект** (`mobile/` dir по `docs/MOBILE.md`).

---

## Контекст, который легко потерять

- **Timezone USSR 1977 = UTC+3, НЕ UTC+4.** Декретное время, без DST до 1981. `zoneinfo` корректно обрабатывает.
- **Jupiter ☌ natal Saturn (для chart 1977-07-01 22:30 Запорожье) = 11 сентября 2026**, не август (была ошибка из-за timezone).
- **MCP-tool `calculate_natal_chart`** не загружает chart из DB при `natal_chart_id` (TODO в `backend/api/v1/astrology.py:130`). Персонализированные гороскопы пока работают только если chart передан напрямую.
- **Cloud Run scale-to-zero + Swiss Ephemeris cold start ~200 ms.** Учитывай при первом запросе.
- **Strategic intent router выигрывает у domain router** при пересечении ключевых слов (намеренно).
- **Archetype-таблицы используют традиционные правители** (Mars/Scorpio, Saturn/Aquarius, Jupiter/Pisces). Modern Pluto/Uranus/Neptune — только для справки.
- **Karpathy anti-bloat правила в `conventions.md`** — критично соблюдать: 50 строк вместо 200, не трогай не связанный код, не добавляй "гибкость" о которой не просили.

---

## Open architectural decisions ждущие owner'а

1. **Цена premium tier:** $9.99 vs $14.99 vs $24.99/мес?
2. **Web frontend deploy:** Vercel или Cloud Run? Render деплоит оба, Vercel дешевле для Next.js.
3. **Mobile-first vs web-first для Q3 2026.** Mobile через Capacitor готов (гайд) + $99/yr Apple + $25 Google Play.
4. **Тестовый Lemon Squeezy аккаунт заведён?** Тестовые product variant IDs нужны для CI smoke.

---

## История фаз (для нового онбординга)

| Phase | Что | PR | Merged |
|---|---|---|---|
| 0 | Discipline scaffolding (PLAN/soul/steering/mandatory) | #111 | 2026-05-26 |
| 1 | MCP server + 13 tools | #111 | 2026-05-26 |
| 2 | ADK agent + CLI | #111 | 2026-05-26 |
| 3 | 8 Claude Code skills | #111 | 2026-05-26 |
| 4 | Production fixes (cost tracker, ephemeris log, mcp-smoke CI) | #111-#114 | 2026-05-26 |
| 5 | ADK orchestrator + 3 specialists + cost tag | #116-#118 | 2026-05-31 |
| 6 | Auth + Lemon Squeezy + BYOK + quotas + Cloud Run + Mobile | #119-#120 | 2026-06-14 |
| 7 | Strategic Life Cycle Analyst pivot (evidence matrix) | #121 | 2026-06-14 |
| 8 | Hard archetype tables + Cloud Run/Vertex AI guide + scaffold start | #122 | 2026-06-28 |
| 9 | Memory system harmonization (next-session, templates, TL;DR, §10) | #123 | 2026-06-28 |

---

## Discipline reminder

Конец каждой substantial-сессии:
1. Добавь запись в `docs/soul.md §9` (что замержено, какие решения, что отложено).
2. Обнови этот файл (`docs/next-session.md`) — новое "what works", обнови P0/P1, обнови "что легко потерять".
3. Если были архитектурные решения — добавь в `docs/soul.md §6` (ADR-NNN).
4. Если были отвергнутые идеи — в `docs/soul.md §10` с обоснованием.

> «Сначала читаешь весь репо. Потом определяешь naming. Потом пишешь.»
