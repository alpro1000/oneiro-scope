# next-session.md — Handoff snapshot

> **English TL;DR:** Single-page snapshot for the next Claude Code
> session. State, what works, what's broken, next priorities, context
> that's easy to lose. Updated at the end of every substantial session
> alongside `soul.md §9`.

**Дата последнего обновления:** 2026-07-27 (part 2)
**Последняя ветка работы:** `claude/fandorin-portrait-generation-d422my`
**Текущий main HEAD:** `#161` — **коннектор ЖИВОЙ, закрыт OAuth (Auth0), карта считается через чат**

**СТАТУС: коннектор работает.** Claude → Auth0 → Render → Swiss Ephemeris.
46 инструментов. `MCP_REQUIRE_AUTH=true` всё время, открытого окна не было.

**Боевые данные Auth0 (EU-2, Development):**
- issuer: `https://dev-u22itgv3h8ew1sgz.eu.auth0.com/` (СО слэшем!)
- audience = `https://oneiroscope-backend.onrender.com/mcp`
- API «OneiroScope MCP», Default Audience выставлен, DCR включён,
  Third-Party Access = User-Delegated, connection `con_dwxq9e9cIn9RG3rh`
  помечен `is_domain_connection: true`

**Новое в сессии 2026-07-27 part 2:**
- **5 гейтов Auth0 пройдены** — порядок и симптомы записаны в `soul.md §9`.
  Самый неочевидный: `mcp_registration_failed` был **лимитом в 10 приложений**
  тенанта (мусорные `tpc_` от неудачных попыток съели квоту), а не форматом
  клиента, как я сначала думал.
- **#160 фикс:** issuer сравнивался строка-в-строку, Auth0 шлёт `iss` со
  слэшем → отвергались ВСЕ настоящие токены. Конфигом не обходилось.
- **#161 разворот на data-first:** `calculate_natal_chart` больше не зовёт
  серверный LLM (`include_interpretation=False` по умолчанию). В MCP-first
  клиент — уже сильная модель; второй хоп лишний, платный, слабее и ломается.
  Серверная проза осталась опцией для запаркованного веб-фронта.
- **#161 заодно:** починен fallback-шаблон (английские слова в русском тексте;
  аспекты как ПЕРВАЯ БУКВА планеты — «- С opposition Л») и rate-limiter
  (ключ был IP прокси Render → все юзеры в одном ведре 100/мин).
- **`/connect/diagnostics` себя оправдал** — на каждом гейте показывал, какая
  переменная не так. Браузерный агент не читает логи, а страницу читает.

**P0 на следующую сессию:**
1. `/mcp` вне rate-limiter'а (диспетчер обходит middleware ради SSE) —
   добавить лимит по `mcp_subject` из токена.
2. Кабинет `/account` задеплоен, но его вход (email+password) НЕ связан с
   аккаунтом Auth0 — это два разных входа. Свести: маппинг Auth0 `sub` → User.
3. Auth0 тенант Development с автоименем `dev-u22itgv3h8ew1sgz` — видно
   пользователям на логине. Перед публичным запуском: Production-тег + имя.

**Из части 1 той же сессии:**
- **Коннектор не работал вообще с #155** — три независимые поломки, каждая
  фатальна сама по себе: эндпоинт лежал на `/mcp/mcp`; SSE-канал
  сервер→клиент не отдавал ни байта из-под GZip/BaseHTTPMiddleware
  (замер на реальном сокете: 0 байт за 6 с против мгновенных заголовков);
  `421 Invalid Host header` из-за localhost-only allow-list транспорта.
  Ошибка, которую видел owner («Couldn't register with sign-in service»),
  была четвёртой: RFC 9728 отдавался всегда → клиент шёл в DCR против
  origin без authorization server.
- `MCPPathDispatcher` — `/mcp` маршрутизируется **над** middleware-стеком.
  Побочный эффект: `/mcp` теперь вне rate-limiter'а, границу задаёт auth.
- **Тесты коннектора и портала никогда не запускались в CI** — их не было
  в списке файлов `mcp-smoke.yml`. Добавлены (340 тестов в этом job).
- **Кабинет** `/account` (`backend/portal/account.py`): тариф, свои ключи,
  GDPR-выгрузка, удаление. Тонкий слой над существующими `auth.py` /
  `billing.py` / `users.py`. JWT в httpOnly `SameSite=Lax` куке. БД
  открывается лениво → страница входа живёт при недоступной БД.
- **Ловушка для будущих сессий:** `TestClient` не видит стриминг — его
  транспорт прогоняет приложение до конца, поэтому бесконечный SSE
  выглядит как зависание. Проверять стриминг только реальным сервером.
- Написан `docs/deploy/auth0-setup.md`. **P0: `MCP_REQUIRE_AUTH=false`,
  `/mcp` открыт всем, у кого есть URL.**

**Новое в сессии 2026-07-21 (fandorin-portrait-generation):**
- **Каталог паттернов реализован целиком** — 6 пар skill+MCP tool поверх
  общего движка `backend/services/strategic/pattern_engine.py`:
  `/money-contour`, `/vocation-map`, `/decade-map`, `/life-pivots`
  (петля валидации жизнью), `/electional-day`, `/character-face`
  (обратная физиогномика, гейт fictional_or_self_only). Тесты:
  `test_strategic_patterns.py` 13 passed; smoke-set обновлён.
- Движок импортируем без стека astrology-service (своя таблица
  достоинств, Moshier) — по образцу lunar/engine.py.
- **Фандорин-кейс** (`docs/specs/fandorin-portrait/`) + генератор
  портретов `scripts/generate_fandorin_portrait.py` (openai/gemini,
  generate/edit).
- Следующее: прогнать skills против живого MCP-сервера; PR в main по
  команде owner; рассмотреть кэш подтверждённых life-pivots ответов
  (user_context) в персональном хранилище, НЕ в репо (PII).

**Сессия 2026-07-08 — `/client-report`, без изменений кода репозитория:**
Сгенерирован полный клиентский PDF-отчёт (натал + транзиты 2026 + Solar Return + астрокартография) на чешском языке для нового клиента (11.02.1986 12:50 Плзень, ЧР). MCP-сервер не был подключён в сессии → использован документированный fallback (прямые импорты `backend.services.astrology`, инициализатор пакета застаблен, чтобы не тянуть тяжёлый `AstrologyService`). Окружение сессии не имело pyswisseph/timezonefinder/matplotlib — поставлены в scratch-venv, `world.geojson` (Natural Earth 110m) скачан во временный scratchpad; **репозиторий не менялся** (requirements.txt не трогали), кроме записи в `docs/soul.md §9`. Заметка для будущих сессий с `/client-report` на bare-checkout: fallback-путь скилла реально работает, но требует ~3 доп. pip-пакета и сетевой доступ для world.geojson (кэш в репо отсутствует) — можно закэшировать geojson в `docs/templates/` или scratchpad конвенции, если это будет происходить часто.

**Новое в сессии 2026-07-05 (вечер, photo-personality-analysis):**
- **Auto-zoom в `_landmarks_from_photo`:** нет лица → апскейл 2x/3x;
  найдено → кроп бокса лица + увеличение до ~600px и повторный,
  более точный прогон. Метрики — отношения, координаты кропа валидны.
- **Анатомическая толщина губ** (`FaceMetrics.lip_thickness`):
  внешняя кайма (0→13 + 14→17) / ширина рта (61–291), только при
  закрытом рте (зазор ≤ 6% ширины) — закрыт бэклог из #144. Нейтраль
  ≈ 0.34 (Farkas), thin ≤ 0.30 / full ≥ 0.40. Анкетный ответ рта
  уступает геометрии, когда та измерила (`mouth_measured`).
- **Лонгитюд:** `services/physiognomy/longitudinal.py` + MCP
  `physiognomy_timeline` — медианы по периодам, diff чтений по topic
  (stable/appeared/disappeared) + дельты метрик + caveat о взрослой
  антропометрии. Live: детство→взрослость owner'а — стабильны earth /
  dilated / широкие глаза / компактный лоб / тонкие губы; появились
  вода-вторичная, нижний двор, атлетик; ушёл пикник.
- Метрика губ валидирована вслепую: owner сказал «скорее тонкие» ДО
  метрики; 5 закрытортных кадров дали 0.22–0.29 → mouth_thin. ✓
- **photo-max-extraction (спека + ядро):** `docs/specs/
  photo-max-extraction/` (Gates 1–3 done); `aggregate.py` + MCP
  `analyze_face_archive` — весь фотоархив одной командой: лестница
  детекции, медианный профиль, стабильность метрик, support с
  честными знаменателями (губы 5/5 замеримых), coverage-карта
  (measured / questionnaire / guided-scan / unreadable). Чтение
  текстуры дворцов (ци-сэ) по бытовым фото закрыто ЭКСПЕРИМЕНТОМ:
  сырой разброс ×160, с нормировкой на щёку ×26, детский контроль
  неотличим от взрослого. Gate 5 = пилот controlled-capture текстуры
  (отдельное решение owner'а).
- **Gate 4 СДЕЛАН — guided-сканер** `/[locale]/face`: браузерный
  FaceLandmarker (@mediapipe/tasks-vision 0.10.14, wasm+модель с CDN,
  override через NEXT_PUBLIC_FACE_MODEL_URL); живые гейты СТРОЖЕ
  серверных (yaw 0.15/0.20, рот 0.05/0.06 + размер лица + симметрия
  света по щекам) → захваченный кадр всегда проходит сервер;
  авто-захват 5 кадров ≥600мс; на сервер уходят ТОЛЬКО лендмарки
  (privacy-first). Новый эндпоинт POST /physiognomy/analyze-archive
  (кап 24 кадра, 422 если все кадры отбиты). Чистая гейт-математика в
  `frontend/lib/face-gates.ts` (jest 6 тестов), клиент
  `physiognomy-client.ts`, компонент `FaceScanner.tsx`, переводы
  FacePage ru/en, пункт «Лицо/Face» в Header.
- Тесты: backend physiognomy 37 passed; frontend 13 passed;
  tsc --noEmit чисто.

**🎯 ПЕРВАЯ ЗАДАЧА СЛЕДУЮЩЕЙ СЕССИИ (запрос owner):** прогнать фотографии
друга «на чистую голову» — с нуля, end-to-end через замерженный
пайплайн (photo → `analyze_face` → агрегация по кадрам →
`physiognomy_report`). Референс прошлого прогона: 18 фото → 13
валидных / 5 отказов по гейтам; Земля 13/13 (0.997–1.687), Вода
вторичная 8/13; нос пограничный wealth (среднее 0.2687, порог 0.28);
«живой рот» — размах lip-gap 0.008–0.047 (mouth-чтения от геометрии
теперь отключены, #144). Данные рождения друга: 26.03.1978 03:20
Запорожье (UTC+3 декретное), живёт в Москве. PII друга (имя/контакты)
в репо и отчёты НЕ вносить — только «Друг».

**Новое в сессии 2026-07-05 (hardening + полевой тест №2):**
- **PRs #136–#144 замержены:** общий safe-path модуль
  `backend/mcp/tools/_files.py` (CWE-22: записи только в gitignored
  `reports/`, .html-only, корень от `__file__`, TMPDIR=/ fallback);
  двухслойные отчёты (полный нарратив → тезисы → данные → дисклеймер);
  MCP-тулы `horoscope_report` / `profile_report_file`;
  conventions.md §11 (engineering modes, persona simulation отвергнута);
  фикс метрики губ (#144, см. ниже). Тесты физиогномики 23/23.
- **Живой кейс #144 (owner поймал противоречие):** `lip_fullness` =
  внутренний зазор губ = раскрытие рта, НЕ толщина. Экспрессивный рот
  усреднился в «тонкие губы». Mouth-чтения от геометрии отключены
  (анкета — можно); бэклог: анатомическая толщина по внешним точкам
  (0→13, 14→17), межкадровая вариативность как черта.
- **Урок сравнения с ChatGPT (принцип метода):** немеряющий читатель
  приписывает элементы по слою подачи (улыбки/позы/стайлинг) одним
  уверенным голосом; наше разделение структура (кость, 1.0) /
  словарь традиции (0.6) / поведение — ровно та дисциплина
  провенанса, которая ловит этот режим отказа.
- Датасет: 2 человека, ~39 фото, ~29 валидных замеров, ~8 честных
  отказов; 6 калибровочных находок, 4 закрыты кодом.

**Предыдущая сессия 2026-07-04 (physiognomy service, боевое крещение и merge):**
- Сервис `backend/services/physiognomy/`: KB мянсян (5 элементов, 3 двора, 12 дворцов, 20 черт) + западные школы (Лафатер/Корман/Кречмер/fWHR), каждая запись с источником; детерминированная геометрия FaceMesh-лендмарок (1.0) → трактовки традиций (0.6 — НИЖЕ symbol-dict 0.8, физиогномика научно не валидирована).
- API `/api/v1/physiognomy`: GET /methods, POST /analyze (landmarks|metrics|анкета), POST /analyze-photo (серверный CV; mediapipe==0.10.14 + opencv-headless ДОБАВЛЕНЫ в backend/requirements.txt → после деплоя фото считается автоматически; без них — 501 с клиентским путём). Privacy-first вариант: лендмарки в браузере.
- **Yaw pose-gate** в geometry (асимметрия глаз >0.20 → отказ) — внедрён и проверен на живом кадре. Тесты: 10 passed.
- Live-валидация на 21 фото владельца (1981–2026): 16 валидных замеров, профиль воспроизводим; 4 калибровочные находки (1 закрыта кодом, 3 в tasks.md: occlusion-флаги, двойная линейка межглазья, детский режим).
- Досье владельца: `.claude/personal/owner_profile_patterns.md` (gitignored, PII-правило репо; было в docs/clients — вынесено по ревью ботов) (натал, пояса ACG, календарь 2026–28, замеры, паттерн «застой воды» с протоколом и дедлайнами: 5 писем до 15.07, 5 оплат до 31.08, запуск в окно сен–окт 2026).
- **Файловые отчёты по всем каналам:** `horoscope_report` и `profile_report_file` в MCP (HTML-файл, safe-path из общего `_files.py`); отчёты двухслойные — полный нарратив → тезисы → данные с источниками (запрос owner).
- **MCP-коннектор готов:** `analyze_face` / `physiognomy_report` (пишет HTML-файл отчёта, принимает photo_path|landmarks|metrics|анкету) / `physiognomy_methods` — зарегистрированы в backend/mcp/server.py.
- **Следующий шаг фичи:** frontend `/[locale]/face` — браузерный FaceLandmarker (@mediapipe/tasks-vision, модель в public/) + анкета-fallback; зонный рендер отчёта; опционально LLM-пересказ (0.7).
- ⚠ Render: проверить, что build с mediapipe/opencv проходит по размеру/времени; если нет — убрать из requirements и жить клиентским путём (сервис деградирует в 501 корректно).

**Предыдущая сессия (Phase 9, pattern features из живых тестов):**
- Сервисы: `historic_tz.py` (советское декретное время из координат), `synastry.py` (совместимость, 5 измерений 0–100), `transit_arcs.py` (фазовый таймлайн pressure/support + turning point), `report.py` (JSON+HTML-отчёт одной кнопкой); `astrocartography.py` — clean-флаг удачи, `compare_locations`, `theme_scan`; `solar_return.suggest_locations`.
- API: `/astrocartography/compare`, `/astrocartography/themes`, `/transits/arcs`, `/synastry`, `/solar-return/suggest`, `/report` (json|html).
- MCP: `compare_relocations`, `scan_cities_by_theme`, `transit_arc`, `synastry`, `solar_return_suggest`.
- Тесты: 254 passed (полный mcp-smoke набор локально).

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
| **MCP server** | ✅ 25 tools зарегистрированы | `backend/mcp/server.py` |
| **ADK agents** | ✅ 4 specialists + 1 orchestrator | `agents/specialists/`, `agents/orchestrator.py` |
| **Strategic Analyst posture** | ✅ prompts + Insight types + no-determinism | `agents/prompts/strategic_system.md`, `backend/services/strategic/` |
| **Hard archetype tables** | ✅ MC/Sun/Houses/Aspects/Dignities + planet_in_house 10×12 (Phase 8) | `backend/services/astrology/archetypes/` |
| **Auth + Billing** | ✅ Lemon Squeezy MoR (Phase 6) | `backend/api/v1/{auth,billing,users}.py` |
| **BYOK + Quotas** | ✅ Fernet-encrypted per-user keys + 402 quotas | `backend/services/{byok,billing/quotas}.py` |
| **Cloud Run + Vertex AI** | ✅ ADC auto-detect via K_SERVICE | `backend/core/llm_provider.py`, `docs/deployment/CLOUD_RUN.md` |
| **Memory system** | ✅ Full STAVAGENT scaffold (Phase 9) | CLAUDE.md, soul.md §1-§10, steering/*, templates/, next-session.md |
| **Backend test suite** | ✅ 275 passed, 6 skipped | `backend/tests/` |
| **Frontend** | ✅ pricing/account/checkout + auth/billing clients (Phase 6.G); ⚠ остальные страницы не интегрированы | `frontend/app/[locale]/{pricing,account,checkout}`, `frontend/lib/{auth,billing}-client.ts` |
| **Mobile (Capacitor)** | ⚠ guide есть, проект не создан | `docs/MOBILE.md` |

---

## Что точно работает (verified locally)

- Натальная карта `calculate_natal_chart` (Swiss Ephemeris MOSEPH).
- Транзиты `compute_transits` (exact dates, тест на Jupiter ☌ natal Saturn = 11.09.2026 ✓).
- Solar Return `solar_return_chart` (arc-min precision, любая локация).
- Astrocartography `astrocartography_scan` (relocated chart angles, scored).
- Archetype-таблицы — 9 MCP tools (вкл. planet_in_house, transit_meaning), классические цитаты, confidence 0.9.
- Strategic Analyst agent с 19 tools, 8-layer evidence matrix.
- Disclaimer enforcement через `ensure_disclaimer()` для 5 локалей.
- Numeric confidence ladder (`LAYER_CONFIDENCE` table).
- Smoke CI зелёный.

## Что НЕ работает / pre-existing

- **`build-and-validate` CI** — pre-existing failure. См. `docs/soul.md §5`. Не блокирует merge (`mergeable_state: unstable`, не `blocked`).
- **Frontend ↔ Backend auth integration** — pricing/account/checkout готовы (token в localStorage); astrology/dreams страницы ещё не шлют Authorization.
- **Vertex AI / Cloud Run живой деплой** — гайд написан, реального деплоя нет. Нужен GCP-аккаунт owner'а.

---

## Следующие приоритеты (порядок)

### P0 — что блокирует production deploy

1. **End-to-end smoke на Cloud Run staging.** По `docs/deployment/CLOUD_RUN.md`. Развернуть один сервис, проверить Vertex AI auto-detect, Lemon webhook signature.
2. **Alembic migrations.** User/Subscription/UserLLMKey модели не имеют миграций; `init_db()` создаёт схему на ходу. Для prod нужно настоящее версионирование.

### P1 — что усиливает продукт

3. ~~**`planet_in_house.py`** archetype module — 10 планет × 12 домов с цитатами Sasportas/Tompkins.~~ ✅ **DONE 2026-06-28 late** — composed table + MCP tool `planet_in_house` (tools 23→24), +5 tests. Phase 8 hard-archetype-набор завершён.
4. ~~**`transit_meanings.py`** — archetype-таблица для транзитов (Saturn □ Sun = midlife reappraisal, цитата Greene).~~ ✅ **DONE 2026-06-28 late-2** — composed table + NAMED_TRANSITS + MCP tool `transit_meaning` (tools 24→25), +7 tests.
5. ~~**Frontend pricing/checkout/account pages** (Phase 6.G).~~ ✅ **DONE 2026-06-28 late-3** — pricing/account/checkout/success + auth-client/billing-client; tsc/build/jest зелёные. TODO: Playwright e2e, BYOK-keys UI, валюта по гео-IP.
6. **DE/ES/FR переводы** — 🟡 _частично (2026-06-28 late-4)_: UI-локали готовы
   (`messages/{de,es,fr}.json` machine-draft + i18n plumbing + LanguageSwitcher,
   tsc/build/jest зелёные). **Остаётся:** контент `lunar_tables.json` (31 день)
   + `symbols.json` (56 символов) через DeepL Pro + **human native review**;
   локаль-валидация MCP tools до `ru|en|de|es|fr`; Accept-Language auto-detect.
   UI-строки тоже ждут проверки носителем.

### P2 — improvement

7. **End-to-end test Strategic Analyst-агента с реальным LLM-ключом.**
8. **Cloud Build `cloudbuild.yaml`** в корне репо для CI/CD.
9. **`forbidden_topics.py`** — единый список запрещённых тем + автотесты.
10. **Capacitor mobile проект** (`mobile/` dir по `docs/MOBILE.md`).

### P2 — из реального использования (`docs/FIELD_NOTES_real_use.md`, 2026-06-29)

11. **Поугловой вывод астрокартографии** — тул/форматтер `Asc/MC/IC/Desc → планета → простой смысл` по городу (сейчас приходится скриптовать).
12. **«Балл = тон, не интенсивность»** — задокументировать + отдельная метрика «активности» (Меркурий/Уран/Нептун весят 0).
13. **Time-sensitivity UX** — разделять время-устойчивые (транзиты/знаки) и время-зависимые (Asc/MC/дома/астрокартография ~15°/ч) выводы; предупреждать при неточном времени.
14. **`.se1` бандлинг** — приоритет именно для астрокартографии/solar-return (MOSEPH портит угловую точность).
15. **Персистентная сохранённая карта/профиль** в продукте (`natal_chart_id` TODO; локально сделано как `/me`).

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

1. **Цена premium tier:** $9.99 vs $14.99 vs $24.99/мес? _(pricing UI пока хардкодит $9.99 из PLAN-матрицы как placeholder — финальное решение всё ещё за owner'ом; менять в `frontend/app/[locale]/pricing/page.tsx` PLANS + Lemon variant.)_
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
