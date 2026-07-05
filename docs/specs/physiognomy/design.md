# Physiognomy Reading — Design

## Слои (по правилам structure.md: детерминизм → словарь → AI)

```
Фото (браузер)
   │  MediaPipe Tasks JS (FaceLandmarker) — на устройстве,
   │  фото никуда не уходит
   ▼
468 лендмарок ──► POST /api/v1/physiognomy/analyze
                        │
                        ▼
              geometry: метрики лица          ← детерминизм, 1.0
              (fWHR, трети, W/L, межглазье,
               челюсть/скулы, полнота губ)
                        │
                        ▼
              analyzer: классификация          ← пороги в коде,
              (5 элементов, 3 двора,             задокументированы
               маппинг черт)
                        │
                        ▼
              knowledge_base/*.json            ← словарь традиций
              (мянсян + западные школы,          с источниками, 0.6
               каждая запись с source)
                        │
                        ▼
              PhysiognomyResponse
              (metrics + readings + provenance + disclaimer)
```

Альтернативные входы того же /analyze:
- `metrics` — готовые отношения (для тестов и сторонних клиентов);
- `features` — анкета перечислимых черт (без фото вообще).
Приоритет: metrics > landmarks > features; features дополняют
неизмеримое (веко, взгляд) всегда.

`POST /analyze-photo` (multipart) — опциональный серверный путь:
try-import mediapipe; при отсутствии — 501 со ссылкой на клиентский
путь. Файл в памяти, на диск не пишется.

## Ключевые лендмарки (MediaPipe FaceMesh, 468 точек)

| Точка | Индекс |
|---|---|
| лоб/верх овала | 10 |
| подбородок | 152 |
| скулы L/R | 234 / 454 |
| углы челюсти L/R | 58 / 288 |
| брови (верх середины) L/R | 105 / 334 |
| глаза: наруж/внутр L | 33 / 133 |
| глаза: внутр/наруж R | 362 / 263 |
| основание носа | 2 |
| крылья носа L/R | 98 / 327 |
| губы верх/низ | 13 / 14 |
| углы рта L/R | 61 / 291 |

Метрики — отношения расстояний (масштабонезависимы). Пороги
классификации элементов — константы в analyzer с комментарием WHY.

## KB-структура

`mianxiang.json`: five_elements, three_courts, twelve_palaces,
features{eyes,brows,nose,mouth,ears,chin,cheekbones,forehead}.
`western.json`: lavater_zones, corman, kretschmer, fwhr_note.
Каждая запись: {ru, en, source}. Confidence НЕ в KB — единая
константа traditions-tier 0.6 в коде (одно место правки).

## Frontend (следующая итерация, отдельная task)

Страница `/[locale]/face`: загрузка/камера → FaceLandmarker
(@mediapipe/tasks-vision, модель в public/, ~3 МБ) → landmarks →
/analyze → рендер отчёта с картой уверенности и дисклеймером.
Fallback-анкета — те же enum'ы, что features в API.

## Почему не LLM-first

Традиции конечны и словарны — LLM здесь добавил бы только
галлюцинации. LLM-слой (пересказ отчёта живым языком) — опция
позже, поверх готовых readings, с confidence 0.7 и меткой.
