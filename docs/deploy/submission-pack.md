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
| Аннотации инструментов | ✅ все 21: `readOnlyHint`/`openWorldHint`, писатели только `calculate_natal_chart` (идемпотентен) и `analyze_dream(remember=True)`; внешняя сеть только у геокодинга. Закреплено тестом |
| Нет инъекционных форм в описаниях | ✅ тест греппит те же шаблоны, что и ревью |
| Privacy / Terms / Disclaimer | ✅ `/legal/*` на фронте |
| **Контакт в privacy** | ⛔ `frontend/app/legal/privacy/page.tsx:28` — «адрес будет опубликован». Обе формы требуют рабочий контакт. Только владелец |
| **Support email в форме** | ⛔ владелец |
| Дисклеймер на каждом толковании | ✅ `disclaimer.py`, `no_determinism.py` — принудительно |
| Биометрия | ⚠️ **владелец вернул чтение лица в MCP** (`read_face_traits`, `physiognomy_methods`). Это осознанный риск, а не недосмотр — см. §5а ниже: что именно сделано, чтобы риск был минимальным, и что всё равно остаётся |
| **Лицензия Swiss Ephemeris** | ⛔ AGPL или Professional (~CHF 750), выбрать ДО публичного запуска. Поле «права на компоненты» есть в обеих формах. Только владелец |
| Аптайм под ревью | ⚠️ Render `plan: free` засыпает; keepalive-workflow смягчает, но на время ревью надёжнее платный инстанс. Владелец |
| **Тестовый доступ ревьюеру** | ⛔ обе площадки просят тестовые креды для OAuth-приложений. Завести отдельный аккаунт (не владельческий!) и вписать в форму. Владелец |
| CORS для сайта | ✅ `browser_origins` в `/connect/diagnostics` |
| **Брендинг экрана входа Auth0** | ⛔ Tenant Settings → General: `Friendly Name` = OneiroScope, `Logo URL` = `https://oneiroscope.vercel.app/icons/icon-192.png`, Support Email/URL. Пустые поля → человек, нажавший «Connect» у OneiroScope, попадает на страницу с логотипом Auth0 и техническим именем тенанта. Ревьюер читает это как небрежность или как фишинг |
| **Auth0 на пробном плане** | ⚠️ баннер «7 days left in your trial». После него тенант падает на Free, и всё, чего в Free нет, отключается — включая, возможно, лимит приложений, вокруг которого крутилась вся отладка коннектора. Выяснить ДО подачи: View Plans → что именно платное |

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

## 4a. Ручной OAuth-клиент чинит владельца, а НЕ продукт

Если подключение у владельца работает через вручную созданное приложение
Auth0 (Client ID + Secret вставлены в коннектор) — это **не** готовность к
подаче, и путать эти два состояния нельзя:

| | Ручной клиент | Нужно для каталога |
| --- | --- | --- |
| Владелец подключается | ✅ | ✅ |
| Ревьюер подключается | ❌ | ✅ |
| Любой пользователь | ❌ | ✅ |

Из каталога коннектор добавляют **по URL**, и клиент регистрируется
динамически (RFC 7591). Свой Client Secret владелец никому передать не
может и не должен. Пока DCR не работает, продукт технически обслуживает
одного человека.

Диагностика: `<backend>/connect/diagnostics?probe=1`. Если строка
`dcr_advertised` говорит «accepts dynamic registration», а коннектор всё
равно отвечает «Couldn't register» — остаётся документированное требование
Auth0: динамически зарегистрированные клиенты являются **third-party**
приложениями и могут пользоваться только соединениями, повышенными до
**domain-level**. Переключателя в дашборде нет, только Management API:

```
GET   /api/v2/connections           → id нужного соединения
PATCH /api/v2/connections/{id}      {"is_domain_connection": true}
```

Перед подачей: починить DCR, удалить ручное приложение, убедиться, что
подключение проходит с ПУСТЫМИ полями Client ID/Secret.

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

## 5а. Чтение лица в MCP — решение владельца, риск и что его снижает

Владелец вернул физиогномику на MCP-поверхность (2026-08-11). Прошлая
редакция этого файла советовала обратное; решение принято владельцем при
явно названном риске, и ниже — честная его формулировка, а не задним
числом придуманное обоснование.

**Что именно вернулось.** Два инструмента из пяти:

| Инструмент | Вход | Статус |
| --- | --- | --- |
| `read_face_traits` | анкета (13 полей словами), опционально `metrics`/`landmarks`, посчитанные КЛИЕНТОМ | ✅ в реестре |
| `physiognomy_methods` | — (список традиций и их источников) | ✅ в реестре |
| `analyze_face`, `physiognomy_report`, `analyze_face_archive`, `physiognomy_timeline` | `photo_path` — путь на диске СЕРВЕРА | ❌ остались снятыми |

**Почему именно так, а не «вернуть как было».** Удалённый клиент физически
не может положить файл на наш диск: фото у пользователя на машине. Значит
`photo_path` — мёртвый параметр перед живым читателем файлов нашей же ФС
(защищённым `_safe_read_path`, но защищённая дверь в пустую комнату лучше
закрыта). Осталась форма, которую чат реально может произвести: **человек
описывает своё лицо словами**. Это вообще не биометрическая обработка —
нет изображения, нет измерения, нет шаблона. Ровно это и есть аргумент
перед ревью, и он держится только пока в реестре нет фото-инструментов;
`test_the_face_tools_never_take_a_server_side_path` следит за этим.

**Что закреплено тестами** (`test_mcp_moderation.py`):

- у `read_face_traits` в схеме ровно `features`/`metrics`/`landmarks`/`locale`;
- описание содержит «not scientifically validated» + источник (Todorov 2017);
- описание запрещает оценку других людей поимённо: hiring, lending,
  insurance, tenancy, policing;
- ответ несёт дисклеймер и источник у каждого пункта; пустой вызов — ошибка.

**Что риска не снимает.** Ревьюер вправе прочитать «face reading» как
запрещённую категорию, не открывая схему, — и тогда отказ получит **весь
сервер**, а не одна функция. Управляемый выбор здесь один:

1. подать каталогам поверхность без чтения лица, добавить после одобрения
   (обновление инструментов ревью не блокирует), — риск ниже, функция
   доступна на сайте всё это время;
2. подавать как есть — риск выше, зато поверхность одна и честная.

Это решение владельца, не техническое. По умолчанию действует (2) — то,
что в коде сейчас.

## 6. ChatGPT: два пути, не перепутать

- **Connector** — тот же remote MCP по URL. Готовность = Claude-готовность.
- **Apps SDK / каталог приложений** — отдельная подача с ревью UI.
  Наши виды — стандартный `io.modelcontextprotocol/ui`, который ChatGPT
  рендерит; козыри в заявке: нулевой CSP (никаких внешних доменов),
  аннотации read-only, «explain» как честный мост из UI в разговор.

Порядок: сначала MCP Registry (`server.json` уже в корне, см.
`directories.md` §1), затем Claude Directory, затем ChatGPT — каждая
следующая форма переиспользует ответы предыдущей.
