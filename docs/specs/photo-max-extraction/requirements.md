# photo-max-extraction — Requirements

> **English TL;DR:** Turn the physiognomy pipeline from
> one-photo-at-a-time into an archive analyzer: extract the maximum
> the photos can honestly give (multi-frame aggregation, quality
> gates, normalization where it is physically valid), and report a
> coverage/degradation map for everything they cannot. A guided
> live-capture "face scanner" (frontend) closes the gap for
> parameters that uncontrolled photos can never provide.

**Feature name:** photo-max-extraction
**Owner:** alpro1000
**Status:** accepted (owner request 2026-07-05: «система … умела
определить максимум из фото и нормализировать разные фото …
откалибровать размеры цвета все возможные параметры … сканер лица …
если их нет то надо определить по доступным данным»)
**Created:** 2026-07-05

---

## §1 Problem statement

Live use (owner archive, 14 photos over ~45 years; friend, 18 photos)
showed the real workflow is always a SET of heterogeneous photos, not
one frame. Today the aggregation (medians, per-topic frequency,
stability) is done by hand in ad-hoc scripts each session. Meanwhile
several parameters are physically unreadable from casual photos
(skin texture/color of the twelve-palace zones: proven ×26 spread
after within-frame normalization; child control frame
indistinguishable from adult) — but the system never says so
explicitly in its output, so users keep asking for them.

## §2 Out of scope

- Reading skin texture / qi-se color / palace smoothness from
  uncontrolled photos — proven unreadable (2026-07-05 experiments);
  only a guided-capture path may revisit this, and only as its own
  spec after the scanner exists.
- Any new interpretation texts: readings come ONLY from the existing
  KB dictionaries.
- Identifying or analyzing third parties (disclaimer unchanged:
  self-reflection for the photo owner only).

## §3 Users and use cases

1. Owner/user with a photo archive (mixed ages, mixed quality) wants
   one stable portrait + what changed over time (timeline exists).
2. User asks "what else can you determine?" — system answers with a
   coverage map: measured / questionnaire-only / needs guided scan /
   unreadable-in-principle, each with the reason.
3. Future: user opens the frontend face-scanner page, gets live
   feedback (turn head straight, close mouth, even lighting), the
   scanner auto-captures N gate-passing frames and feeds the same
   aggregation.

## §4 Acceptance criteria (EARS)

- КОГДА пользователь передаёт набор фото, система ДОЛЖНА обработать
  каждое через лестницу детекции (авто-zoom), отбраковать
  непригодные с причиной и агрегировать пригодные (медианы метрик).
- КОГДА кадров ≥ 2, система ДОЛЖНА сообщать межкадровую стабильность
  каждой метрики и долю кадров, поддерживающих каждое чтение
  (`support`), не изменяя словарную достоверность 0.6.
- КОГДА параметр недоступен по фото, система ДОЛЖНА явно отнести его
  к одному из классов: анкета / управляемая съёмка / нечитаемо в
  принципе — с причиной; она НЕ ДОЛЖНА выдавать чтение без измерения.
- КОГДА доступна анкета, ответы ДОЛЖНЫ дополнять только неизмеренные
  черты (существующее правило mouth_measured сохраняется).
- Все ответы ДОЛЖНЫ нести дисклеймер и провенанс (без изменений).

## §5 Success metrics

- Одна MCP-команда воспроизводит вручную собранный портрет владельца
  (12 кадров, 3 сессии) без ad-hoc скриптов.
- Ни одного чтения без измерения или ответа анкеты в выходе.
