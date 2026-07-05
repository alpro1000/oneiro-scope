# photo-max-extraction — Tasks

- [x] Gate 1 — aggregation service: per-metric medians + stability,
      per-topic support, element consensus, coverage map;
      questionnaire supplement honours mouth_measured. (2026-07-05)
- [x] Gate 2 — MCP tool `analyze_face_archive` (photo set and/or
      metric dicts), skips with reasons; registered in server.
      (2026-07-05)
- [x] Gate 3 — tests: aggregation math, support counting, coverage
      classes, MCP path. (2026-07-05)
- [x] Gate 4 — guided face scanner (frontend `/[locale]/face`):
      browser FaceLandmarker (@mediapipe/tasks-vision), live gates
      (face-found / yaw ≤0.15 / mouth ≤0.05 / face-size / cheek
      brightness symmetry — stricter than the server so captures
      always pass), auto-capture 5 frames ≥600ms apart,
      landmarks-only POST to /physiognomy/analyze-archive, profile
      render with support + coverage map + disclaimer. a11y
      (aria-live status, labels), loading/error/retry states, mobile
      single-column. Pure gate math in `lib/face-gates.ts` with unit
      tests. (2026-07-05)
- [ ] Gate 5 — (research, separate decision) controlled-capture
      texture pilot: does scanner-grade even lighting make palace
      zones stable enough to measure? Requires new evidence BEFORE
      any KB rules; if unstable again — close permanently.
