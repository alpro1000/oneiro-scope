# Physiognomy Reading — Tasks

- [x] Спека (requirements/design) — 2026-07-04
- [x] KB: mianxiang.json (5 элементов, 3 двора, 12 дворцов, черты) с источниками
- [x] KB: western.json (Лафатер, Корман, Кречмер, fWHR) с источниками
- [x] geometry: лендмарки → метрики (детерминизм, тесты на допуск)
- [x] analyzer: метрики/анкета → readings c source+confidence
- [x] service + schemas (Pydantic v2, bilingual)
- [x] API: GET /methods, POST /analyze, POST /analyze-photo (501 без CV)
- [x] Роутер в app/main.py
- [x] pytest: метрики, классификация, дисклеймер, анкетный режим
- [ ] Frontend `/[locale]/face`: браузерный FaceLandmarker + анкета-fallback
- [ ] Опционально: LLM-пересказ отчёта (0.7, поверх readings)
- [ ] Опционально: mediapipe в prod-требования, если нужен серверный фото-путь
