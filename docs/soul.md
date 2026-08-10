# OneiroScope — Soul

> **English TL;DR:** Living project memory between Claude Code
> sessions. Reference, not log dump — keep it under ~400 lines.
> Closed/resolved items get crossed out or deleted, not piled up.
> §9 (session log) is the only append-only section.

Personal/project memory file for cross-session continuity. Read by Claude Code at every session start (see mandatory block in `CLAUDE.md`).

**Section map:**
- §1 Identity — what this project is
- §2 Active projects / contexts — current branch, KB sources
- §3 Rules / discipline — 5 owner-side rules
- §4 Code style / conventions
- §5 Known issues / tech debt — strike through when resolved
- §6 Architecture decisions log (ADRs)
- §7 Deployment notes
- §8 Open questions / parking lot
- §9 **Session log** (append-only, newest first)
- §10 Rejected ideas (and why)

---

## §1 Identity

- **Project:** OneiroScope — эзотерический сервис: научная астрология (Swiss Ephemeris) + анализ снов (Hall/Van de Castle, REM/NREM) + лунный календарь.
- **Repo:** `alpro1000/oneiro-scope`
- **Owner:** alpro1000 (alpro1000@gmail.com)
- **Stack:** Python 3.11 / FastAPI / Pydantic v2 backend, Next.js 14 (App Router, next-intl RU/EN) frontend, PostgreSQL + Redis, Render.com deploy.
- **Languages:** Code/comments — English. Product UI/content — RU + EN. Owner communicates in RU.

## §2 Active Projects / Contexts

### §2.1 OneiroScope (primary)
- Production target: Render.com (backend + frontend + Postgres + Redis blueprint).
- LLM providers (cost order): Groq (free) → Gemini ($0.075/1M) → Together → OpenAI → Anthropic.
- Default LLM env: `GROQ_API_KEY` or `GEMINI_API_KEY`. Fallback templates exist for all services.

### §2.2 Current branch
- `claude/eager-noether-5UQJR` — adding MCP server + ADK agent + skills layer.

### §2.3 Active freelance
*(none recorded — populate when relevant)*

### §2.4 KB sources
- Astrology: Swiss Ephemeris (SWIEPH binary files), `backend/services/astrology/knowledge_base/` (planets/houses/aspects JSON), `backend/data/lunar_tables.json`.
- Dreams: `backend/services/dreams/knowledge_base/symbols.json` (56 symbols, 7 modern), DreamBank Hall/Van de Castle norms `hvdc_norms.json`, prompts in `backend/services/dreams/ai/prompts/`.
- Geo: GeoNames API (username `alpro1000`, 30k req/day), 90+ city fallback DB.

## §3 Rules / Discipline

5 rules owner enforces (owner-side, NOT Claude Code's job):

1. **Pre-session:** Owner does nothing. Claude Code must read the mandatory block in `CLAUDE.md` within first 3 minutes of any session. If it doesn't — owner stops and reminds.
2. **Post-session:** Owner verifies Claude Code updated `docs/soul.md §9` (Session log). Last Gate of every task. If forgotten — owner asks: *"Update docs/soul.md §9 with this session log."*
3. **Architectural decisions** (new AI provider, DB switch, Core↔Kiosks pattern change, new MCP tool taxonomy): update `docs/steering/*.md` — usually `tech.md` or `structure.md`.
4. **New project / case / corpus:** update `§2.3` (Active freelance) or `§2.4` (KB sources) here.
5. **Project Knowledge sync (claude.ai online):** owner copies `soul.md` + `steering/*` into Project Knowledge on claude.ai weekly (or after major update). Claude Code (CLI/home) sees this via Git automatically.

**NOT discipline (skip):**
- Every commit → soul.md update: NO, only for substantial work.
- Updating tasks/specs: not mandatory if spec is finished — just archive the status header at the top.
- Versioning steering docs: only on major rewrite.

## §4 Code style / Conventions

- Backend: Pydantic v2 strict contracts, async services, no mocks in production code, fallback templates instead.
- LLM: provider abstraction via `UniversalLLMProvider`, cost-ordered selection, retry-with-fallback.
- Frontend: Server components for SSR data fetch, client components only when interactive. next-intl for all user-facing strings.
- Tests: pytest backend, jest frontend. No new feature ships without at least a smoke test.
- Commit messages: imperative ("add", "fix", "refactor"), no Claude Code session-id leak into commit body.

## §5 Known issues / Tech debt

- **Биллинг подключён к выдаче `chart_core`** (2026-07-29 найдено «построен и
  подключён к нулю точек»; 2026-07-30 гейт на натальную карту подключён —
  `entitlements.check_chart_entitlement`). Что закрыто: три двери выдачи
  `chart_core` (`POST /api/v1/chart`, `POST /api/v1/astrology/natal-chart`,
  MCP `calculate_natal_chart`) теперь метрируют free = одна карта навсегда.
  **Что ещё НЕ метрируется** (осознанно, по §8 владельца — «отдельными
  entitlement'ами, следующий шаг»): PDF-отчёты, транзиты, соляры, прогнозы,
  серверная астрокартография (`compute_transits`, `astrocartography_*`,
  `solar_return_*`, `forecast_event`, `horoscope_report`, `profile_report_file`).
  Эти инструменты принимают сырые данные рождения и считают на сервере, то есть
  пока остаются мягким обходом натального гейта до своих entitlement'ов.
  **Остаточная зависимость по MCP:** durable-метрирование коннектора живо, когда
  `MCP_REQUIRE_AUTH=true` И субъект долетает до инструмента; при открытом
  коннекторе (`MCP_REQUIRE_AUTH=false`) выдача честно штампуется `gated:false`,
  не молча. Полное объединение веб- и коннектор-аккаунтов (один пользователь,
  оба провайдера) — отдельная работа, не сделана.
- No user auth / natal chart persistence (TODOs in `backend/api/v1/astrology.py:59,102,175`).
- ~~5/14 dream interpreter tests failing (64% pass rate).~~ **Fixed 2026-05-26 in `claude/fix-dream-narrative-tests`** — 14/14 passing.
- ~~`ENVIRONMENT=production` not yet set on Render~~. Already set in `render.yaml` (verified 2026-05-26).
- ~~LLM cost tracking middleware structure exists but counter not wired~~. **Fixed 2026-05-26 PR #111** — `backend/core/cost_tracker.py` wired into `UniversalLLMProvider.generate()`.
- ~~Ephemeris mode (SWIEPH vs MOSEPH) not logged in `/health`~~. **Fixed 2026-05-26 PR #111** — and now also logged on app startup (PR #113).
- LunarWidget no retry on 502.
- **Fallback city database is thinner than advertised** (found 2026-07-27, not
  fixed). `POPULAR_CITIES` in `backend/utils/geonames_resolver.py` holds **55**
  entries, while its own comment, the `search_city` docstring and CLAUDE.md all
  claim "90+". Missing: Plzeň, Cyrillic "прага", and every Spanish city. Without
  `GEONAMES_USERNAME` this makes `search_city("Плзень, Чехия")` return
  `PLACE_NOT_FOUND` — honest, but unusable. Secondary: its Zaporizhzhia
  longitude (35.1969) is ~6 km off GeoNames' 35.11714, so the fallback and API
  paths yield slightly different charts for the same city. Fix needs a real
  source for coordinates, not hand-picked numbers — either a proper offline
  dataset or an explicit decision that the fallback stays minimal and the
  "90+" claim gets corrected.
- **`build-and-validate` CI is red on every PR** (pre-existing). Diagnostic improvements landed in PR #113 (`pip install -v`, upgraded setuptools/wheel); next iteration should see the actual error trace. Not blocking — `mergeable_state` is `unstable` not `blocked`.

## §6 Architecture decisions log

See `docs/steering/tech.md` for technology choices and `docs/steering/structure.md` for layering.

Recent decisions:
- **2026-05-26** — Adopting MCP-first architecture. MCP server wraps existing FastAPI services as tools; ADK agent built on top; skills consume the agent. Rationale: reusable across Claude Desktop / Cursor / web Claude Code; one set of contracts.
- **2026-07-08** — `/client-report` PDFs must carry an inline plain-language glossary (angles/aspects/flags/theme meaning) instead of relying on the reader asking a follow-up. Trigger: a live client couldn't parse the transit table in a delivered report. Encoded as a non-negotiable behavior rule + PDF-structure step 1b in `.claude/skills/client-report/SKILL.md`. Also documented there: `astrocartography.theme_scan`'s displayed `score` is the *general* composite (`_score_hits`: Venus/Jupiter weight 3.0, Sun/Moon weight 1.0, Saturn/Pluto weight -1.5, Mars weight -1.0; **Mercury/Uranus/Neptune contribute exactly 0**) — a tight, theme-relevant Uranus-MC or Mercury-Desc hit can carry a low composite score while still being a real, tight, meaningful contact. Two different-sounding readings of the same city ("great for luck" vs "great for business") can both be correct — they're reading different planets on different angles, not contradicting each other.
- **2026-07-08 (follow-up)** — owner asked to go further: show ALL four angles for every city (not one pre-filtered theme) and always explain the composite score either way ("не значит что там плохо, но а если плохо то почему"). Implemented as real code, not just a report-writing convention: `astrocartography.py` gained `angle_hit_archetype()` (planet-on-angle → cited description, composing the existing `archetypes.planet_in_house_archetype` since Asc/IC/Desc/MC anchor houses 1/4/7/10 — Jim Lewis reads angle lines this way), `full_angle_breakdown()` (every contact within orb, tagged benefic/challenging/neutral using the same `_BENEFICS`/`_MALEFICS` dicts as the score, cited confidence 0.9), and `score_explanation()` (names which contacts drove the score, or says plainly "quiet zone" / "score is low but here's a real contact it can't see"). Wired into `compare_locations()` (now returns `full_breakdown` + `score_explanation` per location) and the `astrocartography_point` MCP tool. `report.render_html()` now opens with the plain-language glossary and lists the full breakdown per city instead of a truncated 6-hit list. Verified against `backend/tests/test_strategic_astro_tools.py`'s existing assertions (Brno Moon-Asc, Warsaw/Prague clean flag, build_report/render_html structure) by hand-running them in a dependency-light venv (no pydantic/fastapi installed in this session's container) — all pass unchanged, new fields additive only.
- **2026-07-08 (follow-up 2)** — owner pushed on two things: (a) "не терять ничего" — even the caveat text wasn't enough, wanted the excluded planets actually counted somewhere; (b) asked point-blank how the `_BENEFICS`/`_MALEFICS` weights (Venus/Jupiter=3.0, Sun/Moon=1.0, Saturn/Pluto=-1.5, Mars=-1.0) were derived. Honest answer given and now documented: the *categorical* claim (Venus/Jupiter benefic, Saturn/Mars malefic) is real classical doctrine (Ptolemy, Tetrabiblos, 2nd c. CE); the *specific numbers* are a pre-existing engineering heuristic in this file (predates this session), not a cited weighting — and the file's own old comment ("Sun/Moon are strong but neutral") already contradicted its own code (which weights them +1.0), a real inconsistency now called out in the docstring rather than left silent. Rather than inventing a fake +/- sign for Mercury/Uranus/Neptune (which have no agreed classical or modern valence — Mercury is classically "common", the outer three are modern/1781+ with no traditional valence at all) just to fold them into `score`, added a second, valence-free metric: `contact_strength()` (angle-weighted tightness of one contact) and `total_significance()` (unsigned sum across all 10 bodies). Wired into `score_explanation()`'s return + prose, and into `report.render_html()`'s per-city display ("score X · angle load Y"). Concrete proof this isn't cosmetic: Girona scores only +0.74 (score) but `total_significance` = 3.58, *higher* than Warsaw's 3.1 (score +5.72) — Girona's tightest contacts (Uranus-MC 0.37°, Mercury-Desc 0.35°) are real and strong, just unscored by the valence formula. `.claude/skills/client-report/SKILL.md` now requires showing both numbers side by side, always.
- **2026-07-08 (pattern: home-vs-work axis split)** — comparing candidate cities for "where to live" vs "where to work" (Girona/Blanes/Barcelona vs Brno/Ostrava/Plzeň, owner's own chart) surfaced a reusable pattern worth codifying, not just a one-off script: a city's `total_significance` can sit ENTIRELY on one life axis. Girona/Blanes/Barcelona carried 100% of their significance on the work axis (Uranus-MC, Mercury-Desc, Sun-Desc — houses 10/7) and exactly 0 on the home axis; Brno/Ostrava were the mirror image (Moon-Asc, Venus-IC, Mars-IC — houses 4/1) with 0 on the work axis. A single ranked list or composite score erases this split entirely, making "best city" look like one question when it's really two. Added `astrocartography.home_vs_work_focus(result)`: splits `total_significance` into `home_significance` (IC/Asc) and `work_significance` (MC/Desc) with a plain verdict (work zone / home zone / mixed / quiet-on-both). Wired into `compare_locations()` (new `axis_focus` field per location) and the `astrocartography_point` MCP tool. Also incidentally confirmed the owner's own read of Plzeň ("не очень подходит"): rank #177/211 on their chart, score -0.22, driven by a tight Mars-IC (0.73°, home-axis tension) with only weak/wide compensating benefics — while Brno (#16, score +3.18, Moon-Asc almost exact at 0.02°) and Ostrava (#8, +4.24) are both far stronger *home*-axis candidates in the same country. `.claude/skills/client-report/SKILL.md` now requires the axis split whenever a report compares ≥2 candidate cities.

## §7 Deployment notes

- Render blueprint: `render.yaml` (backend + frontend + Postgres + Redis).
- Env vars exchange via `RENDER_EXTERNAL_URL` (frontend ↔ backend).
- After updating `NEXT_PUBLIC_*` envs → **Clear build cache & Deploy** on frontend.
- LLM keys stored as Render secrets (`sync: false` in blueprint).

## §8 Open questions / Parking lot

- Should MCP server run as separate Render service or embedded in backend? → Leaning separate: cleaner cost/security boundary.
- Auth strategy for MCP HTTP transport? → JWT? OAuth? Bearer token from Render env initially.
- Cache strategy for natal charts before user-auth lands → Redis with content-hash key (birth_date+place+time).

---

## §9 Session log

### 2026-08-10 (3) — legacy-грант без ключа, isError на отказе, реестр в диагностике

Отчёт владельца после передеплоя дал два настоящих бага и третий заход
одной и той же ложной тревоги.

- **Грант без ключа — стена.** `free_natal_used` существовал до колонки
  ключа; миграция 0002 добавила её NULL-ом. `same_chart(None, …) → False`,
  и такой аккаунт получал `entitlement_required` на ЛЮБУЮ карту, включая
  свою. Прежний комментарий в коде называл отказ «безопасным чтением» — для
  grandfathered-строк это неверно: обещание «своя карта доступна навсегда»
  тихо превращалось в «никакая и никогда». Теперь: грант, который нечем
  сравнить, — грант; следующая выдача усыновляется как выданная карта,
  grace одноразовый.
- **`isError: false` на отказе** (замечание владельца, точное): отказ,
  вернувшийся обычным результатом, неотличим от успешного вычисления для
  универсального клиента. Теперь `ToolError` с JSON-пейлоадом отказа.
- **«Unknown tool» в третий раз** — transit_arc и компания не публикуются
  сервером с WP-10; это кэш коннектора (свежий `meta.commit` едет в ответе,
  список инструментов — нет). Чтобы больше не спорить словами, в
  `/connect/diagnostics` добавлено поле `tools`: реестр, который отдаёт
  именно этот процесс. Урок: **доказуемый URL заканчивает спор, который
  не заканчивают три объяснения.**

### 2026-08-10 (2) — модерация каталогов: самоописание сверено с поведением

Запрос владельца — «чтобы точно прошёл модерацию Claude и ChatGPT». Гарантий
не существует; существует класс отказов «сервер говорит о себе не то, что
делает», и он устраняется целиком:

- **Инструкции сервера** больше не называют астрологию наукой — фраза
  «science-grounded astrology» противоречила нашему же domain.md и была
  готовым штампом отказа. Заявлено то, что код реально принуждает: расчёт
  детерминирован, толкование — традиция и маркируется, советы — нет.
- **ToolAnnotations на всех 19** — и это обещания, поэтому из кода, а не из
  эстетики: `calculate_natal_chart` НЕ read-only (сжигает пожизненный грант),
  но идемпотентен (same_chart); `analyze_dream` НЕ read-only при remember и
  НЕ идемпотентен (append); openWorldHint только там, где GeoNames.
  `test_mcp_moderation.py` сверяет и греппит описания теми же шаблонами,
  какими греппит ревью.
- **`dcr_advertised` в диагностике.** Claude сам регистрируется OAuth-клиентом
  до того, как отправить человека логиниться; issuer без
  `registration_endpoint` убивает поток символом «Failed to start MCP
  authorization» на экране пользователя — при полностью правильной нашей
  конфигурации. Auth0 поставляется с выключенным флагом. Теперь это строка
  с fix'ом, а не загадка.
- **`submission-pack.md`** — паст-реди тексты обеих заявок и честный список
  оставшихся блокеров; все пять — вещи владельца (лицензия SwissEph,
  контакт в privacy, DCR-флаг, тестовый аккаунт, платный инстанс на ревью).

### 2026-08-10 — CORS: прод был недоступен фронту целиком; и три расхождения вида с сервером (#185)

**Повод (владелец):** «И ЕЩЁ КУЧА ОШИБОК» + консоль браузера, полная
`No 'Access-Control-Allow-Origin' header is present` с `oneiroscope.vercel.app`
на `oneiroscope-backend.onrender.com`: города, лунные дни, вход, регистрация.

**Причина — переменная, которой никогда не было.** `ALLOWED_ORIGINS` стоял в
`render.yaml` как `sync: false`, то есть существовал только приглашением в
дашборде Render и не был выставлен ни разу. В проде применялся дефолт для
разработки, `http://localhost:3000`.

**Почему это не всплыло раньше — и главный урок сессии.** Отказ по CORS
невидим со стороны сервера: запрос маршрутизирован, обработан и отвечен 200,
`/health` зелёный, лог чистый. В ответе просто нет заголовка, и знает об этом
только браузер. Каждый сигнал, доступный оператору, говорил «сервис исправен».
Это ровно то тихое вырождение, которое запрещает conventions.md §12, поэтому
чинилось не одно значение, а видимость поломки:

- `render.yaml` несёт `value:`, а не обещание — фикс приезжает с деплоем;
- `cors_problem()` формулирует поломку одной фразой (config.py);
- она печатается `logger.error` на старте и висит строкой `browser_origins`
  в `/connect/diagnostics` — URL, который владелец может открыть без доступа
  к логам;
- `ALLOWED_ORIGIN_REGEX` для preview-деплоев Vercel: opt-in и заякоренный,
  потому что API отвечает с credentials.

`test_cors.py` (15) воспроизводит симптом буквально: **200 без заголовка**.
Тест, у которого нечего ассертить в логе, — и в этом вся суть.

**Данные рождения владельца отгружались каждому посетителю.** `demo-chart.ts`
содержал его реальные дату/время/город и грузился начальным состоянием на
`/natal` и `/astrocartography` — то есть прошлая починка (#183) убрала их из
формы, но не из `useState`. Для читателя это хуже утечки: карта, которая
выглядит как твоя, но принадлежит другому человеку, — не образец, а неверный
ответ. Заменено на Гринвич, полдень 2000-01-01 (место и момент, не человек),
числа из серверного `build_chart_core`, плюс баннер `isSample`.

**Три расхождения вида с сервером, все найдены разбором PR.**

1. `relocations.ts` объявлял `orb`, сервер отдаёт `orb_deg`. Каждый контакт
   рисовался как `орб 0.00°` — и эта выдуманная точность уходила в чат
   кнопкой «объяснить». **Вид, который врёт модели числом, выдаёт себя за
   детерминированный слой (1.0), сочиняя.** Паттерн `(v ?? 0).toFixed()`
   теперь запрещён тестом по всем шести видам.
2. Сортировка городов по весу убрана: `compare_locations` документирует себя
   как сравнение, а не рейтинг (вес не считает Меркурий/Уран/Нептун ни при
   каком орбе). Рядом показана `total_significance`.
3. `pattern-map.ts`: `mc.conjunct` — контакт `{planet, orb_deg}`, а не
   положение; линчпин `same_ruler` несёт одну планету, а не пару; `pick`
   принимал все шесть конвертов `_base()`.

`test_view_payload_contract.py` (15) сверяет имена полей с живыми ответами
сервера — **`tsc` проверяет только веру вида в саму себя**, связи с Python,
который эти поля производит, у него нет.

**Лестница доверия разошлась сама с собой.** Комментарий внутри `layers.py`
утверждал `USER_CONTEXT = 0.6`, тогда как код десятью строками ниже ставил
`0.9`; CLAUDE.md декларировал четыре ступени при восьми слоях в коде. Для
проекта, чьё обещание — «у каждого утверждения своя уверенность», это значит,
что показанное число обосновывалось правилом, которого никто не исполняет.
Сведено: каждый слой стоит НА ступени либо между двумя с письменной причиной
(0.85 — статистика без поцитатной ссылки). `USER_CONTEXT = 0.9`, потому что
«не обобщается» — про охват, а не про уверенность.
`test_confidence_ladder_docs.py` (11) роняет CI при новом расхождении.

**Владелец не мог пользоваться собственным продуктом.** Бесплатный тариф даёт
одну карту на всю жизнь и применялся к нему ровно как к покупателю: после
первой карты любая проверка платного пути отвечала `entitlement_required`.
Гейт, через который нельзя пройти, нельзя и проверить. `STAFF_ACCOUNTS`
(пусто по умолчанию) поднимает названные аккаунты до PRO — **в `current_tier`,
а не у конкретной двери**, и `test_staff_accounts.py` это утверждает
отдельно, чтобы обход нельзя было добавить одному гейту и забыть у
следующего.

**Обзор конкурентов (агент, 54 инструмента).** `astrologyapi.com` закрыт
egress-политикой, читалось по выдаче. Выводы, которые стоит помнить:
- **Swiss Ephemeris — гигиена, а не преимущество.** Им пользуются VedAstro,
  W8s, intellecat, AskSoma, Kerykeion; Astrodienst его написал.
- **Категория снов в MCP пуста** — не тонкая, пустая. HVdC-реализации
  существуют только академическими репозиториями (DreamAnalyzer, DReAMy,
  TXMM) без инструментного слоя.
- **Ни один астрологический или сновидческий сервер не поставляет MCP Apps.**
- Связывающее ограничение — невидимость: нас нет ни в одном каталоге.
  Отсюда `server.json` + `docs/deploy/directories.md`.

**Ложная тревога, которую стоит записать:** внешний анализ сообщил «MCP
публикует 46 инструментов, из них `transit_arc` и `physiognomy_methods`
отвечают Unknown tool — P0». Проверка сервера напрямую: **19 инструментов**,
названных среди них нет, `test_capability_menu.py` отдельно утверждает их
отсутствие. Это устаревший кэш коннектора у клиента, а не расхождение схемы
и деплоя. Лечится удалением и повторным добавлением коннектора.

**Отказ.** Владелец попросил физиогномику «для всех включая отдел кадров».
Физиогномика оставлена и по-прежнему бесплатна для всех (гейта на ней нет),
но HR-применение — нет: AI Act ЕС запрещает распознавание эмоций на рабочем
месте (Ст. 5) и биометрическую категоризацию для вывода чувствительных
характеристик, а подбор персонала отнесён к высокому риску; содержательно
черты лица коррелируют с расой, возрастом и инвалидностью, то есть такой
инструмент отмывает защищённые признаки в кадровый сигнал под видом расчёта.
Собственный дисклеймер продукта уже это запрещает — строка не снята.

**Замечено, не починено:** `inventory-bot` пушит коммит в ветку, и его
workflow-прогоны встают в `action_required`. Голова ветки всегда «не
зелёная» при зелёном коде; зелёное меряется на коммите ниже.

### 2026-08-06 (part 10) — свои данные вместо владельческих, /connect, правовые тексты; два фикса из аудита (#183)

**Повод (владелец):** «надо чтобы на фронте можно было вводить свои данные и
вводить город для картографии, потому что пока это выводится с датой моего
рождения и моими городами из запросов; и ещё страничка с инструкцией
получения MCP и GDPR и остальные условия — придумай и пропиши».

**Данные владельца были зашиты в трёх местах.** `1977-07-01 / 22:30 /
Запорожье / 47.8388,35.1396` стояли `useState`-дефолтами на `/natal` И
повторно на `/astrocartography`; «быстрый переход» на карте был фиксированным
рядом из семи его городов; тем же рождением был пример в connect-копии
портала. Форма теперь стартует пустой, введённое общее для обоих экранов
(`lib/birth-data.ts`, localStorage), города строятся из истории поиска ЭТОГО
пользователя (`lib/recent-cities.ts`).

Ввод — предложение с пропусками (директива дизайн-системы), и это заодно
меньше вопросов: город подставляет координаты, шесть полей → три пропуска +
координаты в моно, которые видны всегда (они решают карту), сворачиваются
только поля ввода. **Выпадашка TZ убрана совсем** — она требовала знать
смещение своего года рождения, а `POST /api/v1/chart` выводит зону из
координат с историческими правилами и возвращает применённую. **«Время
неизвестно» стало галочкой:** пустое поле не отличает «не ввёл» от «не знаю»,
а молчаливый полдень запрещён §12.

**Правовые тексты написаны по АУДИТУ КОДА, не по шаблону** (подагент прошёл
модели, провайдеров, логи, cookie, экспорт/удаление). Поэтому там есть и
неудобное: цепочка фолбэков LLM может доставить один запрос нескольким
провайдерам; через коннектор толкование выключено и текст сна никуда не
уходит, через веб/REST — включено; в логи попадает IP при рейт-лимите и
название места рождения. На каждой странице стоит, что юрист не смотрел.

**Аудит нашёл два расхождения текста с кодом — оба закрыты (по решению
владельца через AskUserQuestion, оба «рекомендую»):**

1. **Удаление не удаляло.** `DELETE /api/v1/users/me` ставил
   `pending_deletion_at = +30 дней` под обещание, что почистит крон. Крона НЕ
   существовало: колонку никто не читал, планировщика в деплое нет. Почта,
   хеш пароля, `free_natal_chart_key` (это момент рождения + координаты) и
   серия снов лежали вечно, пока кабинет писал «данные удалены». Теперь
   стирает при подтверждении, одной транзакцией, каскадом по объявленным
   `ON DELETE CASCADE`. Окна «передумать» больше нет — сознательно: ст. 17
   GDPR просит «без неоправданной задержки», а планировщика всё равно нет.
2. **UUID — не авторизация.** `analyze_dream(store_for_user_id=…)` и
   `dream_series_stats(user_id=…)` брали целевого пользователя прямо из
   вызова; узнав чужой UUID, можно было читать и дописывать чужой дневник
   снов. Оба резолвят свой аккаунт из OAuth-субъекта. Починка **структурная**:
   ни один параметр не называет пользователя → подделывать нечего. Дневник
   остался opt-in как `remember=True`. Поверхность 19 инструментов цела.

**Урок про CI:** `smoke` упал не на поведении, а на переименовании — тесты
портала патчили `users_api.request_account_deletion` через
`monkeypatch.setattr`, который на несуществующем атрибуте кидает. Локально
эти тесты не запускаются (в песочнице starlette ломает импорт модуля), так
что увидел только на CI. Тест ещё и утверждал наличие даты чистки, которая
никогда бы не наступила — теперь утверждает обратное.

### 2026-08-05 (part 9) — «всё собирай, по твоему усмотрению»: мержи #178–#181, схема БД под миграциями (#182)

**Повод:** после разбора прод-багов владелец сказал «Все собирай. По твоему
усмотрению» — закрыть остатки тех-долга без пошагового согласования. Пять PR.

**PR #178 (`33f9066`) — решение «19 остаётся» в коде.** Владелец: «ну я
зачем-то делал 19?» — срез WP-10 в силе. Значит `decade_map`, `life_pivots`,
`transit_arc` не возвращаются, а скиллы `/decade-map` и `/life-pivots`,
которые их звали, переписаны на **композицию** живых инструментов:
`calculate_natal_chart` + `compute_transits` (годовые окна, возвраты считаются
из аспектов) + `solar_return_chart` (годовая выборка для домов/углов, честно
«окно, не дата») + `lookup(transit_meaning)`. Диагноз ChatGPT «рассинхрон
схемы и сервера» проверен по git и **отклонён**: инструменты сняты намеренно
коммитом `6d5b948`, реестр ↔ `analysis_plan.STAGES` ↔ AST-страж сходятся;
«Unknown tool» — до-срезный КЭШ клиента. Владельцу: обновить коннектор.

**PR #179 (`c7a35e1`) — последние старые поверхности на дизайн-систему.**
`VoiceInput` и `CityAutocomplete` (framer-motion долой, латунь вместо
зелёного/красного, координаты моноширинным в каждой подсказке), `/account` и
`/checkout/success`. Заодно ссылка «начать пользоваться» после оплаты вела на
удалённый `/astrology` → `/natal`.

**PR #180 (`58f7dff`) — три штуки по следам гейта и лица.** (1) `same_chart`:
та же карта опознаётся с допуском по МЕСТУ (0.1° ≈ 11 км — разные геокодеры
дают разные координаты одного города), но НЕ по мгновению — момент рождения
сравнивается точно. (2) Отказы гейта локализованы (ru/en) — до этого
англоязычный текст падал в русский диалог. (3) `/face` показывает то, чему
бэкенд сам доверяет: `traits`, `signature`, `lens_note`, а чтения со
`scope: "background"` визуально приглушены.

**PR #181 (`ff54342`) — тесты платного гейта не запускались НИГДЕ.** 24 теста
`test_chart_gate.py` не были ни в одном workflow — мёртвый груз с момента
написания. Подключены; добавлен `test_chart_gate_postgres.py` против живого
Postgres в CI (сервис-контейнер), потому что локально гейт непроверяем:
`postgresql.UUID` не рендерится на SQLite. По дороге: `pg_isready` смотрел в
несуществующую базу; `poolclass=NullPool` — иначе asyncpg-соединение из
прошлого теста тянуло «Future attached to a different loop».

**PR #182 (`8ed8a95`) — схема БД наконец под миграциями.** Закрывает костыль
из #175. Alembic **никогда не запускался на деплое**, базовые таблицы создавал
только `create_all`; цепочка миграций не имела начала (0001 ссылалась на
`users` внешним ключом, 0002 только ALTERила). Добавлен `0000_baseline` из
`Base.metadata` c `checkfirst` — из метаданных, а НЕ рукописным DDL, потому
что это бейзлайн для уже существующих БД и сверить их описание неоткуда;
`downgrade` кидает (откат бейзлайна = дроп всех таблиц с боевыми данными).
0001/0002 усыновляют найденное через inspector. `render.yaml`: `upgrade head`
перед uvicorn через `&&` — упавшая миграция обязана останавливать загрузку.
**Побочная находка, которая чуть не уехала в прод:** `script_location =
alembic` в `alembic.ini` резолвился от рабочей директории, и команда деплоя из
корня репозитория не нашла бы каталог версий вовсе → сервис не поднялся бы.
Исправлено на `%(here)s`; мой же тест это скрывал, потому что переопределял
`script_location` у себя — теперь есть тест, который резолвит команду деплоя
как есть, без БД.

**Что осталось незакрытым (честно):**
- Регистрация SW живёт только в мёртвом `public/vendor/chart-store.js` — §8 п.6.
- Гейт врезан в `calculate_natal_chart`; `vocation_map`, `money_contour`,
  астрокартография — нет (наблюдение владельца, один шов ещё не сделан).
- Калибровка физиогномики (элементы опираются на семейство ширин, которое сам
  бэкенд зовёт ненадёжным; дворы перекошены обрезанным лбом; MCP-инструменты
  физиогномики не зарегистрированы → `/face-portrait` не запускается).
- Прайс/Stripe и текст легальных страниц — на владельце, не на мне.

### 2026-08-03 (part 8) — прод-баги владельца и ChatGPT-проверка; мержи #175–#177; решение «19 остаётся»

**Повод:** владелец прогнал живой расчёт через ChatGPT-коннектор и принёс
баг-репорт (плюс скриншоты «разделы не работают» днём ранее). Три PR за блок.

**PR #175 (`d245aee`) — три прод-бага из отчёта владельца:**
- 🔴 натал 500 `UndefinedTable "users"`: таблицу создавал только `init_db()`
  (гейтован на development), миграции CREATE нет (0002 — только ALTER), на
  Render `ENVIRONMENT=production` и `alembic upgrade` нигде → таблицы не было
  никогда. Фикс: `init_db()` (идемпотентный `create_all`, checkfirst) во всех
  окружениях + импорт `backend.models` перед ним. Follow-up: Alembic-бейзлайн.
- скан прятал Меркурий/Уран/Нептун за score 0.0 (Атланта Уран→Asc 6.0° ≡
  пустой Чикаго): в каждую строку added `total_significance` + `unweighted`
  (те же поля, что у point) + верхний `note` «ранжируйте по significance».
- провенанс без версии: `_PROVENANCE` в pattern_engine (и report, и
  methodology-строки) → единая `EPHEMERIS_VERSION` («Swiss Ephemeris 2.10.03 /
  JPL DE431 .se1 files (SWIEPH)»).

**PR #176 (`41a15b5`) — почему фиксы «не доезжали» до телефона владельца:**
sw.js был cache-first для ВСЕГО, включая HTML-документы (`cached || network`) —
URL страницы не content-addressed, и вернувшийся посетитель вечно крутил
предыдущий деплой (скриншот: новый Header + старое «Load failed» = смесь двух
сборок). Навигации теперь network-first (кэш = офлайн-фолбэк), чанки/модель —
cache-first, VERSION v4→v5. ⚠️ Регистрация SW живёт ТОЛЬКО в
`public/vendor/chart-store.js` (наследие удалённых прототипов) — новые
посетители без SW вообще; управляемая регистрация = §8 п.6. Заодно: /dreams
переписан на приборную систему И теперь показывает детерминированный слой
(hvdc_evidence с клаузами и правилами 1966, norm_comparison с юнитами и
честным «не вычислена», degraded-леджер, дисклеймер рядом с результатом) —
раньше фронт показывал ТОЛЬКО прозу LLM, типы даже не объявляли эти поля;
/face-шелл и сканер — на токены.

**PR #177 (`15f7351`) — greenlet_spawn на нат-гейте.** После создания users
вылез следующий слой: ленивая загрузка `user.subscriptions` из синхронного
current_tier внутри async-запроса. Паттерн владельца «первый вызов падает,
повторный работает» подтверждает: коммит гранта происходит ДО падающей строки
(первый вызов — новый аккаунт, падение после commit; второй — аккаунт есть,
selectinload, всё загружено). Фикс: новорождённому `subscriptions = []`;
подписки снимаются один раз до коммита и передаются `active_subs` во все три
вызова; вся секция обёрнута — сбой хранилища теперь = структурный отказ
«не могу проверить право» (fail closed), не 500. ⚠️ Честно: локальный репро
невозможен (User.id = postgresql.UUID, SQLite его не рендерит, Postgres в
песочнице нет) — точную строку подтвердит только прод-трейсбек. ⚠️ Урок:
test_chart_gate.py на SimpleNamespace — ни ORM, ни сессии, класс бага невидим;
нужен Postgres-тест гейта в CI.

**Проверка отчёта ChatGPT (4 пункта, «он может галлюцинировать но проверь»):**
1. greenlet — ✅ реальный, фикс #177 (см. выше).
2. «decade_map/life_pivots/transit_arc объявлены, но Unknown tool» — факт
   верный, диагноз («рассинхрон MCP schema ↔ backend», «разные инстансы») —
   ❌ неверный. По git: инструменты БЫЛИ зарегистрированы и осознанно сняты
   срезом WP-10 `6d5b948` (47→19). Текущий сервер внутренне консистентен:
   реестр 19 ↔ STAGES 15 ↔ страж `test_registry_matches_the_wp10_surface`.
   Источник призраков — КЭШ КЛИЕНТА: коннектор ChatGPT держит до-срезный
   список инструментов. Лечение: обновить коннектор.
3. Геокодинг «Запорожье» с предупреждением о неоднозначности — ✅ работает
   как спроектировано (после инцидента с хутором «Україна»): выбор
   крупнейшего + честный warning + candidates.
4. Смена commit d245ae→41a15b посреди сессии — ✅ объяснено: два моих мержа
   (#175 15:52, #176 18:25 UTC), Render автодеплоит; один инстанс,
   последовательно. #176 MCP не трогал → «Unknown tool» не отсюда.
   Бонус: meta-блок WP-6 сделал деплой видимым снаружи.

**Решение владельца: «Ну я зачем-то делал 19» — срез в силе, инструменты НЕ
возвращаем.** Следствия закрыты этим же блоком: скиллы /decade-map и
/life-pivots переписаны с мёртвых `mcp__oneiro__decade_map`/`life_pivots`/
`transit_meaning` на композицию из живой поверхности: calculate_natal_chart
(фундамент) + compute_transits годовыми окнами (точные даты аспектов,
возвраты Сатурна/Юпитера читаются прямо из списка) + solar_return_chart как
годовая выборка позиций для домов/углов (честно помечено «окно, не дата») +
lookup(topic="transit_meaning"). Владельцу: обновить ChatGPT-коннектор;
факт «код decade/pivots не раскрыт нигде» (веб-роутов нет, вопреки фразе
WP-отчёта «остаётся для веб-API») зафиксирован.

**Дальше:** владелец проверяет натал первым вызовом после деплоя #177
(meta должен показать commit 15f7351); прайс/connect/кабинет; разбор лица
(бэкенд-смещения + traits/signature на фронте) в бэклоге.

### 2026-07-30 (part 7) — навигация + главная на дизайн-системе; мержи #171 и #172

**Повод:** владелец увидел «смешался старый и новый фронт» (скриншоты) и выбрал
следующим шагом «навигация + главная». Плюс добить лунный календарь (#171).

**PR #171 (лунный календарь) → merge `90038f0`.** Единственный красный —
CI-шаг `test-ui.yml` «Smoke test lunar API»: `curl -sf http://localhost:3000/
api/lunar` требовал 200 с данными. После §12 (убран тихий мок-фолбэк) эндпоинт
честно отдаёт **502**, когда бэкенда нет — а в CI его нет; `-f` роняет curl,
файл пуст, шаг падает. То есть сам CI-шаг держался на фейковых данных, которые
§12 и запретил. Переписан: `curl -s -o … -w "%{http_code}"` ловит код →
**200** валидирует `date/phase/illumination`, **502** принимает как честный §12-
отказ (проверяет поле `error`), иначе фейл с логом dev-сервера.

**PR #172 (nav + home) → merge `ea8b157`.** Старый Tailwind-Header и framer-
motion/slate-главная рендерились поверх новых приборных экранов — это и был
«микс»; nav вдобавок не вёл на natal/astrocartography вообще.
- **Header** на токенах (abyss-фон, единственный акцент латунь, parchment,
  1px-границы `--grat-2`, без градиентов/блюра — скругление/тени убиты глобально
  в tokens.css). Nav перелинкован: **natal · astrocartography · calendar**
  первыми + dreams · account; старые `/astrology` (заменён `/natal`), `/face`
  (не работает), `/pricing` (оплата блокирована на владельце) убраны из меню до
  перестройки — по прямым URL живут. Активный пункт — `usePathname` + латунное
  подчёркивание. Оставил next-intl → все 5 локалей сохранили переведённый nav;
  ключи `natal`/`astrocartography` добавлены в en/ru/de/es/fr.
- **LanguageSwitcher** — компактный моно-латунный тумблер (хайрлайн-разделители),
  переключение с сохранением пути не тронуто.
- **Главная** (`app/[locale]/page.tsx`) переписана как лёгкий **Server
  Component**: «индекс приборов» — 4 рабочих инструмента карточками-панелями,
  сверху правило дома (числа воспроизводимы, смысл — традиция) + обязательный
  рефлексивный/развлекательный дисклеймер. Долой framer-motion, хардкод
  slate/indigo/amber и дубль-хедер внутри страницы. i18n как у приборных
  экранов: ru/en инлайн, английский фолбэк для de/es/fr. First Load **145→96 КБ**.

**Проверка (ultracode, «Проверь»):** состязательный ревью диффа — 5 направлений
находят, каждая находка независимо перепроверяется по коду (Workflow, 14
агентов). CI на #172 был 10/10 зелёный сам по себе. Ревью: **design-compliance
чисто** (ни хардкод-цветов/градиентов/второго акцента, дисклеймер есть, языка
предсказаний нет); 9 находок → **5 подтверждено / 4 отклонено** (вкусовщина:
Radix vs Geburtshoroskop, Astrocarto, Астрокарта vs -графия, «убрали кастомные
focus-ring» — дефолт браузера остаётся). Починил (`61e2034`):
- «Open →»: inline-`color` перебивал CSS-правило `.tool-card:hover .tool-open`
  (мёртвый код + мёртвая анимация), а `--dim` на `--shelf` = 3.48:1 < AA. Вынес
  базовый стиль в globals.css, цвет `--dim`→`--muted` (AA ок), добавил
  `:focus-within` (клавиатурный юзер тоже получает латунную подсветку).
- Мобильный хедер (лого + 5 языков + бургер, без wrap) переполнялся <~330px
  (провал reflow 320px) → переключатель языка ушёл в раскрывающееся меню, верх =
  лого + бургер.
- Восстановил латунные `:focus-visible` рамки (в старом хедере были).
- **Отклонил как out-of-scope:** контраст `.eyebrow` (глоб. токен `--brass-dim`
  10.5px = 3.88:1, задел бы все смерженные экраны) → задача #49.

**Отложено владельцем** («мердж, перевод на другие языки позже»): полноценная
локализация de/es/fr — задача #48 (сейчас английский фолбэк; на главной это
заменило старые нативные HomePage-переводы, ключи осиротели; решить: свести
middleware к ru/en ИЛИ локализовать всё).

**Процесс:** каждый PR — ветка (рестарт с main после мержа предыдущего, чтобы не
наслаивать на смерженную историю) → зелёный CI → merge. Оба смержены merge-
коммитом (как #169/#170). Ветка вновь перезапущена с `ea8b157` под следующий шаг.

**Дальше:** прайс (блокер — Stripe-аккаунт создаёт владелец, я не создаю
аккаунты/не трогаю платёжные ключи) → /connect → кабинет; либо перестройка
dreams/account на дизайн-систему.

### 2026-07-30 (part 6) — лунный календарь в роут (инструмент, честный отказ)

**Повод:** следующий экран по очереди владельца (натал → астро → **лунный**).

**Сделано** — `calendar` роут пересобран на инструментальную систему:
- `components/LunarInstrument.tsx` (клиент) вместо `LunarWidget` (был на
  framer-motion). Панель дня: номер лунного дня крупным моно, фаза +
  освещённость %, знак Луны, время начала дня, `MoonDisc` (яркость диска =
  освещённость — честно, без вымышленной геометрии терминатора, который я не
  могу отрендерить и проверить; форму полумесяца добавлю отдельно после
  превью). Сетка месяца: день месяца + номер лунного дня в каждой ячейке, клик
  выбирает день, стрелки prev/next месяца. Инлайн-`select` часового пояса
  (НЕ `TimezoneSelector` — он на `useTranslations`/next-intl; инструментальные
  экраны на инлайн-i18n, как натал/астро; тянул только чистые
  `getStoredTimezone`/`setStoredTimezone`). Строка провенанса (движок, JD_UT,
  пояс, источник), дисклеймер с жирным лидом. Билингвально ru/en; фаза,
  описание, рекомендация, знак приходят локализованными с бэкенда.
- **Убрал тихий мок-фолбэк** (conventions §12): `lunar-server.fetchLunarDay`
  больше НЕ возвращает `buildMockLunarDay` при ошибке — бросает. Из-за этого
  ожил мёртвый код: `/api/lunar` отдаёт честный 502, страница показывает
  ошибку (раньше fetchLunarDay глотал ошибку → мок, и оба обработчика ошибок
  были недостижимы). Удалены `LunarWidget.tsx`, `lunar-mock.ts`, их тест и
  стори; добавлены `LunarInstrument` + тест (рендер дня, сетка, aria-current
  «сегодня», загрузка по дням) + стори.
- **First Load JS роута 145→93 КБ** — ушёл framer-motion.

**Проверки:** build зелёный (calendar 5.72 КБ), tsc чисто, jest 24/24
(pwa-manifest/face-gates/lunar-math + новый LunarInstrument).

**Хвост:** ключи `CalendarPage`/`LunarWidget` в `messages/*.json` теперь не
используются — можно подчистить (не срочно). Порядок дальше: **прайс →
/connect → кабинет**.

### 2026-07-30 (part 5) — астрокарта в роут (canvas-эталон, не Leaflet)

**Повод:** на вопрос «где ещё астрокарта?» вскрылось, что она жила только
статической страницей. Владелец выбрал «перенести сейчас», до лунного.

**Ключевое различие, которое чуть не увёл в ложную сторону:** было ДВА файла
астрокарты. `frontend/public/astrocartography.html` (20 КБ) — СТАРЫЙ прототип на
Leaflet со старой сине-фиолетовой палитрой. `astrocartography.html` в КОРНЕ
(109 КБ) — приборный ЭТАЛОН дизайн-системы: не Leaflet, а **canvas с
эквидистантной проекцией и вшитыми береговыми линиями**. Порт делал с эталона
(его и требует скилл: «Match it»), функционал (форма, fetch, города, офлайн) —
из прототипа. НЕ по Leaflet.

**Сделано** `frontend/app/[locale]/astrocartography/page.tsx` (React client):
- canvas-проекция (px/py), графитул, суша из `lib/world-coast.ts` (242
  полигона, 55 КБ, вынуто из эталона; аннотирован `number[][][]`, чтобы tsc не
  выводил гигантский литерал), маркер рождения.
- Линии ACG — `acgLines(core,{latRange,bodies})` из chart-kit; углы/контакты
  под курсором — `angles`/`contacts` из chart-kit. Формулы НЕ дублирую (правило
  chart-kit: дубль формул = клиент рисует карту, которой сервер не выдавал).
- Наведение курсора (rAF-throttle) → панель: 4 угла + планеты на них (орб 8°);
  легенда-переключатели планет; города; форма ввода + fetch (гейт 401/402);
  провенанс; офлайн через `chart-store` (lastChart). Билингвально ru/en.
- Цвета canvas — из токенов через `getComputedStyle(--p-*/--abyss/--land/…)`,
  хардкода hex нет (кроме служебного crosshair rgba).
- **DRY:** демо-карта вынесена в `lib/demo-chart.ts`, натал теперь импортирует
  её (натал-бандл 12.7→7.5 КБ). `public/astrocartography.html` и
  `public/vendor/leaflet/` удалены (Leaflet больше не нужен нигде). `sw.js`
  SHELL почищен (минус astro + leaflet), VERSION v3→v4. **Эталон в корне НЕ
  трогал.**

**Проверки:** `next build` зелёный (astro 26.4 КБ), `tsc` чисто, jest 24/24
(было 27 — pwa-manifest тест data-driven по SHELL, минус 3 записи = минус 3
кейса; это и есть страж согласованности SHELL↔файлы, зелёный).

**Порядок дальше:** лунный календарь → прайс → /connect → кабинет.

### 2026-07-30 (part 4) — chart-kit в сборке Next + натальное колесо в роут + легал-каркасы

**Повод:** владелец перед лунным календарём попросил убрать промежуточную
остановку в `public/`: «подключи chart-kit к сборке Next и перенеси натальное
колесо в роут `/[locale]/natal`. Дальше экраны делаем сразу в роутах. Заодно
создай статические `/legal/privacy|terms|disclaimer` — пустые каркасы с
заголовками, текст пришлю; открываются без авторизации и без языкового
префикса».

**chart-kit подключён к сборке Next** — единственным источником, без
дублирования: `transpilePackages: ['@oneiroscope/chart-kit']` в
`next.config.js` + `"@oneiroscope/chart-kit": "file:../packages/chart-kit"` в
`frontend/package.json`. Пакет — чистый TS (его `exports` указывает на
`src/index.ts`), все импорты относительные, рантайм-зависимостей нет — поэтому
Next его просто транспилирует. `npm install` создал симлинк, `next build`
зелёный: `✓ Compiled successfully`. **Открытый вопрос — build-context Vercel:**
Root Directory там `frontend`, а `../packages` вне него. Локально работает;
эмпирически проверяется на PREVIEW-деплое ветки (production деплоится только
при merge в main, так что проверка не трогает прод). Если preview упадёт на
симлинке — фолбэк: зеркалить `src` в `frontend/lib/chart-kit` с CI-проверкой
дрейфа.

**Натальное колесо стало роутом** `frontend/app/[locale]/natal/page.tsx`
(React client-компонент, порт из `public/natal.html`): та же приборная
эстетика, SVG-колесо из `wheelLayout`, панель, **переключатель систем домов
(Ф-3)** с показом кто меняет дом против Плацидуса. Вся геометрия из
`@oneiroscope/chart-kit` — импорт из пакета, а не из `/vendor/*.js`. Цвет
планет — только `var(--p-*)` (добавил `--p-truenode`/`--p-chiron` в tokens.css,
т.к. были только sun..pluto); хардкода hex нет. Все 5 обязательных правил
данных на месте (градусы+минуты, аспекты орб+applying/separating, пограничные
с ±, tz+смещение, строка провенанса). Фетч реальной карты — типизированный
`lib/chart-store.ts` (порт `chart-store.js`: fetch единственная сетевая дверь,
IndexedDB save/last, `ChartFetchError` с `.status`/`.detail` для нейтрального
отказа 401/402). Экран билингвальный ru/en (прототип был только ru).
`public/natal.html` удалён; из `sw.js` убран `/natal.html` из SHELL и поднята
версия v2→v3 (иначе `cache.addAll` падал бы на отсутствующем URL). SW из роута
НЕ регистрирую — его SHELL заточен под статические прототипы; офлайн-хранение
карты (IndexedDB) работает и без SW.

**Легал-каркасы** `frontend/app/legal/{privacy,terms,disclaimer}/page.tsx` —
ВНЕ `[locale]`, поэтому свой root-layout `app/legal/layout.tsx` с `<html>/
<body>` (корневой `app/layout.tsx` — pass-through, html/body даёт каждая ветка;
так же устроен `[locale]`). Middleware matcher получил исключение `legal`:
`'/((?!_next|api|legal|.*\\..*).*)'` — без intl-редиректа и без префикса.
Собираются как статические (`○`), приборный стиль, заголовок + честная пометка
«черновик, текст готовится». Общий каркас — `components/LegalSkeleton.tsx`.

**Проверки:** `next build` зелёный (natal 12.7 kB, три legal статические);
`tsc --noEmit` чисто; jest 27/27. Nav в Header пока НЕ трогал — `/natal`
достижим прямым URL, но в глобальное меню не добавлен (перестройка меню
astrology→natal — часть последовательного раскатывания экранов, отдельным
шагом).

**Дальше по порядку владельца:** лунный календарь → прайс → /connect → кабинет.

### 2026-07-30 (part 3) — дизайн-система «прибор» + экран 1 (натальное колесо)

**Валидация против Astrodienst (авторы Swiss Ephemeris).** Владелец сверил
эталонную карту 01.07.1977 с astro.com: **все планеты сходятся < 0.5″**
(Нептун 0.32″, Хирон подтверждён в Тельце — «13.55″» были ошибкой
astronomy-engine, не нашей). Углы разошлись на 1.7° по ASC — и причина не в
движке, а в геокодере: astro.com взял координаты Запорожья ~100 км от центра
(47.1522/35.7425), мы — фактический город. По арифметике **прав OneiroScope,
не astro.com**. Это подтверждает тезис продукта: эфемериды у всех одни,
карты расходятся на геокодере и часовом поясе, и показать это — наш эдж.

**Дизайн-система установлена** (`b26d151`): `.claude/skills/design-system/
SKILL.md` (триггерится на любую UI-работу; несёт палитру, три гарнитуры и
НЕНАРУШАЕМЫЕ правила данных — градусы+минуты, аспекты с орбом и applying,
пограничные с флагом, tz+смещение, строка провенанса), `frontend/styles/
tokens.css` (морская палитра abyss/brass/parchment, радиус 0, границы не тени;
уже импортирован в layout.tsx), корневой `astrocartography.html` (эталон
компоновки), `docs/design/design-direction.md`. Старые токены заменены;
переходный мост в конце tokens.css перенаправляет старые Tailwind-имена
(bg-bg/text-ink/gold) на новую палитру, чтобы не сломать ещё не
перевёрстанные экраны.

**Экран 1 — натальное колесо** (`2f87a20`, `frontend/public/natal.html`
перевёрстан): SVG-колесо из `wheelLayout` в приборной эстетике (латунная
градусная шкала, планеты в цветах металлов, хорды аспектов цветом планеты,
пунктир для минорных); панель прибора справа. Все 5 обязательных правил на
экране. **Переключатель систем домов (Ф-3)** — фича, которой нет ни у кого:
Плацидус/Порфирий/По знакам, с показом кто меняет дом против Плацидуса
(☽·♅·♇·⚷). За полярным кругом Плацидус честно резолвится в Порфирий, не
падает. Проверено в Chromium на 1240 и 380px: без ошибок и переполнения.
**Позиция:** «прибор, а не гадание» — стайлинг Co-Star тоже моноширинный,
отличают ДАННЫЕ (Co-Star не печатает ни систему домов, ни орбы, ни tz).

**Порядок экранов дальше:** лунный календарь → прайс → /connect → кабинет.
Каждый по `design-system` скиллу, эталон — корневой astrocartography.html.

### 2026-07-30 — claude/oneiroscope-dream-encoder-rebuild-g2iyp0 — гейт на выдаче `chart_core` (§8 п.7)

**Триггер:** владелец выбрал гейт из двух оставшихся пунктов §8. Формулировка:
«check_entitlement только к выдаче chart_core, оба транспорта; free = одна
карта навсегда; всё производное — не гейтить; отказ нейтральный структурный».
Повод — «оплатить можно, а получить нельзя»: биллинг был написан и подключён к
нулю точек (см. §5).

**Разведка вскрыла три вещи, которых формулировка не учитывала:**
1. **Дверей не две, а три.** `chart_core` чеканят `POST /api/v1/chart`, MCP
   `calculate_natal_chart` И богатый `POST /api/v1/astrology/natal-chart`
   (с тем самым `# TODO: Add auth`). Гейт двух при открытой третьей — ровно тот
   обход, о котором я сам писал владельцу. Закрыл все три.
2. **У MCP нет моста к внутреннему User.** Принципал MCP — внешний OAuth `sub`
   (Auth0/Clerk), кладётся middleware в `scope["state"]["mcp_subject"]` только
   при `MCP_REQUIRE_AUTH`. Внутренняя квота живёт на `User`. Мост:
   `User.oauth_subject` (uniq) + find-or-create → free-tier User по субъекту.
3. **«Одна карта навсегда» булевым флагом нечестна.** Флаг `free_natal_used`
   сжёг бы единственную карту при первой же чистке кэша. Сделал keyed:
   `free_natal_chart_key` = identity карты (миг рождения + координаты, тот же
   ключ, что клиент кладёт в IndexedDB). Пере-выдача СВОЕЙ карты бесплатна
   навсегда; отказывается только ДРУГАЯ вторая.

**Сделано (единый seam, три двери):**
- `backend/services/billing/entitlements.py` — `check_chart_entitlement` +
  `mark_chart_issued` (транспорт-нейтральные, работают на любом User-подобном
  объекте, как `quotas.py`), `EntitlementRequired` (402) и `AccountRequired`
  (401), оба со структурным телом: `error/message/allowance/reset_at/
  tier_required/account_url`. Никакого продающего текста — факт, не «купи».
- `chart_core.chart_identity(core)` — единый источник identity.
- `User.oauth_subject` + `User.free_natal_chart_key`; миграция `0002`.
- `auth.require_account` — optional-bearer → структурный 401 вместо голого 403.
- Гейт на всех трёх дверях: build → identity → check → mark → commit; отказ
  сборки (ValueError) РАНЬШЕ гейта, чтобы неудачный расчёт не жёг квоту.
- MCP: `_principal.mcp_subject()` (читает субъект из contextvar, НИКОГДА не
  падает) + `resolve_connector_user`; `_gate_chart_issuance` штампует
  `entitlement:{gated:…}` — без субъекта на открытом коннекторе честно
  `gated:false`, не молча.
- Фронт: `chart-store.fetchChart` пробрасывает `.status`/`.detail`; natal.html и
  astrocartography.html показывают отказ фактом + ссылкой на кабинет.

**Тесты:** `test_chart_gate.py` (16) — keyed idempotency, tiers, форма отказа,
MCP-ветки (метрирует первую, отказывает вторую, пере-выдаёт свою, штампует
открытый коннектор). Байт-идентичность `chart_core` между транспортами держит
прежний тест. Полный прогон: 571 passed, набор из 41 sandbox-падения идентичен
до/после (0 регрессий).

**Adversarial self-review (workflow, 4 линзы на обход) — что нашло и что сделано:**
- **TOCTOU-гонка на `free_natal_used` (high):** два конкурентных запроса первой
  карты проходят check до mark. Задокументировано как известное ограничение,
  идентичное существующему `quotas.py` («Redis in production»): утечка
  ограничена (пара карт под точной гонкой, не безлимит), правильный фикс —
  `SELECT … FOR UPDATE`, отложен вместе с prod-упрочнением слоя квот. Не шью
  непротестированный concurrency-код.
- **MCP fail-open под required-auth (medium) — ИСПРАВЛЕНО:** теперь три случая
  различаются. Off-transport (stdio/прямой вызов) — не метрируется; on-transport
  без субъекта при `MCP_REQUIRE_AUTH` — **fail closed** (отказ
  `entitlement_unverifiable`, не выдаём бесплатно); открытый коннектор —
  штамп `gated:false`. То же для недоступного стора под auth.
- **LLM до гейта на `/natal-chart` (low) — ИСПРАВЛЕНО:** сначала `interpret=False`
  (дёшево, для identity+гейта), интерпретация только для прошедших гейт; на
  втором проходе переиспользуются координаты, чтобы не геокодить дважды.
- **`quotas.mark_used` пишет флаг без ключа (low):** нет прод-вызовов;
  задокументировано, что этот путь обязан писать и ключ, если будет подключён.
- **Ungated серверная астрокартография (known-scope):** уже в §5.

**Следствие для продукта (флаг владельцу):** гейт требует аккаунт — веб-двери
из анонимных стали sign-in-required. Это влечёт «одна карта навсегда»: обещание
про аккаунт держать не на чем без аккаунта. Прототип-страницы теперь показывают
структурный отказ (демо-карта оффлайн работает); полноценный логин — в Next
(§8 п.6).

### 2026-07-28/29 — claude/oneiroscope-dream-encoder-rebuild-g2iyp0 — тонкое ядро `chart_core` + `packages/chart-kit` + PWA

**Триггер:** задание владельца «Тонкое ядро и три поверхности доставки»
(§1–§9 от 28.07, вечер). Повод — рабочий прототип астрокартографии, который
считал ВСЮ геометрию в браузере из ~600 байт. Значит, эфемериды нужны один
раз на карту, а всё производное — бесплатно и офлайн. Стратегия, зафиксированная
владельцем: web+PWA первым, MCP вторым, **нативные iOS/Android в v1 не делать**
(комиссия 15–30%, ревью, две лишние кодовые базы).

**Сделано:**
- **`backend/services/astrology/chart_core.py`** — единый билдер, спина
  продукта. Закрыты три пробела задания: `ecl_lat` у каждого тела,
  `node_type: "true"` явно (true/mean двигает узел до ~1.8° — дом меняется,
  а по числу не отличить), `utc_offset_used` как `+HH:MM`. Бюджет 2048 Б,
  факт 1702. Южный узел намеренно НЕ шлётся — это северный + 180°.
- **Два транспорта:** MCP `calculate_natal_chart` и новый `POST /api/v1/chart`.
  Идентичность доказана **по построению**, не выборкой: MCP сверяется с общим
  билдером байт в байт, AST-тест закрепляет, что HTTP-обработчик делегирует
  ему и не импортирует swisseph сам. Выборочная проверка прошла бы, а пути
  всё равно расходились бы на другом входе.
- **`packages/chart-kit`** (TS, без фреймворка): `angles`, `houseCusps`/
  `houses`, `aspects` (applying по реальным скоростям), `dignities`,
  `acgLines`, `contacts`. Golden-набор 20 карт (широты за обоими полярными
  кругами, эпохи 1815–2350, полночь, антимеридиан), порог 0.01°, факт 0.14″.
  CI **перегенерирует** фикстуру с живого бэкенда — дрейф сервера не спрячется
  за устаревшим файлом.
- **PWA:** manifest + service worker + IndexedDB; прототип переведён на
  chart-kit и живой API. Проверено в headless Chromium: офлайн после
  перезагрузки восстанавливает карту, рисует 44 линии.

**Три дефекта, которые нашли живые пробы (не ревью, не тесты):**
1. **Рождение за полярным кругом роняло карту целиком.** Плацидус там не
   определён, swisseph отказывает, WP-2 заменил тихую подмену на raise.
   Верное решение — подставить Порфирий (сохраняет куспид 1 = Asc, 10 = MC)
   и **объявить** подмену.
2. **Формула Асцендента давала Десцендент на 7.9% Земли.** Свип 1068 точек:
   84 переворота ровно на 180°, все полярнее ~66°. Коррекция квадранта чинит
   все; остаток 0.96″. Та же ошибка жила в прототипе.
3. **Офлайн-обещание было невыполнимо:** Leaflet с CDN — кросс-доменный
   ответ непрозрачен и не кэшируется. Вендорен в `/vendor/leaflet/`.

**Ревью-раунд (Qodo, 8 находок; коммит `8101eb2`):** семь настоящих.
Главная — **релокация наследовала систему домов места рождения**:
`houseCusps` по умолчанию брал `core.house_system`, который сервер разрешил
для координат РОЖДЕНИЯ. Карта из Тромсё оставалась на полярном Порфирии в
Лондоне, а лондонская падала в Тромсё. Релокация — вся суть карты, так что
ошибка была в обе стороны. Починено полем `requested_house_system` (едет
только при подмене) + `resolveSystemFor(core, lat, lon)` на клиенте.
Попутно: ядро больше не объявляет koch/regiomontanus/campanus (сервер их
умеет, chart-kit — нет; `chart_core` обещает клиентскую отрисовку);
`place_label` ограничен 96 байтами; иконки PWA существуют; CI пересобирает
браузерный бандл и падает на устаревшем (он и был устаревшим).

**§8 п.5 — натальное колесо и лунный день (`765eba2`, CI зелёный):**
- **Лунный день считается на клиенте ТОЧНО, а не приближённо.**
  `lunar/engine.py` выводит его чисто из элонгации Луны от Солнца, обе
  долготы уже в ядре → `chart-kit/src/lunar.ts` повторяет ту же
  арифметику. Golden-фикстура генерируется импортом собственных
  `SYNODIC_MONTH` / `_phase_key` / `_moon_sign` сервера: вторая копия
  формулы в генераторе дрейфовала бы вместе с китом вместо того, чтобы
  ловить дрейф.
- **Освещённости в ките нет намеренно.** Сервер берёт её из
  `swe.pheno_ut`; из двух долгот выводится только `(1−cos)/2`, которую
  WP-16 убрал за ошибку до ~4 п.п. Поле называется
  `illuminationKnown: false` — отсутствие объявлено, а не замолчано.
- **Колесо разделено на чистую раскладку и SVG-строку** — ради
  тестируемости: «куспид 1 смотрит на Асцендент» и «глифы не ближе
  минимального зазора» проверяемы как числа, а картинка — нет.
- **Два бага нашли тесты, а не глаз:** (1) `pointAt` крутил колесо по
  часовой — все долготы, куспиды и аспекты верны, а карта зеркальная,
  MC внизу; (2) разведение глифов было одним жадным проходом, и
  расширенный кластер наезжал на соседа, стоявшего свободно до
  расширения.
- Карта без времени рождения колеса не получает (принят полдень → углы
  произвольны); лунный день при этом работает, ему углы не нужны.
- `frontend/public/natal.html` + вынесенный `/vendor/chart-store.js`
  (две инлайн-копии IndexedDB в двух страницах — ровно тот способ,
  которым они бы разошлись). Проверено в Chromium: SVG рисуется,
  релокация на Шпицберген подставляет Порфирий с объяснением, ошибок
  консоли нет, переполнения нет на 390px и 1200px.

**Урок для будущих сессий (метод, не факт):** первая реализация границы
Плацидуса проверяла сходимость каждого куспида. Бинарный поиск по
`swe.houses_ex` показал, что сервер отказывает **по широте** — ровно
`90 − наклон эклиптики` — независимо от звёздного времени. Покуспидная
проверка объявила бы часть полярных карт «определёнными» там, где сервер
подставляет: тихое расхождение клиента и сервера, ровно то, против чего
существует golden-набор. **Границу чужой библиотеки измеряют, а не выводят.**

### 2026-07-28 — claude/oneiroscope-dream-encoder-rebuild-g2iyp0 — пакет WP-1…WP-18: эфемериды, дома, аспекты, HVdC на живом тексте, поверхность 47→19

**Триггер:** консолидированный план владельца от 28.07 (аудит 46 инструментов
+ два живых прогона), порядок исполнения предписан: WP-6 → WP-7 → WP-1 →
WP-2/3 → WP-4/5 → WP-8 → WP-10/11 → остальное. Полный отчёт по каждому WP:
`docs/reports/WP_FIXES_2026-07-28.md`.

**Сделано (7 коммитов на ветке, рестартованной от main/08c7ca8):**
- **WP-6** (18d8fe4): `with_meta` — блок `meta{server_version, commit,
  schema_version, request_id, input_hash, duration_ms, cache_hit,
  computed_at}` в каждом ответе каждого инструмента; AST-страж обёртки.
- **WP-7** (71c9264): AST-страж тихой деградации по расчётным модулям
  (except-pass / swallow-return-None) c ALLOWLIST с обоснованиями; живое
  нарушение в lunar убрано.
- **WP-1** (c9e5759): `.se1` в репо (sepl/semo/seas_18, DE431), новый
  `backend/core/ephemeris.py` — верификация файлов при импорте (нет файлов →
  падение старта), SWIEPH единственный режим, 9 модулей переведены с
  FLG_MOSEPH, все фолбэк-лестницы удалены, проверка возвращённых флагов
  calc_ut, provenance от `swe.version`. Таблица против skyfield+DE421: SWIEPH
  worst 0.17″ (бар 2″). Хирон стал настоящим (был кеплеровским мусором).
  **Важно:** «Neptune 13.55″ ⇒ Moshier» из аудита — ошибка референса
  (astronomy-engine, усечённый VSOP87: сам даёт 9–12″ на Сатурне/Нептуне).
- **WP-2/3** (b39f743): `assign_planets_to_houses` существовал, но НИКЕМ не
  вызывался → дома пустые в natal chart. Теперь двунаправленная связь +
  `cusp_degree` + `house_borderline`/`distance_to_cusp_deg` (<1°); тихий
  фолбэк Placidus→WholeSign удалён (raise). Аспекты: `_is_applying` был
  эвристикой с «return True for simplicity» (20/20 applying в аудите) —
  теперь по скоростям обоих тел; поля `orb_deg`, `speed_diff_deg_per_day`,
  `speed_deg_per_day`. Контрольная карта 01.07.1977 22:30 Запорожье: все 10
  домов совпали с эталоном владельца; аспекты 5 applying / 15 separating.
- **WP-4/5** (f3209f8): субстантивированные прилагательные — курируемый
  список лемм + род из морфологии формы (у «знакомый»/«дежурный» в
  OpenCorpora вообще нет NOUN-разбора!); атрибутивный гейт («старший
  знакомый» = один персонаж); GF без глагола находки (ценность + «лежат/
  вижу/оказывается»), гейты отрицания/кладбища; кодировщик 3.1.0.
  min_events_required: A/F из 1+1 → insufficient_data (2 < 3);
  typicality_warning. Приёмка на дословных фрагментах аудита; калибровка
  GF ×1.8–2.1 держится.
- **WP-8/10/11** (6d5b948): surgery-событие и медицинское сообщение удалены;
  поверхность MCP 47 → **19** (physiognomy/отчёты/generate_horoscope/
  synastry/decade и пр. сняты; 15 lookup-инструментов → один `lookup` с 14
  темами); план стадий 26 → 15 с двусторонними стражами (страж поймал
  необъявленные acg lines/point — добавлены стадии); меню
  `can_also_compute`: ~90k символов → `{"next": [≤3], "full_plan_tool"}`
  ≤200 символов (тест-бюджет).
- **WP-12/15/16/18** (1ece7f9): контракт-тесты lookup (док ↔ диспетчер в обе
  стороны); `scopes_supported` публикуется всегда (openid profile email по
  умолчанию); освещённость через `swe_pheno_ut` (03.08.2026 10:00 UTC →
  77.85%, было 74.08%); квинконс в KB аспектов; +6 символов снов (золото/
  клад/земля/тайник/карманы/наставник) и наставник в male-лексикон; ретро-
  списки гороскопа и forecast синхронизированы; `orb_policy_deg` в ответе
  natal; соляр до секунды (<0.01 arcmin).
- **WP-14**: `.github/workflows/keepalive.yml` — пинг /health каждые 10 мин
  (06–23 UTC) + прод-проверка `engine == SWIEPH` на каждом пинге.
- **WP-13** отложен письменно (аддитивная миграция после подтверждения
  таксономии тиров), **WP-17** — сторона владельца (кит готов),
  compare_dreamy — ждёт среду с доступом к HF.

**Среда:** 40 локальных падений тестов — драйф песочницы (нет
claude_agent_sdk/python-jose, starlette), воспроизведены A/B на дереве до
изменений; авторитетен CI.

### 2026-07-27 (part 6) — claude/oneiroscope-dream-encoder-rebuild-g2iyp0 — слой снов пересобран: структурный HVdC-кодировщик

**Триггер:** живой прогон `analyze_dream` (dream_ca95070c3764) — сон с находкой
монет, передачей фигурок женщине и оттеснением наблюдателя дал
`aggressive=0, friendly=0, good_fortunes=0`, ложные stairs/forest, «A/F=0.00 vs
норма 0.59, significant» из 0/0, и серверную прозу, опровергающую свой же
список символов. Детерминированный слой, который считает неверно, — это
разрушенное позиционирование продукта.

**Сделано (полный отчёт: `docs/reports/DREAM_ENCODER_REBUILD_2026-07-27.md`):**
- **`hvdc_coder.py` + `hvdc_lexicon.json` (v3.0.0)** — кодирование событий, не
  слов: клаузы, персонажи-существительные с полом (местоимения не создают
  персонажей), акты с обязательной целью, GF≠success (усилие перекодирует,
  лотерея ≠ победа в игре), отрицание со скоупом («не смог»→failure, «никого
  не ударил»→ничего), инцидент-дедуп, evidence-клауза + цитата правила на
  каждый счётчик. Всё детерминизм 1.0, ноль LLM.
- **Нормы:** 0/0 → `insufficient_data` с причиной (никогда 0.00);
  `deviation_unit` (pp|ratio), хак `/5` удалён; typicality по значимости.
- **Символы:** позиционные совпадения против клаузной карты — отрицание,
  «не было X», отвергнутая локация («копать не там») гасят; stairs потерял
  глаголы движения; money+монеты/coins.
- **MCP data-first:** `include_interpretation=False` по умолчанию (политика
  #161), `how_to_read`, disclaimer во всех 5 dreams-инструментах; мёртвый
  `physiological_correlations` снят с MCP-пути.
- **lunar_context починен:** импорт бил в несуществующий
  `lunar_service` → всегда null; теперь `LunarEngine`, заполняется от даты.
- **Golden-набор:** 28 снов RU+EN с ручной разметкой
  (`backend/tests/dreams/golden/`), `test_hvdc_golden.py` печатает P/R и валит
  CI ниже порогов. Замер: **precision 1.00 по всем 10 категориям**, recall
  0.70–1.00 (недоборы = 3 задокументированные зоны: модальная неспособность,
  жестовые глаголы, род из местоимений). Символы: 27/27, ложных 0.
- **Личная серия (Domhoff):** `dream_entries` (признаки без текстов, первая
  Alembic-миграция), `dream_series_stats` (MCP + стадия плана), порог N≥15
  явный, GDPR-экспорт/удаление, тесты на SQLite (модель на диалект-agnostic
  Uuid именно ради этого).
- **DReAMy:** настоящая библиотека установлена (вендоренный `external/DReAMy`
  — 48-строчная заглушка!), `scripts/compare_dreamy.py` готов, но сетевая
  политика окружения отвечает 403 на huggingface.co → числовой замер отложен;
  coverage-таблица в отчёте: DReAMy не кодирует A/F/striving/fortune и не
  кодирует по-русски ничего кроме эмоций — наш кодировщик остаётся слоем
  экстракции, кандидат на заимствование только эмоциональная ось (XLM-R).

**Уроки:**
- Словарём HVdC не берётся принципиально — разметка отношений, не слов.
  Керневая ошибка v1 была архитектурной, не в полноте словаря.
- Golden-набор окупился в первый же прогон: 6 реальных багов кодировщика
  (стем «жених»==«жен» перехватывал «жену» через setdefault-порядок;
  дедуп персонажей убивал цель у поздних упоминаний; насекомое "fly" ловило
  глагол fly; "finally" из соседнего предложения перекодировал находку;
  "old man"+"man" двоил персонажа; форма «прохожая» дала бы прохожему женский
  пол — снята из лексикона).
- Precision-first: каждый порог recall в CI — задокументированный недобор,
  а не обещание; поднять recall ценой precision тест не даст.

**Не сделано намеренно:** сонники (magickum), расширение словаря как фикс
кодирования, новые серверные LLM-хопы. DreamBank-корпус с Dryad не загружен
(сеть); harness примет его тем же micro-P/R путём.

**Правки по ревью владельца (раунд 2, та же сессия):**
- ⚠️ **Поправка к подаче метрик:** «precision 1.00» — это ВНУТРЕННЯЯ
  согласованность (разметку и кодировщик делал один автор), не внешняя
  точность; при n=28 ДИ широкий. Внешняя проверка — слепая вторая разметка
  владельцем + каппа Коэна: кит готов (`blind_annotation_template.json` без
  утечки разметки + `scripts/kappa_golden.py`, взвешенная каппа + список
  расхождений). Отчёт §2 и докстринг теста переподаны в этой рамке.
- ⚠️ **Поправка по DReAMy:** пункт помечен НЕ выполненным (критерий 8 → ❌).
  Формулировка «наш кодировщик остаётся слоем экстракции» была подана как
  результат, будучи доводом из таблицы покрытия — переписана как гипотеза
  до прогона `compare_dreamy.py` в окружении с HF-доступом.
- **Расследование заглушек (вопрос владельца «кто импортировал и что
  получал»):** стабов ДВА — `external/DReAMy` (хэш-«эмбеддинги») и
  `external/pyswisseph` (39 строк аппроксимации под именем Swiss
  Ephemeris!). Потребитель один: `etl/pipeline.py` (ежедневный cron
  `dreams-etl.yml`, права push) — принудительно sys.path'ом берёт ОБА стаба
  и пишет `dreams_enriched.parquet` с мусорными эмбеддингами и луной из
  аппроксимации; **выход никем не читается** → вред нулевой, но воркфлоу
  молотит вхолостую, а `build.yml` тестирует на фальшивой астрономии
  (вероятная причина его pre-existing red). Прод не задет (Render ставит
  настоящий pyswisseph из backend/requirements). DReAMy-стаб снят с
  прод-пути (`backend/requirements.txt`); чистка `external/` + корневого/etl
  requirements + судьба ETL — отдельный P1 (файлы CI/ETL вне этой ветки).
- **conventions.md §12 — молчаливые фолбэки на путях данных запрещены**
  (прецеденты задокументированы). Код приведён: `degraded: list[str]` в
  ответе (упавшая подвычисление оставляет запись, null больше не двусмыслен),
  прямой импорт LunarEngine без try/except, RuntimeError вместо пустого KB
  и вместо захардкоженных «дефолтных норм».
- **pymorphy3 — жёсткая зависимость** вместо префиксных заплаток: лемма +
  грамматика для персонажей (жена/жених, отца→отец, детьми→ребёнок),
  animacy-гейт для агентивных суффиксов (граница/постель/лисица отсечены),
  **родительный отрицания** («Водителя не было видно» — персонаж
  отсутствует; «Мама не была рада» — присутствует). Golden-метрики
  бит-в-бит, +3 теста.
- **method_note в norm_comparison**: precision-first недосчитывает против
  людей-кодировщиков норм 1966 → «ниже нормы» может быть артефактом;
  индексы сравнимы между пользователями одной версии кодировщика.
  Калибровка — после каппы/внешнего корпуса.

**Раунд 3 (вопрос владельца «как скачать базу снов») — скачана и прогнана:**
- Dryad/HF/dreambank.net закрыты политикой, но raw.githubusercontent открыт →
  JSON-зеркало DreamBank (mattbierner/DreamScrape, ~30k снов). Скачаны
  НАСТОЯЩИЕ нормативные корпуса 1966 года: norms-m (491) + norms-f (490).
  `scripts/fetch_dreambank.py` (в gitignored data/dreambank/) +
  `scripts/validate_against_norms.py`.
- **Первая внешняя калибровка** (отчёт §7.5): взаимодействия ~×0.5 от
  человеческого уровня (прогноз ревью подтверждён), sexuality ×0.36–0.41,
  misfortune ×0.6. Замер сам нашёл и починил три дефекта:
  (1) эмоции 45/29→83.7/78.9 vs 80/80 — счётчики перешли на by_type-словари
  (прилагательные afraid/scared, не существительные fear/anxiety);
  (2) good_fortune ×3.9→×1.7–2.0 — гейты «found myself/found that/нашёл
  его.»; (3) male_percent 47 vs 67 — асимметрия лексикона/местоимений,
  направление задано числом.
- ⚠️ KB-находка: `hvdc_norms.json` пишет «A/F ratio = 0.59», но по её же
  rate'ам (0.47/0.38) это A/(A+F)=0.55, а A/F=1.24 — формула и значение
  противоречат друг другу; адъюдикация по Domhoff.
- Урок: **петля «внешние данные → замер → фикс → перемер» за один заход дала
  больше, чем неделя полировки по внутренним тестам.** Golden не поймал ни
  идиому «found myself», ни словарную асимметрию эмоций — их поймал корпус.

### 2026-07-27 — claude/identity-direction-question-vrognh — geocoder "City, Country" bug + node definition aligned

**Trigger:** a long client session (strategic reading for a real person, birth
1977-07-01 Zaporizhzhia). The connector went live mid-session, so the chart was
cross-checked through the deployed MCP against the same chart computed by
importing `pattern_engine` directly. Planets and the six tight aspects agreed to
0.01°, all twelve cusp signs agreed — but the coordinates did not.

**The bug (found via `validate_birth_data`).** `birth_place="Запорожье, Украина"`
returned `valid: true, issues: []` and coordinates **47.33333 / 36.26667** — a
hamlet literally named «Україна», ~100 km from the city (47.85 / 35.12). The
same query *without* the country suffix resolved correctly, which isolated it:
the whole string went into GeoNames' free-text `q` instead of splitting the
country into the `country` parameter. Effect on the chart: **ASC +2.43°,
MC +1.08°, and the Moon flipped from house 12 to house 11** — all reported as a
successful validation. A silent wrong answer with a confident success flag is
worse than an error.

Three defects grew from that one root, all fixed in `geonames_resolver.py`:
1. the country suffix polluted `q` → `split_place_query()` + `country=` ISO-2
   (unrecognised tails like "Frankfurt am Main, Hessen" are deliberately left
   in the query rather than guessed at);
2. `geonames_lookup` fetched 10 candidates "to choose best match" and then took
   `candidates[0]` — it never chose. GeoNames orders by relevance, not
   importance, so a hamlet outranked a city of 700k. Now `pick_best()`:
   name-matching candidates first, then population, plus `orderby=population`;
3. the fallback city database was keyed on the full string, so
   "Запорожье, Украина" missed the "запорожье" entry too.

**Silence is the real defect, so it is now impossible:** `name_matches()`
(diacritic- and transliteration-tolerant, `unicodedata` folding + `difflib`
ratio ≥0.62) flags `name_matched=False` when nothing resembles the request; it
propagates through `GeoLocation` → `search_city().warning` →
`validate_birth_data().warnings`. Kept a **warning, not an issue**, so a
legitimate transliteration miss can never block a chart.

**Node aligned.** `astrology/ephemeris.py` always used the TRUE node (body 11);
`strategic/pattern_engine.py` used the MEAN node — 200.828° vs 200.257° on the
same chart, enough to change a house and to make `calculate_natal_chart` and
`money_contour` disagree about one person. `pattern_engine` now uses
`swe.TRUE_NODE` under the key `north_node` (matching `Planet.NORTH_NODE`).
Verified on the live chart: node moved 0.57° and stayed in house 8, so the
linchpin / dignity / angular readings are unchanged.

**Tests:** `test_geocoder_query_split.py` (19 cases incl. the exact regression —
mocked payload with the hamlet first and the city second) and
`test_node_definition_consistency.py`. Regression check done properly: failure
signatures captured before and after via `git stash` — **28 both ways, zero new
failures**. The 28 are pre-existing missing-dependency errors in this sandbox
(`claude-agent-sdk`, `cryptography`), not code faults.

**Found, not fixed (reported, see §5):** the fallback city database holds **55**
entries while the docstring and CLAUDE.md both claim "90+"; it has no Plzeň, no
Cyrillic "прага", and none of the Spanish cities. So `search_city("Плзень,
Чехия")` honestly returns `PLACE_NOT_FOUND` without an API key. Also its
Zaporizhzhia longitude (35.1969) differs ~6 km from GeoNames' 35.11714, so the
fallback and API paths give slightly different charts for the same city.

**Lesson.** MOSEPH vs SWIEPH was the thing we set out to worry about, and it was
the *least* consequential item by three orders of magnitude: <1″ (<0.0003°)
against a 1–2.4° geocoding error and ~1.2° per 5 minutes of birth-time
uncertainty. Uploading `.se1` would have fixed nothing that mattered. The
cross-check found the real defect only because two independent code paths were
compared against each other instead of one being trusted.

**Part 2 — the geocoder gets smaller, not bigger.** Owner's question: if the
service is reached through a chat, doesn't the chat already know the
coordinates? Largely yes, and it reframed the work. The chat reads any script
natively (北京, القاهرة — where our Cyrillic-only `transliterate_russian()` does
literally nothing) and it can ask the user *which* Barcelona. So geocoding a
place the caller already resolved only adds a chance of picking the wrong one.
Most tools already take lat/lon (`money_contour`, `vocation_map`, `decade_map`);
only the chart entry points took a string. Two things do **not** move to the
caller, though: the timezone, because an hour of zone error moves the MC ~15°
against ~1° per degree of longitude — historical offsets stay in tzdata; and
provenance, because a coordinate from a model is 0.7 synthesis wearing a 1.0
costume, with no `geonameId` to audit.

Shipped instead of the planned per-request `lang` detection (which the chat makes
unnecessary):
- **`calculate_natal_chart` accepts `latitude`/`longitude`** (+ optional
  `timezone_name`), validated as a pair with range checks, and skips geocoding
  entirely. Zone is derived from the coordinates via tzdata unless explicitly
  overridden. Proven by a test whose geocoder raises on any call.
- **`search_city` returns `candidates` + `ambiguous`.** `geonames_lookup` always
  fetched `maxRows=10` and discarded nine — the pool is now surfaced at zero
  extra API cost, with `is_ambiguous()` set when ≥2 name-matching candidates sit
  in different countries or admin areas. Barcelona ES/VE is the test case.
  Ambiguity is a warning, never an issue: it must not block a chart, but it must
  never be silent either.
- Same "City, Country" split applied to `geonames_search_cities`; its rows gained
  population + feature code so a human can actually choose.
- Corrected the **"90-city fallback"** claim in `CLAUDE.md`, `backend/mcp/README.md`
  and two docstrings — the list holds 55 entries. False documented numbers are
  cheap to fix and expensive to trust.

**Second lesson, from my own test double.** `_FakeResponse` lacked `status_code`,
which the resolver logs on the primary path. The primary call therefore raised
`AttributeError`, fell into the transliteration retry (which happens not to log
`status_code`), and the tests passed on correct values via the *wrong code path*.
Caught only because a new test asserted the call count. A test double that omits
an attribute the code touches doesn't fail — it quietly tests something else.

**Part 3 — every tool response now advertises the rest of the surface.** The
owner's ask, after comparing our natal output against a plain ChatGPT reading:
make any tool call surface the full list of what else is computable, with
astrology + physiognomy together and dreams separate. The diagnosis behind it is
real — the server registers 46 tools and a chat that lands on one sees only that
one. `analysis_plan` has answered "what can be computed, in what order" from the
start, but nothing surfaced it unless the model thought to ask, and it usually
did not. So the answer travels with the data: `can_also_compute` on every
substantive response.

- `analysis_plan.py`: `Stage` gained `domain`; 11 stages added for tools that
  had none (transit-arc, event-forecast, compare-cities, cities-by-theme,
  solar-return-where, lunar-period, face-single, face-timeline, and the three
  report writers) → **26 stages covering 26 tools**. New `capability_menu()`
  returns `ready` / `needs_input` / `questions_to_ask` / `reference_lookups`.
- `mcp/tools/_menu.py`: `with_menu()` — one line at the end of 25 tools. Returns
  non-dicts untouched (a bare list shape is a contract; wrapping it to carry a
  hint would break callers — which is why `get_lunar_period` has no menu) and
  never double-attaches.

**Offered, not run** — the owner's "или всегда запускай" was the other option and
it is the wrong one: a decade map scans ten years at a 10-day step, a city scan
runs a whole pool, and a Solar Return suggestion computes one return per
candidate. Firing that on every call spends minutes and quota answering a
question nobody asked, and each of those tools needs an input (`cities`,
`target_date`) that a chart call does not carry. The menu instead lists only
steps whose inputs are *already* satisfied, so the next call is one step away.

**Domains** follow the owner's split exactly: `astro` = chart **and** face (both
read one standing person from static data), `dreams` = per-episode, no shared
inputs. Verified: the dreams menu offers `analyze_dream` + 3 dictionaries and
nothing chart-shaped; the astro menu never offers `analyze_dream`.

**Size is a feature here.** First cut was 4569 chars on *every* astro response —
more than the payload of a light tool like `get_lunar_day`. Blocked entries were
carrying the full "what it answers" prose, which is dead weight until the step
can actually run. Trimmed to `{name, tool, missing}` → 3452 chars (−24%), with
`test_menu_stays_within_a_size_budget` pinning the ceiling at 4500 so a future
stage can't silently balloon every response. `analysis_plan` still returns the
full text on demand — that is the division of labour.

**Tests:** `test_capability_menu.py`, 27 cases. Beyond behaviour, five AST-level
drift guards: every stage tool attaches a menu, each marks its own stage
completed, menu domain matches stage domain, completed ids are real stages,
reference lookups stay menu-free. All five were **mutation-tested** — menu
removed, stage id swapped, domain flipped — and each failure was caught by the
intended guard. Full suite 414 passed vs 389 on `origin/main`, failure
signatures byte-identical (47 both ways, all pre-existing sandbox dependency
gaps).

**Lesson, and it is the same one twice.** Earlier in this branch I wired the
physiognomy menus with a regex and gave three tools each other's stage ids.
Every runtime test still passed — the menus were *present*, just describing the
wrong step. Only a structural check catches that class of error, so the drift
guards exist and are mutation-tested rather than assumed. A test that has never
been shown to fail is a comment.

**Part 5 — two OAuth discovery defects, found by pointing Inspector at prod.**
Owner ran MCP Inspector against the live deployment. Two things in one place,
both capable of stopping a strict client *before any login window*, which from
the outside is indistinguishable from "the connector doesn't connect":

1. **The published issuer was normalised.** `protected_resource_metadata()` sent
   `MCP_AUTH_ISSUER.rstrip("/")`. The subtlety is that `rstrip("/")` appears
   three times in `remote.py` and is *right* twice — at `jwks_url()` it precedes
   a well-known path, and at token validation it is applied to both sides, which
   is precisely what keeps a real Auth0 token from being rejected over a slash.
   The third is different in kind: an issuer **identifier** handed to a client,
   which per RFC 8414 §3.3 builds the metadata URL from it and then requires the
   `issuer` the AS returns to be identical to what it started with. Auth0 emits
   the slash; we stripped it; a strict client is entitled to abort. Now verbatim.
2. **Metadata was served only on the bare well-known path.** RFC 9728 §3.1
   builds the URL by inserting `/.well-known/oauth-protected-resource` *between*
   the host and the **path** of the resource identifier — so a resource at
   `https://host/mcp` is described at `.../oauth-protected-resource/mcp`. The
   bare path is correct only for a resource with no path. Both are served now,
   canonical first, and `WWW-Authenticate` advertises the canonical one.

**Why this hid so well.** Claude connects fine — 46 tools, `MCP_REQUIRE_AUTH`
true throughout — because it follows the `WWW-Authenticate` header literally and
lands on the path we happened to serve. So the working client proved the wrong
thing: it validated the header path, never the RFC-constructed one, and never
compared issuer strings. Two independent conformance gaps, invisible to the one
client we tested with. Token validation deliberately untouched.

**Correction I had to make to my own reporting.** I told the owner "416 passed
vs 389 on main, 47 both ways" for part 4. Those numbers were taken after I had
`pip install`-ed `mcp[cli]` mid-session for a registry check, which flipped
three unrelated import tests from fail to pass — measured against a baseline
from before the install. Re-measured with `origin/main` checked out in the same
directory and interpreter: 392 → 424, 44 failures both ways. The conclusion was
unaffected, but the numbers were an artifact of my environment, and this is the
second time in two sessions that a "baseline" of mine drifted (the first was the
`_PROJECT_ROOT` worktree artifact). **A baseline is only a baseline if the only
thing that changed is the code** — same directory, same interpreter, same
installed packages, measured back to back.

### 2026-07-27 (part 2) — claude/fandorin-portrait-generation-d422my — connector LIVE with OAuth; data-first pivot

**The connector works.** First real natal chart computed through Claude →
Auth0 → Render → Swiss Ephemeris. 46 tools listed. `MCP_REQUIRE_AUTH` was true
the entire time — the owner chose the route with no open window, and there
never was one.

**Auth0 bring-up, five gates in order** (each produced a different error, and
each error named none of the others). Recorded because the next person will hit
them in the same sequence:
1. `Oops` → **third-party API access**: DCR clients are third-party, and a
   custom API denies them by default. Fix: API → Settings → *Default
   Permissions for Third-Party Applications* → **Authorized for User-Delegated
   Access** (dashboard, no token).
2. `no connections enabled for the client` → **domain-level connection**. No
   dashboard toggle; Management API `PATCH /connections/<id>
   {"is_domain_connection": true}`. Required for a multi-user connector: every
   user's DCR makes a *new* client, so per-app enabling cannot scale.
3. `mcp_registration_failed` → **the 10-application tenant limit**. Each failed
   attempt left a `tpc_` client behind; seven of them filled the quota and DCR
   started failing outright. Deleting them fixed it — no manual Client ID
   needed after all. (My "Auth0 issues a confidential client, Claude wants a
   public one" hypothesis was plausible and *wrong*; the audit log's HTTP 201
   should have pointed at quota sooner.)
4. `Authorization with the MCP server failed` after a *successful* login →
   **our bug**, see below.
5. Broken interpretation text → **our bug**, see below.

**Bug: issuer trailing slash (#160).** `verify_bearer` passed
`issuer=MCP_AUTH_ISSUER.rstrip("/")` to jose, which exact-string-compares
against `iss`. Auth0 emits `iss` *with* the slash and the docs tell operators to
configure it with one, so stripping only our side rejected every real token —
unfixable by configuration. Now compared slash-normalised on both sides, with
rejection reasons logged (previously a rejection was invisible server-side).

**ADR-worthy: data-first tools (#161).** Owner asked the right question —
*"зачем в первом выводе ИИ, если всё работает через чат?"* `calculate_natal_chart`
was calling a server-side LLM, a leftover from the web-app era. In an MCP-first
product the client is already a frontier model, so that hop is redundant, costs
the operator money, uses a weaker model, and is a failure point — which is
exactly how it failed live (no provider key → broken template). The tool is now
data-first by default (`include_interpretation=False`), matching the strategic
pattern tools; server-side prose stays opt-in for the parked web frontend. The
confidence ladder is unchanged, it just runs where the model already is.

**Also fixed (#161):** the fallback template spliced English keywords into
Russian and rendered aspects as the *first character* of the planet name
("- С opposition Л"); and `RateLimitMiddleware` keyed on `request.client.host`,
which behind Render's proxy is the proxy — every user shared one 100/min
bucket. Now keyed on the rightmost `X-Forwarded-For` entry (spoof-resistant;
the leftmost is client-controlled).

**Method note.** The self-check endpoint earned itself: at each gate the owner
pasted `/connect/diagnostics` and it said which env var was wrong. A browser
agent cannot read logs or run curl — a URL that reports on the server is worth
more than a runbook paragraph.

**Still open:** `/mcp` is outside the rate limiter (the dispatcher bypasses
middleware so SSE survives); auth bounds it now, but per-subject limiting on
`mcp_subject` is the right next step. Auth0 tenant is Development-tier
(lower quotas) and its name is the autogenerated `dev-u22itgv3h8ew1sgz`, which
users see on the login page. Ephemeris runs MOSEPH (no `.se1` files on Render);
<1″ for 1900–2100 so not urgent.


### 2026-07-27 — claude/fandorin-portrait-generation-d422my — the connector was never reachable; account page

**Trigger:** owner added the deployed backend as a custom connector in Claude
and got *"Couldn't register with OneiroScope's sign-in service"*. Reproducing
the client handshake locally against the real transport found that the visible
OAuth error was the least of it.

**Three independent blockers (merged #158), each fatal alone:**

1. **The endpoint was at `/mcp/mcp`.** FastMCP serves the transport at `/mcp`
   *inside its own app*, which we mounted at `MCP_PATH`. The URL in the connect
   dialog had been 404ing since #155.
2. **The server→client SSE channel delivered nothing.** Mounted behind the app
   middleware, GZip withholds output while deciding whether to compress and
   BaseHTTPMiddleware re-frames the response. Measured over a real socket:
   **0 response bytes in 6 s** mounted vs headers immediately when dispatched
   above the stack. `MCPPathDispatcher` now routes `MCP_PATH` straight to the
   transport, which also removes the `307 → /mcp/` (whose `Location` comes back
   `http://` behind a proxy that isn't trusted for forwarded headers).
3. **`421 Invalid Host header`.** The transport's DNS-rebinding allow-list
   defaults to localhost only, so every request to a real deployment was
   rejected. Derived from `MCP_PUBLIC_URL` now (+ new `MCP_ALLOWED_HOSTS`).

Plus the reported error itself: the RFC 9728 document was served
unconditionally, so clients read it, found no `authorization_servers`, assumed
this origin was the AS and attempted Dynamic Client Registration against it. It
now 404s until OAuth is both configured *and* enforced.

**Method note worth keeping.** The first SSE measurement used `TestClient` and
looked like a hang — its transport runs the app to completion, so an endless
stream can never finish. That artifact nearly buried a real bug; the two
configurations had to be compared over an actual socket. The regression test
therefore runs a real uvicorn server. Related: `test_mcp_remote_auth.py` and
`test_portal.py` **were never in CI's file list** — every test written for the
connector had been running only on developer machines. Now in `mcp-smoke.yml`
(340 tests there).

**Review:** Qodo found the SSE issue independently, plus the discovery/
`MCP_REQUIRE_AUTH` mismatch, an IPv6 host-split bug (`[2001:*`), and `/connect`
building its copy-paste URL from the Host header. All fixed. One Amazon Q
"crash risk" (`slashed.encode("utf-8")` vs `slashed.encode()`) declined —
byte-identical.

**Account page (личный кабинет):** `backend/portal/account.py` + three
templates — plan, own model keys, GDPR export, deletion. Deliberately thin: it
delegates to the API handlers that already exist (`auth.py`, `billing.py`,
`users.py`) so each rule has one implementation. Session is the same JWT in an
httpOnly `SameSite=Lax` cookie (Lax is the CSRF defence; every mutating route
is a POST). The database is opened lazily inside handlers rather than via
`Depends(get_db)`, so a signed-out visitor gets the page even when the DB is
unreachable — verified on a real server: `/account` 200, sign-in 503 with an
honest message, `/mcp` still 200 throughout.

**Testing constraint, recorded honestly:** the models use the PostgreSQL `UUID`
column type and the repo has no Postgres fixture, so account tests fake the DB
and assert the portal's own behaviour (cookie flags, delegation, failure
modes). The DB paths are not covered by tests.

**Still open:** `MCP_REQUIRE_AUTH=false` — `/mcp` is open to anyone with the
URL, and since the dispatcher bypasses the middleware it is now outside the
rate limiter too. Auth is the only thing that would bound it.
`docs/deploy/auth0-setup.md` written for that step (documents three Auth0
traps: opaque tokens without a Default Audience, DCR clients unusable until a
connection is `is_domain_connection`, issuer trailing slash). Needs owner
clicks in the Auth0 console.

### 2026-07-24 — claude/fandorin-portrait-generation-d422my — deploy unblocked, MCP connector, product architecture decided

**Trigger:** owner drove the split-deploy rollout, Render kept failing, and the
session turned into three decisions plus the code to back them.

**Deploy fixes (merged #153, #154):** the Render build was blocked by a chain
of dependency conflicts introduced when `mcp` and `claude-agent-sdk` were added
without reconciling older pins — httpx, then `openai-whisper` (unbuildable
sdist, unused, dropped with torch), then pydantic → 2.11, pydantic-settings,
python-multipart, uvicorn, and finally `mcp[cli]`'s typer colliding with spacy
(dropped the extra). Whole requirements file now resolves clean.
Also #154: five review defects, notably the void-of-course scan missing
240/270/300 offsets (it declared entire days void).

**MCP connector (merged #155):** `backend/mcp/remote.py` — streamable-HTTP
transport mounted into the FastAPI app at `/mcp`, plus the OAuth 2.1 *resource
server* half (RFC 9728 discovery, JWKS validation, 401 + WWW-Authenticate,
scope enforcement). Authorization server stays external by design. Fails closed
in production without an issuer. Runbook: `docs/deploy/mcp-connector.md`.

**Product architecture DECIDED (`docs/specs/product-architecture/`):**
MCP-first. The chat is the product surface; the website is a thin portal with
four jobs (explain / sign up / pay / issue access) plus legal pages. Rich web
UI deferred; the Next.js frontend is parked, not deleted; Vercel is off the
critical path. Accepted cost: free-tier chat users are unreachable for now.

**Orchestrator (`analysis_plan`):** new MCP tool that answers "what can be
computed and in what order" — `next_step`, `ready` (canonical order),
`blocked` with the exact missing input, verbatim ru/en questions, `completed`.
Dependencies are advisory (`better_after`), missing birth time degrades rather
than blocks (`degraded_without`). This is the fix for the real weakness of a
45-tool connector: neither the model nor the user knows what to ask for.
Tests: `test_analysis_plan.py` (9 passed, 1 skipped without the mcp package).

**Brand decision:** keep OneiroScope for now. Trademark/market check found
`Oneiros` dream apps and `Oneiroscope Games` as neighbours and `.com` taken →
usable but not clean (~6.5/10). No domain purchased: the connector needs no
custom domain, the directory display name carries the description, and with
zero users renaming later is as cheap as renaming now. Revisit when there are
users and a paid clearance is affordable. Candidates explored and rejected
with reasons: Kairoscope (opaque), Astrolab (domain gone), AstralLens (occult
connotation + one letter from an existing AstroLens app), AstroPrism
(unpronounceable in RU).

**Still open:** nobody has pressed Deploy on Render — that is the only thing
between the repo and a live connector. Then: portal, then STAVAGENT golden set
before Cemex Pitch Days.


### 2026-07-21 — claude/fandorin-portrait-generation-d422my — reverse physiognomy (Fandorin), portrait generator, patterns catalog → 6 skills + 6 MCP tools

**Trigger:** owner brought Akunin's public request for critique of a
50-year-old Fandorin portrait; the session grew from one reverse-
physiognomy case into a full patterns catalog and its implementation.

**Done:**
- **Fandorin case** (`docs/specs/fandorin-portrait/`): book-canon
  appearance table, critique of the author's variant, reverse KB
  mapping (traits → face), RU/EN generation prompt + negative.
  Owner generated the portrait, posted the reply publicly.
- **Portrait generator** `scripts/generate_fandorin_portrait.py`:
  gpt-image-1 + gemini-2.5-flash-image providers, generate/edit
  modes, output gitignored.
- **Patterns catalog** `backend/services/strategic/knowledge_base/
  analysis_patterns.json` + spec `docs/specs/strategic-patterns/`:
  six session-distilled recipes (money-contour, vocation-map,
  decade-map, life-pivots, electional-day, reverse-physiognomy),
  each = deterministic compute (1.0) → symbolic rules (0.8) →
  optional user_context loop (0.9), disclaimer + no_determinism flags.
- **Implementation of all six**: engine
  `backend/services/strategic/pattern_engine.py` (natal geometry with
  rulers/dignities/sect/Part of Fortune; house blocks + linchpin; MC
  complex; decade + pivot monthly scans; Moon-by-step electional with
  void-of-course; reverse-physiognomy KB lookup with
  fictional_or_self_only gate; importable WITHOUT the astrology-service
  stack — own compact Ptolemaic dignity table, Moshier mode); MCP tools
  `backend/mcp/tools/strategic_patterns.py` (registered in server.py,
  Phase 10 section); six skills in `.claude/skills/`; tests
  `backend/tests/test_strategic_patterns.py` — **13 passed** (neutral
  fixture chart, no PII) + smoke-test registration entries.
- Live validation during the session: owner's own natal/decade/pivot
  runs (hand-run predecessors of the engine) matched life facts the
  owner volunteered (наём не идёт; переломные окна) — the life-pivots
  validation loop is modeled on exactly that exchange.

**Known gaps:** skills call `mcp__oneiro__*` — with the MCP server
offline they need the documented fallback (direct engine imports);
electional VoC is 10-min-grid approximate (documented in methodology).

**Addendum (same session): life-pivots validation loop closed live.**
Owner confirmed/refuted the scanned windows verbally; resulting
calibration (weights only, biography stays out of the repo — full
version in gitignored `.claude/personal/astro-calibration.md`, which
does NOT survive container recycling): **angles/ASC = max weight (3/3
windows, one month-exact)**; Uranus opposition + Saturn return =
exact-by-theme; Pluto☌Moon + Saturn☌DSC = confirmed; Moon/MC transits
= quiet; some relocations invisible to the angle+luminary scan (honest
miss). Insight "наём не держится" elevated to HIGH (astronomy +
user_context, confirmed ≥3 independent periods) — it anchors the
"Saturn-in-2nd 2026-27 = build own income base" decade reading, and
the vocation-map pattern matched the owner's actual professional
profile. Apply-forward: Pluto☌ASC 2032-04 is the owner's top-weight
milestone of the 2026-2036 decade; Moon/MC transits downweighted.

**Trigger:** owner ran a live multi-batch photo reading (9 adult +
5 childhood frames of himself) and asked (a) that the system zoom into
photos and recognize traits itself instead of the questionnaire, and
(b) special attention to childhood→adulthood changes.

**Done:**
- **Auto-zoom detection ladder** (`_landmarks_from_photo`): native →
  2x/3x upscale on miss (archival prints), then a face-box crop
  enlarged to ~600px face height for a sharper second pass. Metrics
  are ratios, so crop-space coordinates need no back-mapping.
- **Anatomical lip thickness** (`FaceMetrics.lip_thickness`): outer
  vermilion (0→13 + 14→17) / mouth width (61–291), trusted only on a
  near-closed mouth (inner gap ≤ 6% of mouth width) — closes the
  known openness≠thickness gap from #144. Neutral ≈ 0.34 (Farkas);
  thin ≤ 0.30, full ≥ 0.40, deviations-only like fWHR. Questionnaire
  mouth answers now yield to geometry when a closed-mouth frame
  measured the lips (`mouth_measured` param), pass through otherwise.
- **Longitudinal module** (`services/physiognomy/longitudinal.py`) +
  MCP tool `physiognomy_timeline`: per-period medians → KB readings
  diffed by topic (stable / appeared / disappeared) + metric deltas;
  adult-anthropometry caveat and disclaimer travel in every result.
- Tests: 9 new (lip thin/full/open/questionnaire-precedence,
  longitudinal diff, median with missing optionals, MCP timeline);
  suite 32 passed.

**Live validation (owner's own archive):** 5 closed-mouth adult
frames gave lip_thickness 0.22–0.29 → mouth_thin, matching the
owner's self-report given *before* the metric existed. Timeline over
3 childhood vs 8 adult frames: stable — earth, dilated, wide-set
eyes, compact forehead, thin lips, low fWHR; appeared — water
secondary, lower court, athletic; disappeared — pyknic, middle-court
dominance. Sharper zoom landmarks pushed one borderline frame
(IMG_2029, asym 0.20) into the yaw gate — honest rejection.

**Addendum (same session, photo-max-extraction):** owner asked for a
system that extracts the maximum from any photo set, normalizes and
calibrates what it can, and degrades honestly for the rest; spec
written (`docs/specs/photo-max-extraction/`), core implemented:
`services/physiognomy/aggregate.py` + MCP `analyze_face_archive` —
detection ladder per photo, median profile, per-metric stability,
per-reading `support` with honest denominators (optional metrics
count only measurable frames: lips 5/5 closed-mouth, not 5/11), and
a coverage map (measured / questionnaire-only / guided-scan-only /
unreadable-in-principle, citing the evidence). Palace-zone texture
experiments (raw spread ×160; within-frame cheek-normalized still
×26; child-skin control indistinguishable from adult) permanently
closed casual-photo qi-se/palace reading; controlled-capture pilot =
Gate 5 in tasks.md. Live: 14 photos → 11 accepted in one call, earth
consensus 9/11, eye_spacing the only ≤10%-spread metric across ~45
years of frames.

**Gate 4 shipped (same session): guided face scanner.** Frontend
`/[locale]/face`: browser FaceLandmarker (@mediapipe/tasks-vision
0.10.14; wasm+model from CDN, `NEXT_PUBLIC_FACE_MODEL_URL` override),
live gates STRICTER than the server (yaw 0.15 vs 0.20, mouth 0.05 vs
0.06, plus face-size and cheek-brightness symmetry) so every captured
frame passes server-side; auto-capture 5 frames ≥600ms apart;
landmarks-only upload (privacy-first) to the new
POST /physiognomy/analyze-archive (≤24 frames, 422 when all frames
rejected). Pure gate math extracted to `frontend/lib/face-gates.ts`
(6 jest tests); `FaceScanner.tsx` with aria-live status,
loading/error/retry states, mobile single-column; FacePage i18n ru/en
+ Header nav item. Backend physiognomy tests 37, frontend 13,
tsc clean, `next build` green (route 4.18 kB).

**Calibration finding (live, owner):** the thin-lips reading's
«скупость на слова» clause was contradicted by the owner's report
(«очень разговорчивый») — an expected 0.6-tier miss, resolved by
life-context-wins. The composite itself carried the talkative signal
3-voices-to-1 (dilated 12/12 + water + childhood pyknic vs the mouth
clause). Lesson: dictionary voices conflict by design; portraits
should present conflicting clauses side by side, never averaged into
one verdict. Possible refinement (backlog): a narrative connective
for openly contradicting readings.

**Deferred:** brow/eyelid/cheekbone geometric detection (no reliable
FaceMesh heuristic yet — questionnaire remains their path); server CV
deps (mediapipe 0.10.14 pin uses legacy `solutions` API removed in
0.10.20+) still optional, not in requirements.txt.

### 2026-07-05 — claude/top-cities-living-work-shxind — MCP hardening, two-layer reports, second-subject field test (PRs #136–#144)

**Trigger:** continuation of the physiognomy session — owner asked to
subscribe to PR bot reviews and fix what's real, make physiognomy a
full MCP connector with file output, restructure reports (full
narrative first, then theses), and field-test the system on a second
person (friend, b. 26.03.1978 03:20 Zaporizhzhia, 18 photos).

**Done (all merged to main):**
- **Security hardening across PRs #136–#141, #143** — shared safe-path
  module `backend/mcp/tools/_files.py`: CWE-22 path confinement,
  project root from `__file__` (not cwd), writes confined to
  gitignored `reports/`, `.html`-only suffix, anchor-root exclusion
  (TMPDIR=/ case) + fallback test, photo reads confined to
  home/tmp/project, collision-proof names, 8MB + content-type cap on
  the API. Bot-review convergence policy applied: ~19 findings
  accepted/fixed, ~15 rejected with written rationale (Amazon Q went
  6+ consecutive false positives, incl. confusing the one-arg
  back-compat wrapper with the two-arg `_files` function).
- **Two-layer reports (#140):** full deterministic narrative
  (`compose_narrative`, KB text woven with connectives only, 0.6) →
  memorable theses (`compose_theses`) → sourced data → disclaimer.
  Applied to physiognomy + new MCP file-report tools
  `horoscope_report` and `profile_report_file`.
- **conventions.md §11 (#142):** external "senior engineer" prompt
  templates triaged — debugger/UI adopted; architect/review/perf
  bounded by Karpathy anti-bloat; persona simulation REJECTED in
  favor of the real adversarial loop (pytest + review bots +
  convergence policy).
- **Owner-caught contradiction → metric semantics fix (#144):**
  `lip_fullness` (inner-lip gap 13/14) measures mouth OPENNESS, not
  anatomical thickness — an expressive mouth averaged into «тонкие
  губы» across mostly-closed frames. Geometry no longer emits mouth
  readings (questionnaire-only); schema description corrected; 2
  backlog items (outer-point thickness metric; inter-frame
  variability as a first-class trait). Tests 23/23.

**Field test #2 (friend, 18 photos → 13 valid / 5 rejected by gates):**
- Earth-primary 13/13 (0.997–1.687), Water secondary 8/13; lower court
  rivals middle (two life peaks); nose borderline wealth (mean 0.2687);
  «живой рот» — lip-gap range 0.008–0.047 became the live case above.
  Chart cross-check: ASC Capricorn matches Earth face; Uranus·MC 0.2°;
  Rome crown +7.9 clean. Reports delivered (PDF + fixed HTML),
  anonymized — friend's PII excluded per repo rule.
- **ChatGPT-comparison lesson (recorded as method principle):** an
  unmeasured reader assigns elements from the presentation layer
  (smiles, poses, styling) and packages it in one confident voice;
  our split — skeletal structure (measured, 1.0) vs tradition
  dictionary (0.6) vs behavior — is exactly the provenance discipline
  that catches this failure mode. Structure ≠ подача.

**Dataset to date:** 2 people, ~39 photos, ~29 valid reads, ~8 honest
gate rejections; 6 live calibration findings, 4 closed in code.

**Deferred:** anatomical lip-thickness metric, inter-frame variability
trait, occlusion flags, dual-reference eye metric, child-face mode,
frontend `/[locale]/face`, Render build check with mediapipe/opencv.
**Next session (owner's plan):** re-run the friend's photos fresh
(«на чистую голову») end-to-end through the merged pipeline.

---

### 2026-07-04 — claude/top-cities-living-work-shxind — Physiognomy service (mianxiang + Western traditions)

**Trigger:** live client session (astrocartography consultation) drifted
into face reading; owner set goal: encode the Chinese mianxiang system +
Western physiognomy into OneiroScope with a photo-upload flow.

**Done:**
- Spec `docs/specs/physiognomy/` (requirements EARS + design + tasks).
- New service `backend/services/physiognomy/`: KB (`mianxiang.json` —
  5 elements, 3 courts, 12 palaces, 20 features; `western.json` —
  Lavater, Corman, Kretschmer, fWHR) with per-entry sources (Ma Yi Shen
  Xiang, Shen Xiang Quan Bian, Lavater 1775, Corman 1937, Kretschmer
  1921, Geniole 2015, Todorov 2017).
- Deterministic pipeline: FaceMesh 468 landmarks → scale-free ratios
  (`geometry.py`, confidence 1.0) → threshold classifier + KB lookup
  (`analyzer.py`, tradition tier **0.6** — deliberately below the 0.8
  symbol-dictionary tier because physiognomy lacks scientific validity).
- API `/api/v1/physiognomy`: GET /methods, POST /analyze
  (landmarks|metrics|features questionnaire), POST /analyze-photo
  (server CV optional → 501 with client-side guidance when mediapipe
  is absent). Privacy-first: photo stays in the browser; only landmark
  coordinates travel.
- Ethics: self-reflection only; disclaimer forbids use on third
  parties/hiring/legal; no health or attractiveness judgments.
- Tests: `backend/tests/test_physiognomy.py` — 9 passed (metric
  tolerance 1e-6, element classification, source+0.6 on every reading,
  disclaimer + forbidden-determinism words, questionnaire-only mode,
  no metric/questionnaire duplication).

**Live validation (same session, 21 photos of the owner 1981–2026):**
- 16 valid reads / 5 honest rejections; adult profile Earth-primary
  16/16, Metal secondary — reproducible across cameras and decades;
  same-day 4-photo series: fWHR spread 0.02 = method precision.
- 4 calibration findings from real photos: child-face/fringe
  (width_length off-scale), upper-court occlusion, yaw rotation,
  ICD/eye conflating aperture size with spacing (resolved with PD
  data: «55» was frame lens width 55-16, PD≈64).
- **Yaw pose-gate implemented same session** (eye-width asymmetry
  >0.20 → ValueError; 10 tests green) — rejected the rotated frame,
  passed frontals. Remaining 3 findings in tasks.md backlog.
- mediapipe==0.10.14 + opencv-headless added to backend requirements
  so `/analyze-photo` computes server-side after deploy.
- Owner profile dossier moved to gitignored `.claude/personal/
  owner_profile_patterns.md` (bot review caught the repo's own PII rule;
  full content also delivered to owner as PDFs). NOTE: the file existed
  in main history via PR #135 — history rewrite left to owner's call.
- Follow-up PR: bot-review fixes (zero-guard geometry, 8MB+content-type
  upload cap, response_model for /methods) + physiognomy MCP connector
  (`analyze_face`, `physiognomy_report` → HTML file, `physiognomy_methods`)
  + zone-structured HTML report renderer. 12 tests green; e2e smoke:
  photo → MCP tool → report file.

**Deferred:** frontend `/[locale]/face` page (browser FaceLandmarker +
questionnaire fallback), occlusion flags, dual-reference eye metric,
child-face mode, zone-structured report renderer, optional LLM
narrative layer (0.7).

---

### 2026-07-02 — claude/july-2026-transits-jja4qn — Dreams: Russian morphology + non-blank LLM fallback

**Trigger:** live walkthrough of the dreams KB found an inflected Russian
dream losing 5 of 8 symbols (exact/prefix keyword matching can't handle
case endings: «змею»≠«змея»), and `interpretation` coming back BLANK in
no-keys mode (the provider chain returns a stub with provider=None which
the parser accepted as an answer, so `_generate_fallback` never ran).

**Done:**
- `backend/services/dreams/morphology.py` — pure-Python Snowball Russian
  stemmer (no deps): normalize (ё→е), stem, keyword_stems (min length 3
  vs false positives), text_stems. «водитель» does NOT collapse to «вода».
- `analyzer.py` — stem-set pass in `_find_symbols` when regex misses;
  demo dream now yields 9 symbols instead of 3.
- `symbols.json` — suppletive verb/kin forms the stemmer can't unify
  (лечу/летел…, упал…, матери, отца…, бегу…) for 6 symbols.
- `ai/interpreter.py` — raise on provider=None / empty / unparseable LLM
  reply → existing `_generate_fallback` produces real summary +
  interpretation + recommendations instead of blank text.
- Tests: `test_dream_morphology.py` (15 cases) added to mcp-smoke; full
  smoke set now **269 passed**.

---

### 2026-07-01 — claude/july-2026-transits-jja4qn — Pattern features from live testing + synastry (Phase 9)

**Goal:** Turn the patterns from 4 live user tests (owner + 3 friends, all
Zaporizhzhia-born) into product features, plus compatibility (synastry).
Session earlier shipped interactive astrocartography (PR #130) and full
CI-green fixes incl. a real LunarWidget self-cancelling-effect bug (PR #131).

**Done (backend services, `backend/services/astrology/`):**
- `historic_tz.py` — birth-moment resolver: coordinates→IANA zone
  (timezonefinder) → zoneinfo historic rules (Soviet decree time works:
  1977/1989 Zaporizhzhia = UTC+3). Provenance: source, offset, pre-1970 flag.
  Rejects bad tz names instead of silently using UTC.
- `synastry.py` — inter-chart aspects + 5 dimension scores (attraction /
  emotional / communication / stability / tension, 0–100) + reflective
  summary. Conjunction nature resolved by planet pair (soft vs intense).
- `transit_arcs.py` — thematic phase timeline: significators derived from
  natal houses (occupants + cusp rulers + natural planets) per theme
  (money_debt / career / relationships / home); slow transits grouped into
  pressure/support phases + first sustained turning point. Reproduces the
  hand-made debt analysis (1989 chart: turning point = 2027-08).
- `astrocartography.py` — `clean` luck flag in `relocation_summary`
  (benefic angular AND no malefic angular ≤6°: Warsaw clean, Prague not);
  `compare_locations()` (side-by-side, order preserved); `theme_scan()`
  (luck/career/relationships/home city ranking with clean flags).
- `solar_return.py` — `suggest_locations()`: SR-relocation ranking by
  benefics/malefics in angular houses.
- `report.py` — one-call profile bundle (natal + places + themes + year
  transits + provenance + disclaimer) as JSON and self-contained HTML
  (print-to-PDF), no new deps.

**API (`/api/v1/astrology`):** `/astrocartography/compare`,
`/astrocartography/themes`, `/transits/arcs`, `/synastry`,
`/solar-return/suggest`, `/report` (json|html). ValueError → 400.

**MCP:** `compare_relocations`, `scan_cities_by_theme`, `transit_arc`,
`synastry`, `solar_return_suggest` registered in `server.py` (Phase 9 block).

**Tests:** +13 in `test_strategic_astro_tools.py` (28 total there) locking
session-validated facts: USSR +3h offsets, Warsaw-clean/Prague-mixed,
Pluto□Mars debt peaks (Jan+Oct 2026), synastry symmetry + bounded scores,
SR ranking, report structure incl. Sun-in-Cancer anchor. Full CI smoke set
locally: **254 passed**.

**Patterns that drove this (from live tests):** users live on their
Uranus/Pluto/Mars lines while their Venus/Moon belts are elsewhere; "clean
vs mixed" luck changes the read entirely; users ask for "строго по
транзитам" (raw-data-first); every reading converges to 4 themes
(luck/career/relationships/home); the deliverable is always the same
report bundle.

---

### 2026-06-29 — Real-use field notes + /me personal skill

Long session split in two: (1) finished the P1 queue, (2) used OneiroScope
as a real personal Strategic Analyst end-to-end, which surfaced concrete
product feedback.

**Shipped (code):**
- Earlier P1 work: `planet_in_house` (10×12), `transit_meanings`, frontend
  pricing/account/checkout (Phase 6.G), DE/ES/FR UI locales (Phase 6.F).
- `.claude/skills/me/SKILL.md` + `.claude/personal/profile.md` — a `/me`
  personal astrologer + dream interpreter. **The profile holds private data
  and is gitignored** (`.claude/personal/`, `.claude/skills/me/`) — local
  only; the public repo must not carry owner PII.

**Product conclusions (see `docs/FIELD_NOTES_real_use.md`):**
- The Strategic Analyst posture (no determinism / provenance / confidence /
  life-context-wins) is the real, if niche, differentiator. Validated.
- Gaps for the roadmap: per-angle astrocartography output (Asc/MC/IC/Desc →
  plain meaning); "score = tone, not intensity" caveat; time-sensitivity UX
  (transits robust vs angles/astrocartography sensitive ~15°/h); `.se1`
  bundling matters specifically for relocation precision; persistent saved
  chart/profile (`natal_chart_id` TODO).
- Safety: added "never interpret external clinical instruments (MMPI)" to
  `strategic_system.md`; lottery/gambling "lucky periods" stay refused.

**Note:** OneiroScope monetization left intentionally open (not decided
either way this session).

---

### 2026-06-28 (late-4) — P1 #6 (partial): DE/ES/FR UI locales (Phase 6.F)

Last item in the P1 queue. **Deliberately partial** — split the
engineering from the content-quality work, because PLAN §6.F gates the
domain content on DeepL Pro + human native review (which I cannot do
autonomously and won't fake).

**Done (engineering, shippable):**
- `frontend/messages/{de,es,fr}.json` — complete machine-draft of all 157
  UI strings. Validated programmatically: identical key shape + matching
  `{placeholders}` vs `en.json`. **Marked as pending native review.**
- `i18n/request.ts` + `middleware.ts` — locales en/ru/de/es/fr.
- `LanguageSwitcher` — DE/ES/FR buttons.
- tsc clean, next build green, jest 7/7.

**NOT done (left for the content pipeline, by design):**
- `backend/data/lunar_tables.json` + `dreams/knowledge_base/symbols.json`
  DE/ES/FR — these are the domain content needing DeepL + native review.
  Backend already falls back to EN, so de/es/fr users get localized UI
  chrome + EN domain content until the pipeline runs.

So **P1 #6 is partially closed**: UI locales live; content translation
remains a discrete follow-up (still needs a human + DeepL key).

**Shipped:** PR merged to `main`.

**P1 queue now empty of fully-autonomous items.** Remaining work is P0
(Cloud Run staging, Alembic) + the human-gated content half of #6.

---

### 2026-06-28 (late-3) — P1: frontend pricing / account / checkout (Phase 6.G)

Continued the P1 queue (goal "делай следующий незакрытый p1"). After the
two backend archetype P1s, the next unclosed item was the monetization
frontend surface (#5) on top of the existing Phase 6 Lemon Squeezy backend.

**Done:**
- `frontend/lib/auth-client.ts` — register/login/me + localStorage token
  storage (server-safe no-ops, Bearer header helper).
- `frontend/lib/billing-client.ts` — `createCheckout` (hosted Lemon URL)
  + `getSubscription`.
- Pages (bilingual RU/EN, design-token styled):
  - `[locale]/pricing/` — Free / Premium $9.99 / Pro(BYOK) $5.99 + one-time
    ($19 natal PDF, $29 yearly). Unauthed CTA → `account?next=pricing`.
  - `[locale]/account/` — login/register, profile + subscription summary,
    upgrade CTA, logout; resumes checkout via `?next`.
  - `[locale]/checkout/success/` — polls `/billing/me` for webhook-lagged
    tier activation.
  - `Header` nav + `messages/{en,ru}.json` (Pricing/Account/CheckoutSuccess).
- **Verified:** `tsc --noEmit` clean, `next build` green (all 3 routes
  compile, dynamic), `jest` 7/7.

**Prices** come from PLAN.md Phase 6 matrix. Pricing still uses placeholder
USD only in the UI; multi-currency display (€/₽) and the actual Lemon
variant IDs are env/dashboard config (`LEMON_VARIANT_*`), not frontend.

**Shipped:** PR merged to `main`.

**Still deferred:** Cloud Run staging smoke, Alembic migrations, DE/ES/FR
content translations (the last remaining P1, needs human native review).

---

### 2026-06-28 (late-2) — P1: transit_meanings archetype table

Continued through the P1 queue (goal: "делай следующий незакрытый p1").
Next unclosed item after planet_in_house was `transit_meanings.py`.

**Done:**
- `backend/services/astrology/archetypes/transit_meanings.py` — the
  transit archetype layer: symbolic meaning (conf 0.9) on top of the
  deterministic transit DATES from `compute_transits` (astronomy 1.0).
  Same composition philosophy as planet_in_house:
  - `TRANSIT_AGENDA` (6 slow transiting planets — process + tempo),
    cited to Hand *Planets in Transit* (1976) + Greene *The Outer
    Planets and Their Cycles* (1983).
  - natal drive reused from `PLANET_DRIVES`; aspect nature from `ASPECTS`.
  - `NAMED_TRANSITS` — canonical life-cycle transits get explicit
    archetype + specific citation. **Saturn □/☍ Sun = "Midlife
    reappraisal"** (the example named in next-session.md), Saturn Return,
    Pluto/Neptune/Uranus □ Sun.
  - Natal bodies restricted to Sun..Saturn to match `transits_engine`.
- MCP tool `transit_meaning()` → **MCP tools 24 → 25**; in
  `list_archetype_topics`.
- Tests +7. **Backend suite: 275 passed, 6 skipped.**

**Shipped:** PR merged to `main`.

**Still deferred (unchanged):** Cloud Run staging smoke, Alembic
migrations, frontend pricing/checkout, DE/ES/FR content translations.

---

### 2026-06-28 (late) — P1: planet_in_house hard table (10×12)

Follow-up session after the Phase 7-9 consolidation. Picked up the
first deferred P1 item from the consolidated entry below.

**Done:**
- `backend/services/astrology/archetypes/planet_in_house.py` — the
  10 planets × 12 houses lookup, completing the Phase 8 hard-archetype
  set. Built by **composition, not fabrication**: each cell joins a
  cited planet-drive descriptor (Tompkins *Contemporary Astrologer's
  Handbook* ch.4 / Hand *Horoscope Symbols*) with the already-cited
  house life-area (Sasportas *The Twelve Houses*). We deliberately do
  NOT invent a distinct page citation per cell — both real sources are
  returned joined, keeping the provenance principle honest.
- MCP tool `planet_in_house()` (layer `astrology_symbolic`, conf 0.9,
  disclaimer); registered in `server.py` → **MCP tools 23 → 24**.
- Listed in `list_archetype_topics`.
- Tests +5 (full 10×12 grid, dual-citation assertion, case-insens,
  invalid-input, tool wrapper). **Backend suite: 268 passed, 6 skipped.**

**Birth-chart verification run** (01.07.1977 22:30 Запорожье, UTC+3 —
re-confirmed via IANA `Europe/Zaporozhye` = +3 for that date, decree
time, no pre-1981 DST): full path planets → house assignment → table
produced cited deterministic readings for all 10 planets. Two honest
caveats on *that run* (not the code, which is test-covered): this
container lacks `.se1` files → MOSEPH approximate positions; house
numbers derive from an approximate Asc (~16° Aquarius) so are
indicative, not arc-precise. In prod (ephemeris files + GeoNames) the
placement is exact.

**Shipped:** PR merged to `main` (branch `claude/phase-9-consolidation-f64chg`).

**Still deferred (unchanged):** Cloud Run staging smoke, Alembic
migrations, `transit_meanings.py`, frontend pricing/checkout, DE/ES/FR
content translations.

---

### 📌 2026-06-28 — SESSION CONSOLIDATED (Phases 7-9 landed today)

End-of-day consolidation. Three merged PRs this session:

| PR | Phase | What |
|---|---|---|
| **#121** | 7 | Strategic Life Cycle Analyst pivot — 8-layer evidence matrix, no-determinism validator, 3 deterministic astronomy MCP tools (compute_transits, astrocartography_scan, solar_return_chart), Strategic Analyst agent, rewritten system prompts |
| **#122** | 8 | Hard archetype tables (MC/Sun/Houses/Aspects/Dignities with cited classical sources), 7 new MCP tools, Cloud Run + Vertex AI guide with ADC auto-detect, domain.md + conventions.md from peer-review scaffold, numeric confidence ladder, disclaimer enforcement |
| **#123** | 9 | Memory system harmonization — next-session.md, _TEMPLATE_spec/, _TEMPLATE_bug/, English TL;DR blocks in steering docs, §10 «Rejected ideas» |

**Numerical state at end-of-day:**
- MCP tools: **23** (was 13 at start of day)
- Specialist agents: **4** + 1 orchestrator
- Backend test suite: **263 passed, 6 skipped** (was 183)
- Memory scaffold files: **complete** (CLAUDE.md + soul.md §1-§10 + steering/5 files + next-session.md + 7 templates)

**Major architectural shift this session:** OneiroScope is no longer "another AI horoscope". It is now positioned as **Strategic Life Cycle Analyst** with:
- Provenance per claim (every output cites which layer + source)
- Confidence ladder 1.0/0.9/0.8/0.7 (astronomy / cited tradition / symbol dict / LLM)
- No deterministic prediction language (regex-validated)
- Mandatory disclaimer (5 locales, enforced)
- Hard archetype tables as 0.9-confidence layer (above LLM 0.7) for the well-known archetypal interpretation surface

**Key correction surfaced this session:** Prior manual chart analyses used wrong timezone (UTC+4 vs correct UTC+3 for USSR summer 1977 — decree time, no DST until 1981). All new MCP tools use `zoneinfo` correctly. The famous Jupiter ☌ natal Saturn aspect for the test chart (01.07.1977 22:30 Запорожье) is actually **September 11, 2026**, not August 25 — falls in the first 2 weeks of the user's magistratura at Pardubice.

**What's deferred to next session (P0/P1 in `docs/next-session.md`):**
- End-to-end smoke on Cloud Run staging
- Alembic migrations for User/Subscription/UserLLMKey
- `planet_in_house.py` (10 × 12 archetype table, completes Phase 8 set)
- `transit_meanings.py` (transit archetype with citations)
- Frontend pricing/checkout/account pages (Phase 6.G)
- DE/ES/FR translations for lunar_tables / symbols (human native review)

**Next session start sequence:** follow `CLAUDE.md` mandatory block — read 8 files in order (conventions → product → tech → structure → domain → soul → PLAN → next-session). The `next-session.md` file lists exact P0/P1/P2 priorities.

Individual phase entries below (chronological within today).

---

### 2026-06-28 — claude/memory-system-harmonization — Phase 9: scaffold memory-system harmonization

**Goal:** Owner shared the peer-review scaffold from another chat (full STAVAGENT-style memory-management system). Apply the missing pieces here: `next-session.md` handoff format, `docs/templates/_TEMPLATE_{spec,bug}/` workflows, English TL;DR blocks in steering docs, §10 "Rejected ideas" in soul.md, cleaner CLAUDE.md mandatory block.

**Done:**
- `docs/next-session.md` — handoff snapshot with project state table, what works / what's broken, P0/P1/P2 priorities, "context easy to lose" notes (USSR 1977 = UTC+3 not UTC+4, Jupiter ☌ Saturn = Sep 11 not Aug 25, etc.), open architectural decisions.
- `docs/templates/_TEMPLATE_spec/{requirements,design,tasks}.md` — full SDD template trio. EARS-style criteria, provenance-ladder mapping, 6 implementation Gates.
- `docs/templates/_TEMPLATE_bug/{report,analyze,fix,verify}.md` — reproduce-first bug workflow. Hypothesis-generation in analyze.md, domain-rule re-check in verify.md.
- `CLAUDE.md` mandatory block — expanded to read 8 files in order (conventions → product → tech → structure → domain → soul → PLAN → next-session). Added English TL;DR for external readers + the 5 core principles spelled out.
- `docs/soul.md` — English TL;DR + section map at top; new §10 «Rejected ideas» with 6 entries (Stripe+YooKassa, Llama-as-primary, Co-Star positioning, MCP separate service, pure-LLM MC interpretation, Chiron MOSEPH).
- `docs/steering/{product,tech,structure}.md` — added English TL;DR blocks in headers.
- `docs/PLAN.md` — Phase 8 logged + Phase 9 added and checked off.

**Decisions:**
- Kept `docs/steering/conventions.md` and `domain.md` from Phase 8 untouched (already match the scaffold).
- Did NOT renumber soul.md sections (would break all earlier §-references in commit history). Added §10 instead of fitting "Rejected ideas" into existing slots.
- Did NOT add `docs/specs/` or `docs/bugs/` directories yet — templates are ready to copy when needed, but creating empty dirs is bloat.

**Verification:**
- All scaffold-required files present: CLAUDE.md ✓, soul.md (§1-§10) ✓, steering/{product,tech,structure,domain,conventions}.md ✓, next-session.md ✓, templates/_TEMPLATE_{spec,bug}/ ✓.
- No code change in this PR → no test impact.

---

### 2026-06-28 — claude/hard-archetypes-cloudrun — Phase 8: Hard archetype tables + Cloud Run + scaffold adoption

**Goal:** After Phase 7 Strategic Analyst pivot, user requested **hard interpretation modules** (MC archetype tables, Sun, Houses, Aspects, Dignities) — so the system can cite classical/modern sources directly without going through LLM_NARRATIVE (0.7) → upgrade to ASTROLOGY_SYMBOLIC (0.9) with provenance. Also: peer-review scaffold suggestions to adopt + Cloud Run / Vertex AI integration.

**Done — archetype tables (`backend/services/astrology/archetypes/`):**
- `zodiac_signs.py` — 12 signs × {element, modality, ruler, keywords, shadow, description, source}.
- `mc_in_sign.py` — 12 MC archetypes (career role, NOT "destiny").
- `sun_in_sign.py` — 12 Sun archetypes (identity, with growth_edge).
- `houses.py` — 12 houses × area-of-life with natural sign/ruler.
- `aspects.py` — 5 aspects (conjunction/opposition/trine/square/sextile) with default orbs from domain.md §2.3.
- `dignities.py` — essential dignity table (domicile/exaltation/detriment/fall/peregrine) using **traditional** rulers per Lilly 1647.
- All citations from Sue Tompkins, Liz Greene, Howard Sasportas, Robert Hand, Stephen Arroyo — real, well-cited modern astrology sources.

**Done — MCP tools (`backend/mcp/tools/archetypes.py`):**
- 7 new tools: `mc_in_sign`, `sun_in_sign`, `house_meaning`, `aspect_meaning`, `planet_dignity`, `zodiac_sign`, `list_archetype_topics`.
- Each returns `{layer: "astrology_symbolic", confidence: 0.9, ..., source: <citation>, disclaimer: <text>}`.
- Registered in `backend/mcp/server.py` (total 23 tools, was 16).
- Added to `StrategicAnalystAgent.allowed_tools` (now 19, was 12).

**Done — scaffold adoption:**
- `docs/steering/domain.md` — adopted from scaffold. Confidence ladder 1.0/0.9/0.8/0.7, disclaimer rules, forbidden patterns, acceptance criteria (provenance/disclaimer/tolerance, not exact text).
- `docs/steering/conventions.md` — Karpathy anti-bloat rules, EARS-style criteria, commit/branch naming, update matrix, gates.
- `backend/services/strategic/disclaimer.py` — `ensure_disclaimer(text, locale)`, `has_disclaimer()`, sentinel-phrase paraphrase detection. 5-locale canonical text (RU/EN/DE/ES/FR).
- `backend/services/strategic/layers.py` — added `numeric_confidence()` function, `LAYER_CONFIDENCE` table mapping Layer → 0-1 numeric, convergence bonus.

**Done — Cloud Run + Vertex AI:**
- `docs/deployment/CLOUD_RUN.md` — full step-by-step (project setup → service account → secrets → Cloud SQL → Cloud Build → deploy → custom domain → optional Swiss Ephemeris bucket → CI/CD via Cloud Build trigger). ~$10-21/mo at MVP traffic.
- `backend/core/llm_provider.py::_provider_configured(VERTEX)` — now detects Cloud Run via `K_SERVICE` / `K_REVISION` env vars (set by Cloud Run automatically). When present + `VERTEX_PROJECT`, Vertex activates via metadata-server ADC — no explicit token needed.

**Tests:**
- `test_archetypes.py` — 35 tests (table completeness, required fields, dignity calculations, MCP tool wrappers carry layer/confidence/disclaimer).
- `test_disclaimer_and_numeric_confidence.py` — 18 tests (disclaimer detection across locales, paraphrase tolerance, idempotency; numeric ladder values match scaffold, convergence bonus, LLM-only cap).
- Updated `test_mcp_smoke.py` registry to include 7 new archetype tools.
- Updated `test_strategic_agent.py` allowed-tools to include archetype tools.
- All added to `mcp-smoke.yml` CI.
- Full backend suite: **263 passed, 6 skipped** (was 183 → +80).

**Decisions:**
- Archetype tables are deterministic Python dicts with cited sources — not configurable, not LLM-generated. This is the "0.9 cited classical rule" tier from the scaffold confidence ladder.
- Disclaimer is **enforced at the response layer** via `ensure_disclaimer()` — auto-appends if LLM forgot. Sentinel-phrase detection lets the LLM phrase its own version.
- Numeric confidence is **derived** from source mix, not declared. The 3-bucket Confidence enum (HIGH/MEDIUM/LOW) still exists as UI labels; the 0-1 float is for fine-grained ranking.
- Cloud Run vs Render: Cloud Run wins for solo founder (scale-to-zero, ~$10/mo vs ~$21/mo). Vertex AI ADC via metadata-server is the right path — no secrets to rotate.

---

### 2026-06-14 — claude/strategic-analyst-pivot

### 2026-06-14 — claude/strategic-analyst-pivot — Phase 7: Strategic Life Cycle Analyst pivot

**Goal:** After a long product-direction conversation (user explored own chart deeply with the existing tools, then surfaced peer-review feedback that "another astrology AI" is the wrong positioning), execute the **Strategic Life Cycle Analyst pivot** end-to-end in one PR: multi-layer evidence-matrix substrate, new deterministic astronomy tools (transits, astrocartography, solar return), new Strategic Analyst agent, rewritten domain prompts to inherit the posture.

**Why this matters now:** Co-Star / Sanctuary / Nebula saturate the predictive-astrology market with unfalsifiable text. OneiroScope's defensive moat is **forced source-attribution** — every claim is tagged with which analytical layer (astronomy / age psychology / user context / symbolism) produced it, and confidence is derived from the source mix, not declared. Astrology stays as a symbolic layer; it just doesn't get to pretend to predict.

**Done — Phase 7.A (substrate):**
- `backend/services/strategic/layers.py` — `Layer` enum (8 epistemic levels), `Source`, `Insight` (Pydantic with no-determinism validator), `EvidenceMatrix` with auto-derived `Confidence`.
- `backend/services/strategic/no_determinism.py` — regex guard for "will/будет/случится" + hedge-prefix allowlist + softener helper.

**Done — Phase 7.B (deterministic astronomy):**
- `backend/services/astrology/astrocartography.py` — `relocate()` + `scan_cities()` with planet/angle hits and a benefic/malefic scoring.
- `backend/services/astrology/transits_engine.py` — `find_transits()` with local-minimum detection over a date window.
- `backend/services/astrology/solar_return.py` — `solar_return()` with 2-stage (hourly + minute) search to arc-minute precision.
- `backend/mcp/tools/strategic_astro.py` — three MCP wrappers (`compute_transits`, `astrocartography_scan`, `solar_return_chart`), registered in `backend/mcp/server.py`. Total tools now 16 (was 13).

**Done — Phase 7.C (agent + prompts):**
- `agents/prompts/strategic_system.md` — full Strategic Analyst posture: 8 layers, hard rules (no determinism, source attribution, confidence derivation, skeptical default), required response structure (8 sections ending with Evidence Matrix), fixed closing line.
- `agents/prompts/astrology_system.md` — rewritten to inherit the posture.
- `agents/prompts/dream_system.md` — rewritten ("no diagnosis", "reflection prompts" instead of interpretations).
- `agents/specialists/strategic_agent.py` — `StrategicAnalystAgent` with 12 tools (synthesis across domains).
- `agents/orchestrator.py` — `strategic` intent router (RU + EN keywords); strategic wins when both strategic + domain present.

**Done — Phase 7.D (docs):**
- `docs/STRATEGIC_ANALYST.md` — design rationale, architecture diagram, code map, market positioning matrix, "what this is NOT", how to extend.
- `docs/PLAN.md` — Phase 7 fully checked off.

**Important correction surfaced during session:**
While running real chart tests through the new tools, discovered my prior manual analyses used **wrong timezone** (UTC+4 instead of correct UTC+3 for USSR 1977 summer — decree time, no DST until 1981). This shifted natal Asc/MC interpretations and the Jupiter ☌ Saturn date (was claiming Aug 25; actually Sep 11). The Strategic Analyst MCP tools use `zoneinfo` which handles historical timezones correctly. New tests lock in correct values.

**Verification:** 
- Backend suite: **183 passed, 6 skipped** (was 139). +44 new tests.
- All new files added to `mcp-smoke.yml` CI.
- MCP server registers 16 tools cleanly.

**Decisions:**
- Pivoted from "yet another astro AI" to Strategic Life Cycle Analyst. Free tier keeps classic astrology UI; Premium tier ($25-50/mo) gets the Evidence Matrix experience.
- Astrology kept as `Layer.ASTROLOGY_SYMBOLIC` (LOW confidence by default) — not removed.
- `Layer` enum is extensible — adding Vedic, Chinese cycles, biorhythms is "add to enum + add MCP tool".

---

### 2026-06-14 — claude/phase-6-lemon-implementation — Phase 6 production-ready: Lemon Squeezy MoR + auth + BYOK + quotas + 5-locale email + deployment & mobile guides
**Goal:** Owner is solo founder in EU, no юр.лицо. Pivot from Stripe+YooKassa to **Lemon Squeezy as Merchant of Record** and ship a production-ready service: auth, subscription, BYOK, quotas, 5-locale email scaffolding, deployment guide for Render+Vercel+Lemon+Resend, mobile strategy via Capacitor (iOS+Android).

**Plan pivot (PLAN.md Phase 6 rewritten):**
- Lemon Squeezy as MoR — handles VAT/sales tax/KYC/chargebacks; works with RU cards via card processor; **no юр.лицо**.
- 5 currencies/locales: USD/EUR + auto-detect by geo-IP; Lemon converts.
- Mobile = Capacitor wrap (Phase 6.J added) — one Next.js codebase, two app stores.
- Open questions resolved: Resend for email, DeepL Pro + human review for translations, 1 free natal lifetime + 1 horoscope/day.

**Backend implemented (production-grade):**
- `backend/models/user.py` extended: `password_hash`, `name`, `lemon_customer_id`, `free_natal_used`, `pending_deletion_at`, `llm_keys` relationship.
- `backend/models/user_llm_key.py` — new model for BYOK Fernet-encrypted keys.
- `backend/models/subscription.py` — added `tier`, `provider`, `lemon_subscription_id`, `lemon_variant_id`, `lemon_customer_id`; dropped old `check_one_gateway` constraint.
- `backend/services/byok/keys.py` — Fernet encryption derived from SECRET_KEY (rotation invalidates all keys — by design). `encrypt`/`decrypt`/`hint`.
- `backend/services/billing/quotas.py` — `Tier` enum + `assert_quota(user, QuotaKind)` raising HTTP 402 with CTA. Daily horoscope counter (in-memory; Redis path documented).
- `backend/services/billing/lemon_provider.py` — Checkout API (httpx), webhook HMAC-SHA256 signature verification, `parse_webhook()`, `tier_for_variant()`, product-slug-to-variant env mapping.
- `backend/services/email/resend_provider.py` — quiet no-op when `RESEND_API_KEY` unset; locale-aware template rendering with English fallback.
- `backend/api/v1/auth.py` — POST `/register`, `/login`, `/refresh`, GET `/me`; constant-time-ish password verification.
- `backend/api/v1/billing.py` — POST `/checkout`, `/webhook` (signature-verified + idempotent), GET `/me`.
- `backend/api/v1/users.py` — `/me/llm-keys` save/list/delete, `/me/data-export` (GDPR Article 20), DELETE `/me` (Article 17 soft-delete).
- All routers mounted in `backend/app/main.py`.
- MCP tool docstrings annotated `# ru | en | de | es | fr`.

**Email templates (5 locales):** `welcome.{subject,html}` for en/ru/de/es/fr (DE/ES/FR machine-translated baseline — flagged for native review in PLAN.md).

**Tests (38 new, all green):**
- `test_byok.py` (6): round-trip, empty rejection, tamper detection, hint redaction, secret-rotation invalidation.
- `test_quotas.py` (13): tier resolution (free/premium/pro precedence, inactive ignored), lifetime flags, daily counters, lunar always free, 402 payload shape.
- `test_lemon_provider.py` (12): signature verify (valid/tampered/missing/no-secret), variant lookup (known/unknown/unset env), tier mapping, webhook parsing (full/minimal), key/store unset errors.
- `test_email_templates.py` (7): rendering each of 5 locales, fallback to en, full variable substitution.
- Full backend suite: **139 passed, 6 skipped** (was 101 → +38).
- All 4 new test files added to `mcp-smoke.yml` CI; `cryptography` and `email-validator` added to CI deps.

**Documentation (production-ready):**
- `docs/DEPLOYMENT.md` — step-by-step Render+Vercel+Lemon+Resend setup, all env vars enumerated, custom domain DNS, monthly cost breakdown (~$65/mo), recurring ops checklist.
- `docs/MOBILE.md` — Capacitor wrap strategy, why-not-RN matrix, Xcode/Android Studio walkthrough, RevenueCat path for IAP, App Store metadata in 5 locales, 5-day timeline to TestFlight + Closed Track.
- `.env.example` extended with all Lemon Squeezy + Resend vars.

**What is NOT in this PR (tracked for next iteration):**
- Alembic migration for new User/Subscription columns — needs to be generated against existing schema (out of scope for code-only change; documented in DEPLOYMENT.md §1.3 as a one-time bootstrap step).
- Quota wiring into astrology/dreams endpoints (Phase 6.B sub-item) — service exists, the `Depends()` call to plug it in is straightforward but touches every endpoint signature; safer as a focused follow-up PR.
- DE/ES/FR translation of `lunar_tables.json` (31 days) and `symbols.json` (56 entries) — needs human native review with astrology/psychology context; flagged in DEPLOYMENT and PLAN.
- Frontend pricing/account/login pages — frontend work is the owner's plan.
- Capacitor `mobile/` directory — depends on `next.config.js` static-export flip; documented in MOBILE.md as the owner's next step.

---

### 2026-05-31 — claude/plan-phase-6-monetization — Phase 6 plan: monetization + 5-language GA
**Goal:** After owner clarified product direction (hybrid BYOK+web, audience RU/EN/DE/ES/FR), write Phase 6 of the plan covering auth, subscription, payments, and i18n expansion. No code yet — planning only.

**Decisions captured (from chat):**
- Backend ASR (Whisper/Vosk) **stays** — owner will build the web frontend; voice input is a UX driver for mobile.
- Audience: **5 languages** (RU, EN, DE, ES, FR) on the web, simultaneously.
- Two access paths: **MCP free (BYOK)** as community/SEO loss-leader + **Web subscription** for non-tech users.
- Pricing tiers drafted: Free / Premium ($9/€9/799₽) / Pro-BYOK ($5/€5/499₽) / one-time reports ($19-29).

**Phase 6 sub-phases written into `docs/PLAN.md`:**
- 6.A Auth foundation (JWT, User model, email verification).
- 6.B Subscription & quota DB, quota enforcement on astrology/dreams endpoints.
- 6.C Stripe integration (intl: USD/EUR markets).
- 6.D YooKassa integration (RU market; flagged юр.лицо requirement).
- 6.E Pro/BYOK tier — per-user encrypted LLM key + provider override.
- 6.F i18n DE/ES/FR — frontend messages, backend prompts, `lunar_tables.json` keys, dream-symbols translations, MCP `locale` enum extension, language auto-detect.
- 6.G Frontend pricing + checkout + account pages (region-aware provider routing).
- 6.H Transactional email (Resend/SendGrid, multilingual templates).
- 6.I GDPR compliance (data export, delete, cookie banner, privacy policy, retention).

**5 open questions documented at end of Phase 6** — owner needs to answer before implementation: юр.лицо для YooKassa, страна Stripe-аккаунта, email-провайдер, переводчик (DeepL vs human), free-tier лимиты.

---

### 2026-05-31 — claude/orchestrator-error-handling — gather(return_exceptions=True) fix
**Goal:** Address Amazon Q's review of PR #117 — multi-domain `asyncio.gather` would crash on any specialist failure.

**Done (PR #118):** `return_exceptions=True` + per-result `BaseException` check; failed domains surface as tagged inline `## Dream — temporarily unavailable: RuntimeError` block. Regression test `test_multi_domain_partial_results_when_one_specialist_crashes`. Suite: 101 passed, 6 skipped.

---

### 2026-05-31 — claude/adk-orchestrator — ADK Phase C+D: SuperOrchestrator + cost-tracker agent tag
**Goal:** Complete the SuperOrchestrator (routing + fan-out + merge) and per-agent cost tracking, finishing the plan started in PR #116.

**Done — Phase C (orchestrator):**
- `agents/orchestrator.py` — `SuperOrchestrator` with keyword-based intent router (deterministic, no extra LLM call). Single-domain passes streaming through as-is; multi-domain runs specialists in parallel via `asyncio.gather` and merges output with `## Domain` headers. Specialists are instantiated lazily — no idle stdio MCP children.
- `agents/cli.py` — `SuperOrchestrator` is now default; `--generalist` opts into the old single-agent path.
- Keyword tuning: `гороск` not `горо` (the latter false-matched "город" → mis-routed dreams about cities to astrology).

**Done — Phase D (cost-tracker agent tag):**
- `backend/core/cost_tracker.py` — keys now include `<agent>` segment (`oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:<suffix>`). `record()` resolves the tag from explicit arg → `ONEIRO_AGENT_NAME` env → `"default"`. `report()` aggregates across all tags by default; `agent=` filters to one; `group_by_agent=True` returns per-agent breakdown.
- `BaseOneiroAgent` — propagates `ONEIRO_AGENT_NAME=self.name` into the spawned MCP child's env, crossing the process boundary without extra infrastructure. The backend's LLM provider reads that env transparently.

**Deferred (tracked):**
- Context passing between specialists (e.g. natal chart `chart_id` → DreamAgent for personalized interpretation). Needs the persistence layer (§5 known issue).

**Tests:**
- `backend/tests/test_orchestrator.py` — 22 tests: 13 router cases + fallback, single/multi-domain dispatch, isolation, lazy instantiation, cost-tracker tag via env, explicit-agent precedence, MCP-env propagation.
- Full backend suite: **100 passed, 6 skipped** (was 78 → +22 orchestrator/cost-tag tests).
- Orchestrator tests added to `mcp-smoke.yml`.

---

### 2026-05-28 — claude/adk-specialists — ADK Phase A+B: base class + 3 specialist agents
**Goal:** Refactor the single `OneiroAgent` into a base class and stand up 3 domain-specialist agents (Astrology / Dream / Lunar) as Phase A+B of the SuperOrchestrator plan in `docs/PLAN.md`.

**Done:**
- `agents/base.py` — `BaseOneiroAgent` (name, system-prompt path, allowed_tools subset). Shared `run()` (streaming text deltas). Idempotent `_qualify()` (bare `tool` or `mcp__oneiro__tool` both work).
- `agents/oneiro_agent.py` — `OneiroAgent` is now a 30-line subclass of `BaseOneiroAgent` keeping all 13 tools; backward-compat CLI unaffected.
- `agents/specialists/{astrology,dream,lunar}_agent.py` — each declares a narrow tool subset:
  - astrology: 7 (natal/horoscope/forecast/list_* + geo helpers)
  - dream: 4 (analyze + list_*)
  - lunar: 2 (get_lunar_day/period)
- `agents/prompts/{astrology,dream,lunar}_system.md` — domain prompts (science-first, provenance shown, no prediction-as-fact, no esoteric/forbidden content).
- `backend/tests/test_specialist_agents.py` — 10 tests: import, tool-subset correctness, prompt content, name uniqueness, qualifier idempotence, generalist backward-compat. All green.
- Full backend suite: **78 passed, 6 skipped** (was 68 + 10 specialist). Specialist tests added to `mcp-smoke.yml`.
- `docs/PLAN.md` — Phase 5 added; A+B checked off.

**Next (Phase C+D, separate PR):** SuperOrchestrator (intent router + fan-out + context-passing + merge) + cost-tracker agent tag.

---

### 2026-05-28 — claude/cloud-llm-providers — Vertex AI + Bedrock providers, horoscope/dream test run, lunar-table path fix
**Goal:** Run sample daily/monthly/yearly horoscopes + a dream for birth data (01.07.1977 22:30 Запорожье), and add Vertex AI / Bedrock as LLM providers.

**Done:**
- **Vertex AI provider** (`backend/core/llm_provider.py`): Gemini via GCP regional endpoint. Auth via `VERTEX_ACCESS_TOKEN` or ADC (`google-auth`). Gated on `VERTEX_PROJECT` + creds.
- **Bedrock provider**: Claude via AWS `bedrock-runtime.invoke_model` (boto3, SigV4, sync call in executor). Gated on AWS creds + boto3 importable. Anthropic Messages schema + `anthropic_version: bedrock-2023-05-31`.
- Both added to the cost-ordered catalog (Vertex after Gemini, Bedrock after Anthropic) and to `_provider_configured()`; disable gracefully when unconfigured.
- `backend/tests/test_llm_providers_cloud.py` — 8 tests (gating + request construction with mocked httpx/boto3). Full backend suite 68 passed, 6 skipped.
- **Bug fix**: `backend/services/astrology/interpreter.py` loaded `lunar_tables.json` from `backend/services/data/` (wrong) instead of `backend/data/` — degraded ALL horoscope template content. Fixed the path (one more `dirname`).
- Deps: added optional `google-auth>=2.27`, `boto3>=1.34` to `backend/requirements.txt`.
- Docs: CLAUDE.md env section + provider table, `docs/steering/tech.md` provider list.

**Test run results (template fallback, no LLM keys in this env):**
- Natal chart 01.07.1977 22:30 Запорожье → Sun Cancer 9.83°, Moon Capricorn, Asc Aquarius, MC Sagittarius (MOSEPH analytic — no SWIEPH binaries locally). Geocoded via 90-city fallback (47.84, 35.20, Europe/Kyiv).
- Daily/monthly/yearly horoscopes: correct period boundaries; content brief+identical because template fallback only uses lunar day (LLM keys produce 600-1000 words/period).
- Dream analysis: symbols escape_liberation/house/animal, emotion happiness 0.65, archetypes liberation/self/instinct. Interpretation empty without LLM key.

**Notes:**
- Local env briefly had the `external/pyswisseph` stub shadowing real pyswisseph (from the build-CI work) — reinstalled real `pyswisseph==2.10.3.2` for accurate positions.
- Geocoder rejects "City, Country" suffix (", Украина" failed; bare "Запорожье" works). Candidate future fix: strip country segment before fallback lookup.

---

### 2026-05-26 — claude/fix-build-ci — Build CI hardening + startup ephemeris log
**Goal:** Get `build-and-validate` CI green (red on every PR since pre-existing) + add operator-friendly startup logs.

**Done (merged via PR #113):**
- `requirements.txt` / `etl/requirements.txt`: pin `numpy>=1.26,<3`, `pandas>=2.2,<3`, `pyarrow>=15`. Clean-venv install verified locally.
- `.github/workflows/build.yml`: upgrade `setuptools wheel build` alongside pip, switch to `pip install -v` (diagnostic), use `python -m pytest` for consistency with smoke workflow.
- `backend/app/main.py`: log ephemeris mode at startup (mirrors `/health`). INFO for SWIEPH, WARNING for MOSEPH fallback with `SE_EPHE_PATH` hint.

**Outcome:** `build-and-validate` **still red on PR #113** — root cause not visible without GHA log access. Verbose flag will surface the actual error on the next iteration. Smoke + inventory + dream tests all green.

**Decisions:**
- Did not chase further without log visibility. Pinned-version + diagnostic improvements are useful regardless of whether they fully resolve build-and-validate.
- Did NOT revert changes — all three are independently beneficial.

---

### 2026-05-26 — claude/fix-dream-narrative-tests — Dream interpreter v2.1 test fixes
**Goal:** Resolve the 6 known-failing tests in `test_dream_interpreter_narrative.py::TestContextualSymbolValidation` (noted as `§5` known issue; tracked as out-of-scope in the previous session).

**Done:**
- Added Russian keyword roots to `symbols.json` for `vehicle` (`автомобил`, `авто`, `машин`), `surveillance` (`слеж`, `следи`, `наблюд`), `boundaries` (`границ`, `наруш`, `вторг`), `escape_liberation` (`выброс`, `отброс`, `свобод`, `освобод`, `облегчен`). Root: the inflection-aware regex needs a literal prefix of the surface form.
- Restored strict reinforcement requirement for `surveillance` only — lone keywords like "camera" produced false positives. Other reinforcement-driven symbols stay soft.
- Added house exclusion for `(throw|выбросил…) … (window|окн)` — common in surveillance/escape dreams, the window is not a house symbol.

**Verified:** 14/14 dream narrative tests pass; full backend suite 60/60 (6 skipped). Updates §5 (5/14 → 0/14 failing).

**Decisions:**
- Did NOT change the Russian regex compilation (still `\bkeyword\w*\b`). Keyword roots were the lowest-risk fix.
- Strict reinforcement applied only to `surveillance`; widening it to others would regress legit detection cases.

---

### 2026-05-26 — claude/eager-noether-5UQJR — MCP + ADK + Skills foundation
**Goal:** Stand up MCP-server / ADK-agent / skills layer on top of existing FastAPI services + introduce discipline files (soul.md, steering/*, mandatory block in CLAUDE.md).

**Plan reference:** `docs/PLAN.md` (phases 0–4).

**Phase 0 completed:** Created `docs/PLAN.md`, `docs/soul.md` (this file), `docs/steering/{tech,structure,product}.md`, mandatory-block header in `CLAUDE.md`.

**Phase 1 completed — MCP server (`backend/mcp/`):**
- `server.py` runs FastMCP on stdio (default) or streamable-HTTP. 13 tools registered:
  astrology (calculate_natal_chart, generate_horoscope, forecast_event, list_event_types, list_horoscope_periods),
  dreams (analyze_dream, list_dream_symbols, list_archetypes, list_hvdc_categories),
  lunar (get_lunar_day, get_lunar_period),
  geo (search_city, validate_birth_data).
- `backend/tests/test_mcp_smoke.py` — 9 tests, all green.

**Phase 2 completed — ADK agent (`agents/`):**
- `OneiroAgent` spawns MCP server as stdio child; restricts allowed_tools to `mcp__oneiro__*` (no shell, no fs).
- System prompt enforces science-first, cost-aware tool chain, bilingual parity, provenance, no prediction-as-fact.
- `python -m agents.cli "<prompt>"` CLI entry.
- 5 agent smoke tests, all green.

**Phase 3 completed — Skills (`.claude/skills/`):**
- 8 SKILL.md files: `/natal`, `/horoscope`, `/dream`, `/lunar`, `/deploy-cycle`, `/validate-prod`, `/cost-report`, `/research-symbol`.
- README lists conventions; all skills consume `mcp__oneiro__*` only.
- Expanded `.claude/settings.local.json` with common dev permissions.

**Phase 4 partial:**
- `ENVIRONMENT=production` already set in `render.yaml` (verified).
- `/health` now returns `ephemeris` block (engine + path + first 5 files).
- `mcp[cli]>=1.2` + `claude-agent-sdk>=0.2` added to `backend/requirements.txt`.
- `.github/workflows/mcp-smoke.yml` runs 14 smoke tests on push/PR.
- Deferred: `cost_tracker.py` (needs middleware wiring), separate Render MCP service (embedded works), MCP Dockerfile (backend Dockerfile covers).

**Decisions:**
- MCP-first adopted: FastAPI services strict-typed → trivial adapters; one MCP server reusable from Claude Desktop, Cursor, agents, web Code.
- Agent restricted to MCP tools only — never invokes Bash/Write/Read directly, keeps domain scope clean.
- Skill layer never calls FastAPI HTTP — only MCP tools (rule in `docs/steering/structure.md`).
- Cost tracking deferred to next session: requires deeper LLM-provider middleware change.

**Out of scope this session:** user auth, natal-chart DB persistence, 5/14 failing dream interpreter tests, separate Render MCP service.

**Verified:** 14/14 smoke tests green (`pytest backend/tests/test_mcp_smoke.py backend/tests/test_agent_smoke.py`).

**2026-07-08 — `/client-report` run, no repo changes (client-report skill):**
- Generated a full Czech-language client report for a new client (11.2.1986, 12:50, Plzeň, CZ; current city = birth city). MCP server not connected this session → used the documented fallback path (direct imports from `backend.services.astrology`, package `__init__` stubbed to skip the heavy `AstrologyService` import chain).
- Environment had none of pyswisseph/timezonefinder/matplotlib installed — created a scratch venv and installed them there; no changes to `backend/requirements.txt` or any repo file. `world.geojson` (Natural Earth 110m) fetched fresh into scratchpad (no cached copy existed in-repo).
- Notable finding surfaced by the pipeline: natal Mercury/Venus/Jupiter sit within ~2° of this client's own MC, so `theme_scan` over `DEFAULT_CITIES` lit up almost the entire Central-European band (Munich +11.9, Rome +9.9, Milan +9.3, Zurich +8.4, Berlin +8.2, Prague +6.4) as "clean" career/luck cities — all clean, none flagged. Plzeň itself scores +8.3 clean via `compare_locations`, so the honest read was "no relocation needed," not a generic city list.
- Home/relationships themes returned almost nothing over the default pool (only one weak, non-clean hit each) — reported as an honest gap rather than forcing a recommendation.
- Solar Return 2026 computed for Plzeň per client's confirmation; 5 bodies (Sun/Mercury/Venus/Mars/Pluto) landed in SR house 1 — flagged as an unusually self-focused year.
- Delivered: 5-page PDF (`Astrologicky_profil_Plzen_2026.pdf`) + embedded astrocartography map, entirely in Czech, disclaimer included. No repo files were modified; all script/data artifacts live in the session scratchpad only.

*(append new entries above this line on next session)*

---

## §10 Rejected ideas (and why)

Track ideas we explicitly decided NOT to pursue, with the rationale.
Prevents re-debating the same questions in future sessions.

- **Stripe + YooKassa as payment providers** — rejected 2026-06-14
  (Phase 6 pivot). Solo founder in EU, no юр.лицо; Lemon Squeezy as
  Merchant of Record handles VAT/sales tax/KYC/chargebacks instead.
- **Llama-3.1-8b (Groq) as primary LLM for premium tier** — rejected
  2026-06-28. Llama-8b breaks the Strategic Analyst 8-section response
  structure and the no-determinism rule under load. Kept as fallback
  for free tier; premium uses Claude Sonnet 4.6 / Gemini Flash.
- **Loud public "AI horoscope" positioning (Co-Star clone)** —
  rejected 2026-06-14 (Phase 7 pivot). Saturated market with
  unfalsifiable text; OneiroScope's defensive moat is forced
  source attribution via the Evidence Matrix.
- **MCP server as a separate Render service** — rejected 2026-05-26.
  Embedded in the backend works (stdio child) and avoids a second
  paid service. Re-evaluate if/when MCP HTTP becomes external-traffic-
  heavy.
- **Pure-LLM interpretation for MC / Sun / Houses** — rejected
  2026-06-28 (Phase 8). Hard archetype tables with cited classical
  sources (Sue Tompkins, Liz Greene, Howard Sasportas, Robert Hand,
  William Lilly) give confidence 0.9 instead of 0.7 and run at
  $0 cost — strictly better than LLM-on-the-fly for the well-known
  archetypal layer.
- **Chiron / asteroid transits via MOSEPH analytic ephemeris** —
  rejected 2026-06-14 (Phase 7). MOSEPH doesn't ship asteroids
  (`seas_18.se1` is required). Two options remain: drop Chiron from
  the transit list (current state) OR upload `.se1` files to a Cloud
  Storage bucket and point `SE_EPHE_PATH` at it (Phase 8 Cloud Run
  guide §8 documents the path).
