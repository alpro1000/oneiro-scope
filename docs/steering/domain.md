# domain.md — Astrology + Dream-journal domain rules

> **English TL;DR:** domain rules. Astronomy is deterministic
> (Swiss Ephemeris) and never produced by an LLM; interpretation is the
> AI layer and always labelled. Strict ethical disclaimer: reflective /
> entertainment content only, never medical / psychological / legal /
> financial advice, no absolute predictions.

Adopted from peer-review scaffold (2026-06-28) — synthesizes the
Strategic Life Cycle Analyst posture with concrete domain rules.

## §1 Disclaimer (НЕнарушаемо)

- Контент носит **рефлексивно-развлекательный** характер.
- НЕ медицинский, психологический, юридический, финансовый совет.
- UI **обязан** показывать дисклеймер видимо (не подвалом мелким шрифтом).
- **Запрещены абсолютные предсказания**: здоровье, смерть, беременность,
  гарантия событий, диагнозы, императивные советы вида «уйди от партнёра /
  уволься».
- Любое толкование — рекомендательным тоном («часто связывают с…»),
  не в императиве и не как факт о будущем.

**Технический enforcement:** `backend/services/strategic/disclaimer.py` —
`ensure_disclaimer(text, locale)` добавляет дисклеймер если отсутствует;
`has_disclaimer(text, locale)` — быстрая проверка для тестов.

## §2 Астрология — детерминированное ядро (Confidence 1.0, БЕЗ LLM)

- §2.1 **Зодиак**: tropical (дефолт) / sidereal (опция). ADR-001.
- §2.2 **Системы домов**: Placidus (дефолт) / Koch / Whole Sign / Equal.
  ADR-002.
- §2.3 **Аспекты и дефолтные орбисы** (из `archetypes/aspects.py`):

  | Аспект | Угол | Дефолтный орб |
  |---|---|---|
  | Соединение | 0° | 8° |
  | Оппозиция | 180° | 8° |
  | Трин | 120° | 7° |
  | Квадрат | 90° | 7° |
  | Секстиль | 60° | 5° |

- §2.4 **Эссенциальные достоинства** — таблицы Лилли (1647) в
  `backend/services/astrology/archetypes/dignities.py`. Используются
  только традиционные правители (Mars/Scorpio, Saturn/Aquarius,
  Jupiter/Pisces) для подсчёта силы; современные (Pluto/Uranus/Neptune) —
  только для справки.
- §2.5 **Эфемериды**: Swiss Ephemeris через `pyswisseph`. SWIEPH (binary,
  arc-second) предпочтительно; MOSEPH (analytic) как fallback. Покрытие
  тестами golden-test'ами.
- **Правило**: положение/дом/аспект — математика, покрыта `compute_transits`,
  `solar_return_chart`, `astrocartography_scan`. LLM сюда **не вмешивается**.

## §3 Астрология — интерпретация (AI и hard-tables)

**Confidence ladder для интерпретативного слоя:**

| Источник | Confidence | Где живёт |
|---|---|---|
| Эфемерида / геометрия | 1.0 | `backend/services/astrology/{ephemeris,transits_engine,astrocartography,solar_return}.py` |
| Цитата классика (Lilly, Greene, Tompkins) | 0.9 | `backend/services/astrology/archetypes/*.py` |
| Словарь символов снов | 0.8 | `backend/services/dreams/knowledge_base/symbols.json` |
| LLM-синтез | 0.7 | Любой `generate_*` через `UniversalLLMProvider` |

**Структура толкования (обязательная):**
1. **Факт расчёта** (астрономия, confidence 1.0)
2. **Классическое правило с цитатой** (archetype-таблицы, confidence 0.9)
3. **LLM-синтез под контекст пользователя** (помечен, confidence 0.7)
4. **Disclaimer** (обязательно)

**Язык формулировок:**
- ✅ «в традиции X это обычно толкуется как…»
- ✅ «классически связывают с…»
- ✅ «вероятность выше», «период связан с»
- ❌ «это ЗНАЧИТ, что…», «с тобой ТОЧНО случится…», «НИКОГДА / НУЖНО»

**Технический enforcement:** `backend/services/strategic/no_determinism.py` —
regex-валидатор «will/будет/случится» внутри `Insight.statement`. Pydantic
отвергает детерминистические формулировки при конструировании.

## §4 Сны — лексикон и фреймворки

- §4.1 **Словари символов (lookup, confidence 0.8):**
  `backend/services/dreams/knowledge_base/symbols.json` — 56 символов,
  Hall/Van de Castle категории + Юнгианские архетипы. Каждая запись —
  с источником в коде.
- §4.2 **Фреймворки толкования:**
  - Hall/Van de Castle (1966) — контент-анализ
  - Юнгианские архетипы — символика
  - REM/NREM — нейрокогнитивный контекст
  - DreamBank — норм-сравнение по полу
  - Лунный контекст — symbolic only (confidence 0.8)
- §4.3 **Связка сон ↔ астрология**: если включена — транзиты на дату сна
  как доп. контекст, помечен как интерпретация. ADR-003.
- **Правило**: словарный hit — детерминирован; обобщение по сну — LLM с
  пометкой `Layer.LLM_NARRATIVE`.

## §4b Физиогномика — традиции и особый confidence-tier

- §4b.1 **Системы:** мянсян (5 элементов, 3 двора 三停, 12 дворцов
  十二宮, словарь черт; источники: Ma Yi Shen Xiang, Shen Xiang Quan
  Bian, Liu Zhuang Xiang Fa) + западные школы (Лафатер 1775, Корман
  1937, Кречмер 1921, fWHR по Geniole 2015). KB:
  `backend/services/physiognomy/knowledge_base/`.
- §4b.2 **Confidence 0.6 — собственный tier НИЖЕ словаря символов
  (0.8):** физиогномика научно не валидирована (Todorov 2017), это
  фиксируется в provenance каждого ответа. Измерения лица
  (лендмарки → отношения) — детерминизм, 1.0.
- §4b.3 **Этика жёстче обычной:** только само-рефлексия владельца
  фото; запрещено применение к третьим лицам, найму, кредитным и
  правовым решениям; никаких суждений о здоровье, привлекательности,
  этничности. Причина — история злоупотреблений (Ломброзо).
- §4b.4 **Приватность:** канонический путь — лендмарки извлекаются в
  браузере, фото не покидает устройство; серверный CV — опция.

## §5 Этические границы (что НЕ делаем)

Запрещённые паттерны (примеры):
- предсказания смерти / болезни / беременности;
- «звёзды велят тебе…» как руководство к действию;
- диагнозы психических расстройств по снам;
- финансовые / инвестиционные сигналы (включая ставки, лотереи,
  крипто-спекуляции);
- юридические советы;
- романтические рекомендации в императиве («уйди / останься»).

**Технический enforcement:** `backend/services/dreams/ai/prompts/` —
prohibited list в JSON-промпте dream interpreter'а. Будущий
`backend/services/strategic/forbidden_topics.py` — единый список с
автотестами.

## §6 Acceptance-критерии домена

- ✅ Расчёт домов для известной даты совпадает с эталонной эфемеридой
  ±допуск (1 arc-min для SWIEPH, 1 arc-deg для MOSEPH).
- ✅ Любой ответ с толкованием содержит дисклеймер (`has_disclaimer()`
  возвращает True).
- ✅ Любой ответ не содержит запрещённых детерминистических формулировок
  (`contains_determinism()` возвращает `[]`).
- ✅ Каждое толкование несёт `source` (citation) и `confidence` (numeric).
- ❌ Толкование возвращает **ровно текст T** — текст вариативен, не
  привязываемся к дословному совпадению. Привязываемся к структуре и
  провенансу.

## §7 ADR (Architecture Decision Records)

См. `docs/soul.md §6` для живого индекса. Ключевые:
- **ADR-001**: Tropical zodiac — дефолт. Sidereal — опция.
- **ADR-002**: Placidus houses — дефолт.
- **ADR-003**: Strategic Analyst posture — pivot из «AI horoscope»
  в decision-support tool (PR #121).
- **ADR-004**: Hard archetype tables — отдельный слой между астрономией
  и LLM (PR на текущей ветке).
- **ADR-005**: Lemon Squeezy как MoR — без юр.лица (PR #120).
