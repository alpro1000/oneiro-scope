# Submission pack — модерация Claude Directory и ChatGPT Apps

> Гарантии «точно пройдёт» не существует: решение принимают ревьюеры
> Anthropic и OpenAI, и оба процесса оставляют место усмотрению. Что можно
> сделать — и что сделано здесь: закрыть каждое опубликованное требование,
> убрать всё, к чему у ревью есть готовый штамп отказа, и подготовить
> тексты заявок так, чтобы владелец их вставлял, а не сочинял.

---

## 1. Что ревью проверяет на самом деле

Обе площадки смотрят одно и то же, разными словами:

1. **Сервер работает и переживает их тесты.** Подключение, OAuth-цикл,
   вызовы инструментов, повторные вызовы, мусорные аргументы.
2. **Самоописание не врёт.** Инструкции сервера, описания инструментов и
   аннотации сверяются с поведением. Расхождение — готовый отказ.
3. **Политики платформы.** Медицинские/юридические/финансовые советы без
   квалификации, предсказания судьбы как факт, биометрические выводы о
   людях, сбор данных без объяснения — всё это штампы отказа.
4. **Приватность.** Политика существует, достижима, соответствует тому,
   что сервис реально делает с данными; путь удаления работает.
5. **Инъекции.** Описания инструментов и ответы сервера не содержат
   директив хосту («ignore previous…», «do not tell the user…»).

## 2. Состояние: закрыто кодом ↔ ждёт владельца

| Требование | Состояние |
| --- | --- |
| HTTPS remote MCP (streamable-http) | ✅ `<backend>/mcp` |
| OAuth 2.1 resource server + RFC 9728 | ✅ `/.well-known/oauth-protected-resource` |
| **Dynamic Client Registration у issuer** | ⚠️ проверяется строкой `dcr_advertised` в `/connect/diagnostics`. Auth0 поставляется с выключенным флагом — включить: Settings → Advanced → «OIDC Dynamic Application Registration». Без него подключение Claude умирает с «Failed to start MCP authorization» |
| Честные инструкции сервера | ✅ «science-grounded astrology» удалено; заявлен раскол: расчёт ↔ традиция, не наука; not-advice прямо в тексте. Закреплено `test_mcp_moderation.py` |
| Аннотации инструментов | ✅ все 19: `readOnlyHint`/`openWorldHint`, писатели только `calculate_natal_chart` (идемпотентен) и `analyze_dream(remember=True)`; внешняя сеть только у геокодинга. Закреплено тестом |
| Нет инъекционных форм в описаниях | ✅ тест греппит те же шаблоны, что и ревью |
| Privacy / Terms / Disclaimer | ✅ `/legal/*` на фронте |
| **Контакт в privacy** | ⛔ `frontend/app/legal/privacy/page.tsx:28` — «адрес будет опубликован». Обе формы требуют рабочий контакт. Только владелец |
| **Support email в форме** | ⛔ владелец |
| Дисклеймер на каждом толковании | ✅ `disclaimer.py`, `no_determinism.py` — принудительно |
| Биометрия | ✅ физиогномики нет в MCP-поверхности (снята в WP-10; на сайте — только self-reflection со своим запретом на оценку других). **Не возвращать её в MCP до/после подачи** — у обеих платформ политики против вывода характеристик из биометрии |
| **Лицензия Swiss Ephemeris** | ⛔ AGPL или Professional (~CHF 750), выбрать ДО публичного запуска. Поле «права на компоненты» есть в обеих формах. Только владелец |
| Аптайм под ревью | ⚠️ Render `plan: free` засыпает; keepalive-workflow смягчает, но на время ревью надёжнее платный инстанс. Владелец |
| **Тестовый доступ ревьюеру** | ⛔ обе площадки просят тестовые креды для OAuth-приложений. Завести отдельный аккаунт (не владельческий!) и вписать в форму. Владелец |
| CORS для сайта | ✅ `browser_origins` в `/connect/diagnostics` |

## 3. Тексты заявки — вставлять как есть (EN)

### Short description (≤ ~200 chars)

> Deterministic astrology & structural dream analysis. Swiss Ephemeris
> charts, astrocartography, relocation, lunar calendar; Hall/Van de Castle
> dream coding where every count cites its clause. Every claim carries a
> source and confidence.

### Long description

> OneiroScope separates what is computed from what is interpreted — and
> labels both.
>
> The astronomy is deterministic: Swiss Ephemeris natal charts with houses
> and applying/separating aspects, transits, solar returns, astrocartography
> line sets (GeoJSON), side-by-side relocation comparison, and a lunar
> calendar. Dream analysis uses Hall/Van de Castle structural coding: every
> count cites the exact clause it came from, with precision gates enforced
> in CI against a hand-coded bilingual golden set, plus comparison against
> DreamBank norms.
>
> Every response carries provenance and a per-claim confidence: computed
> 1.0 · cited rule 0.9 · symbol dictionary 0.8 · model synthesis 0.7. The
> server refuses deterministic prediction language; astrology and dream
> interpretation are presented as traditions of reading, not sciences.
>
> Seven tools ship interactive views (MCP Apps, `ui://`): the natal wheel,
> the astrocartography map, the lunar month, dream coding with its evidence
> highlighted in the user's own text, relocation comparison, and chart
> patterns. Every row has an "explain" control that hands its exact figures
> back to the conversation — the model reads the same numbers the user is
> pointing at. The views declare no CSP domains: no fetch, no external
> assets, nothing to warn the user about.
>
> Reflective / entertainment material — never medical, psychological,
> legal or financial advice.

### Category / tags

Lifestyle (или Entertainment, если Lifestyle нет) · astrology, dreams,
astronomy, journaling, self-reflection.

### Data handling (ответы на вопросы формы)

- **What data does the app receive?** Birth date/time/place for chart
  computation (processed per request), dream text for coding (processed per
  request, never stored by default), city names for geocoding (sent to
  GeoNames).
- **What is stored?** Nothing by default. Two explicit opt-ins: an account
  stores its own natal grant; `analyze_dream(remember=true)` stores coded
  numeric features of the caller's own dreams — never the dream text.
- **Third parties?** GeoNames (geocoding queries). LLM providers receive
  request content only when a text interpretation is explicitly requested.
- **Deletion?** Account page → delete: the row is erased immediately in one
  transaction (no retention window). Privacy policy: `/legal/privacy`.
- **Children?** Not directed at children; reflective/entertainment content.

### Reviewer test instructions (шаблон — вписать креды)

> 1. Connect: `https://oneiroscope-backend.onrender.com/mcp` (OAuth; the
>    client self-registers via DCR).
> 2. Test account: `<EMAIL>` / `<PASSWORD>` — a dedicated review account,
>    not a personal one.
> 3. Suggested flow: `search_city("Prague")` → `validate_birth_data` →
>    `calculate_natal_chart` (renders the interactive wheel; press
>    "explain" on any aspect row) → `analyze_dream` with any short dream
>    text (renders the coding with evidence highlighted; nothing is stored
>    without `remember=true`) → `get_lunar_period` (renders the month).
> 4. Health & self-diagnosis: `/health`, `/connect/diagnostics`.

## 4. Чем это отличается от всего в категории (для поля "what makes it unique")

> The only server in its vertical that shows its work: per-claim provenance
> and confidence, dream coding with clause-level evidence, CI precision
> gates on the interpretation layer — and the only astrology/dream server
> shipping MCP Apps interactive views at all.

(Не писать «Swiss Ephemeris» как отличие: его используют VedAstro, W8s,
intellecat, AskSoma, Kerykeion; Astrodienst его написал. Для ревьюера,
знающего рынок, это признак незнания рынка.)

## 5. Что ещё может завалить ревью — честный список

1. **Лицензия SwissEph не выбрана** → поле про права заполняется неправдой
   или пустотой. Блокер №1, решение владельца.
2. **Контакт-заглушка в privacy** → формальный отказ по privacy-требованию.
3. **DCR выключен в Auth0** → ревьюер не сможет даже подключиться; симптом
   «Failed to start MCP authorization». Проверка: строка `dcr_advertised`.
4. **Cold start на free-плане** → таймаут при первом же тесте ревьюера.
5. **Нет тестового аккаунта** → ревью OAuth-приложения не начинается.
6. Астрология как категория проходит у обеих платформ (в каталогах она
   есть), ПОКА нет медицинских обещаний и предсказаний как факта — у нас
   это закрыто принудительным дисклеймером и запретом детерминизма, и
   теперь закреплено тестами на сами описания.

## 6. ChatGPT: два пути, не перепутать

- **Connector** — тот же remote MCP по URL. Готовность = Claude-готовность.
- **Apps SDK / каталог приложений** — отдельная подача с ревью UI.
  Наши виды — стандартный `io.modelcontextprotocol/ui`, который ChatGPT
  рендерит; козыри в заявке: нулевой CSP (никаких внешних доменов),
  аннотации read-only, «explain» как честный мост из UI в разговор.

Порядок: сначала MCP Registry (`server.json` уже в корне, см.
`directories.md` §1), затем Claude Directory, затем ChatGPT — каждая
следующая форма переиспользует ответы предыдущей.
