# Field notes — OneiroScope under deep real use

> Captured after an extended real-world consultation using OneiroScope as a
> personal **Strategic Life Cycle Analyst** — full natal + transits + solar
> return + astrocartography + dream + lunar across a long multi-turn session.
> These are **product observations** (gaps + validations) to guide the
> roadmap. No personal data here — behaviour notes only.

## ✅ What works (validated in real use)

- **Strategic Analyst posture** (no determinism, provenance, confidence
  ladder, life-context-wins) produces honest, differentiated readings vs
  "vibes" astrology. **This is the product's real differentiator** — and a
  niche one (most consumers want vibes), which is useful to know for
  positioning.
- **Archetype tables compose well.** `planet_in_house`, `transit_meaning`,
  `sun_in_sign`, dignities + `compute_transits` + `solar_return_chart` +
  `astrocartography_scan` combine cleanly into a real strategic life
  analysis.
- **Solar Return relocation works** and is genuinely insightful (the
  birthday location sets the year-chart angles). Worth surfacing in UI/skill.
- **Disclaimer + numeric confidence ladder** keep readings grounded and
  honest under pressure.

## 🔧 Gaps surfaced (roadmap candidates)

1. **Per-angle astrocartography output.** `astrocartography_scan` returns
   angle hits + a score, but there's no clean per-city
   **`Asc / MC / IC / Desc → planet → plain meaning`** breakdown. Real use
   required ad-hoc scripting. Add a formatter/tool that lists the four
   angles, the planet on each (within orb), and a plain-language meaning.
   (Prototyped during the session.)
2. **Score = tone, not intensity.** `_score_hits` weights Mercury / Uranus /
   Neptune at 0, so a city with those planets *exactly* on angles scores ~0
   despite being highly "active". Document that the score = easy/hard
   **tone**, NOT how much is happening; consider a separate
   "angularity/activity" metric.
3. **Time-sensitivity is a first-class UX concern.** Astrocartography angles
   and house cusps shift ~15° per hour of birth time; transits and sign
   placements do not. The product should (a) distinguish **time-robust**
   outputs (transits, signs) from **time-sensitive** ones (Asc/MC/houses,
   astrocartography), and (b) warn when birth time is uncertain/unknown.
4. **`.se1` ephemeris bundling matters for relocation features.** MOSEPH
   approximation is fine for transit dates (±1 day) but degrades
   astrocartography/house precision. Prioritise bundling `.se1`
   (`seas_18.se1` etc.) for the **astrocartography / solar-return** path
   specifically — not just transits.
5. **Persistent saved chart / profile.** The `natal_chart_id`
   personalization TODO is real: a user should save their chart once and
   have horoscope/transit/relocation tools reuse it without re-entry.
   (Implemented locally as a `/me` skill + a gitignored personal profile,
   but the product itself lacks the concept.)

## 🛡️ Safety guardrails (validated — keep hard)

Real use confirmed these matter; they must stay enforced (see
`agents/prompts/strategic_system.md`):

- **No "lucky periods" for lottery/gambling**; no predicting competition
  wins, exam pass/fail, health, or specific financial returns.
- **No interpretation of external clinical/psychological instruments**
  (e.g. an MMPI profile) — that is for a licensed professional; route the
  user there instead of reading scales.
- **Birthplace/relocation framing:** present a "difficult" relocated chart
  (e.g. Neptune on MC) as a **place-specific mirror**, never a verdict on
  the person's ability or worth.
