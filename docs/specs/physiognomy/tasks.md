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
- [ ] Калибровка: детское лицо / чёлка дают width_length ~0.98 (вне всех
      взрослых прототипов → элемент-скоринг вырождается в jaw-терм);
      добавить age-режим или warning при width_length > 0.9
- [ ] Метрика межглазья: ICD/eye_width путает «широкую посадку» с
      «компактной глазной щелью» (живой кейс: 1.23–1.25 при
      ICD/лицо 0.24–0.26 ≈ норма 0.23 и щели/лицо 0.19–0.21 —
      офтальмологи того же человека говорят «узко»). Ввести двойную
      проверку (ICD/eye + ICD/face) и отдельную черту
      eyes_compact_aperture → KB eyes_small; wide/close только при
      согласии обеих линеек
- [x] Pose-gate: детектор асимметрии ширин глаз L/R (>0.20 → отказ)
      внедрён в geometry (2026-07-04); live-валидация: кадр с asym
      0.36 отвергнут, 0.16 пропущен
- [ ] Occlusion-флаги: аномальный верхний двор (чёлка/убор) → «зона
      закрыта, не читаем» вместо чтения (принцип честности до черт)
- [x] Рендер отчёта: self-contained HTML по зонам (метрики → элементы →
      дворы → чтения по системам с источниками) — report.py (2026-07-05)
- [x] MCP-коннектор: analyze_face / physiognomy_report (файл HTML) /
      physiognomy_methods в backend/mcp (2026-07-05)
- [x] Ревью ботов PR#135: zero-guard в geometry, лимит 8MB + content-type
      + 413/415 на /analyze-photo, response_model для /methods, PII-досье
      перенесено в gitignored .claude/personal/ (2026-07-05)
- [x] Ревью ботов PR#136: MCP hardening — output_path прикован к
      tmp/cwd (CWE-22), photo_path — к home/tmp/cwd (анти-зондирование
      ФС в HTTP-режиме), уникальные имена отчётов (%f+uuid), guard на
      пустой ввод, null-guard в рендерере (2026-07-05)
- [x] Ревью ботов PR#137: cwd-обход ограничения закрыт (корень проекта
      от __file__ вместо runtime cwd + отбрасывание anchor-корней);
      пустая строка output_path = default, каталог = ValueError
      (2026-07-05)
- [ ] Frontend `/[locale]/face`: браузерный FaceLandmarker + анкета-fallback
- [ ] Опционально: LLM-пересказ отчёта (0.7, поверх readings)
- [ ] Опционально: mediapipe в prod-требования, если нужен серверный фото-путь
