---
name: client-report
description: Full client astrology report in one command — natal portrait, birth + current city angles, themed city rankings with clean-luck flags, year-by-month transits, Solar Return, line map, and a polished PDF. Use when the user supplies a client's birth data ("клиент", "посчитай для...", date+time+city) or invokes /client-report. Optional synastry between two people.
---

# /client-report — Client report pipeline

## What this does

Produces the standardized client deliverable that was hand-built and
refined across five live profiles (2026-07 session): one command in,
one PDF out. Every report has the same structure, the same honesty
rules, and the same disclaimers — that consistency IS the product.

Pipeline (all deterministic, Phase 9 services):

1. **Birth moment** — `historic_tz.resolve_birth_moment` from
   coordinates (handles Soviet decree time; never guess offsets).
2. **Natal chart** — planets, Placidus houses, aspects → personality
   portrait ("who they are in one sentence" + table + key aspects).
3. **Birth city + current city** — `compare_locations`: four angles,
   planets on angles, honest summary incl. `clean` flag.
4. **Cities by theme** — `theme_scan` for luck / career /
   relationships / home over the default pool (`report.DEFAULT_CITIES`)
   plus any cities the user mentions. Always show ✅ чисто vs
   ⚠️ с минусом — never hide malefics.
5. **Year by month** — `find_transits` (slow planets, orb ≤1°),
   grouped by month with 🟢/🔴 and windows "act / consolidate / rest".
   For an acute topic (debt, move, exams) add `transit_arcs.compute_arc`
   with its pressure/support phases + turning point.
6. **Solar Return** — nearest birthday at the current city; if the user
   asks "where to celebrate", rank candidates with
   `solar_return.suggest_locations`.
7. **Line map** — matplotlib PNG: country borders (cached
   `world.geojson`), MC/IC meridians + ASC/DESC curves per planet,
   ★ markers on the report's top cities, ▪ on the current city.
8. **PDF** — rich HTML (self-contained, DejaVu Sans for Cyrillic,
   base64-embedded map) → Chromium headless `--print-to-pdf`.
   Fallback without Chromium: `report.build_report` +
   `report.render_html` and deliver the HTML.
9. Deliver PDF + map via file attachment; give a short chat summary
   (lead with the most interesting finding, not a section list).

## How to invoke

- `/client-report 19.12.1956 13:30 Запорожье, живёт в Запорожье`
- `/client-report 1978-03-26 03:20 Zaporizhzhia, lives in Moscow`
- "Новый клиент: женщина, 24 января 1989, 22:30, Запорожье, живёт в Самаре"

Options (append to the command):
- `--synastry <second person birth data>` — add a compatibility
  section via `synastry.compute_synastry` + `synastry_summary`
  (dimension scores 0–100 + reflective summary).
- `--lang en` — English report (default: ru).
- `--short` — skip the map and Solar Return; 2-page PDF.
- `--cities <list>` — extra candidate cities for the theme scan.

## Required inputs

- **birth_date**, **birth_time** (ask once if missing; noon fallback
  drops ASC/houses and the report must say so), **birth_place**.
- **current_city** — where the client lives now. If absent, ask once;
  if unknown, produce the report without section 3's second column.

## Behavior rules (non-negotiable)

- **Time zones are resolved, never assumed.** USSR births = decree
  time via zoneinfo history; surface the resolved offset + source in
  the PDF header. Bad tz input → ask, don't default.
- **Honesty over flattery.** A benefic line with a tight malefic
  nearby is "⚠️ удача с минусом", and hard periods (Saturn/Pluto
  squares) are named as care-windows, softly but truthfully.
  Age-appropriate tone: for elderly clients frame hard transits as
  "поберечься, плановое внимание к здоровью", never as fear.
- **No determinism language** (enforced project-wide): "период
  располагает", "традиционно связывают" — never "будет/случится".
- **Relocation ≠ prescription.** Where the chart is neutral at home,
  say so ("уезжать не предписано"); frame cities as "в гости за
  подзарядкой" unless the client explicitly plans to move.
- **Explain the jargon inline — don't make the client ask twice.**
  (owner feedback, 2026-07-08: a report was sent without this and the
  client couldn't read the transit table at all). Every report needs a
  short plain-language glossary covering: the four angles (ASC = как
  проявляешься, MC = карьера/статус, DESC = партнёрства, IC = дом/тыл);
  aspect words (конъюнкция/трин/секстиль = мягко работает вместе,
  квадратура/оппозиция = трение, требующее внимания); the 🟢/🔴 and
  ✅чисто/⚠️с минусом flags; and one line on what each theme
  (luck/career/relationships/home) actually scans for (which planets,
  which angle). Put it right after the header, before the first table
  that uses this vocabulary — don't assume the reader already knows.
- **Show ALL four angles for every city, not one pre-filtered theme.**
  (owner feedback, 2026-07-08: "надо учитывать все возможные варианты и
  человек пусть сам решает" — list every angle contact and what it
  means; let the reader decide what they care about instead of the
  report silently filtering to one lens.) For every city that gets a
  detailed writeup (birth/current city, shortlisted candidates), call
  `astrocartography.full_angle_breakdown(result)` — it returns EVERY
  natal planet within orb of EVERY angle (Asc/MC/IC/Desc), each with a
  cited archetype description (confidence 0.9, composed from
  `archetypes.planet_in_house` since angles anchor houses 1/4/7/10) and
  a benefic/challenging/neutral tag. `theme_scan`'s single-theme
  ranking is still useful for shortlisting candidates out of a big
  pool, but the actual per-city writeup should show the full picture.
- **Always show the composite `score`, but explain it — good or bad.**
  Call `astrocartography.score_explanation(result)` alongside the
  score. `_score_hits` only weighs Venus/Jupiter/Sun/Moon (positive,
  Venus/Jupiter at 3.0 vs Sun/Moon at 1.0) and Saturn/Mars/Pluto
  (negative) — **Mercury, Uranus and Neptune contribute exactly 0**
  regardless of orb. A city can have a razor-tight, genuinely
  meaningful contact — e.g. Uranus conjunct MC at 0.4° (career:
  innovation/tech/entrepreneurial reputation) or Mercury conjunct Desc
  at 0.3° (relationships: contract/negotiation-based partnerships) —
  and still show a low or flat composite score, because the scorer
  can't see those planets at all. A low score does NOT automatically
  mean "nothing here" (`score_explanation` says so explicitly when
  `driving` is empty but `unweighted` isn't) — and when the score
  genuinely IS low/negative because of a real malefic contact, name
  which one and its orb (`score_explanation` does this too), don't
  just show the number. This is exactly why two different readings of
  the same city (e.g. "good for luck" vs "good for business") can both
  be true — they're reading different planets on different angles, not
  contradicting each other.
- **Always show `total_significance` next to `score` — nothing gets
  dropped.** (owner feedback, 2026-07-08: "надо добавить все контакты
  ... чтобы не терять ничего" — don't just caveat the score in prose,
  surface a real number for the planets it excludes.) `score` is a
  *valence* judgment and can only ever cover the 7 bodies with an
  agreed classical/modern +/- (Ptolemy's Tetrabiblos names Venus/
  Jupiter benefic, Saturn/Mars malefic; Sun/Moon get a mild modern-
  popular +1 baked into this codebase already). Mercury is classically
  "common" (takes the nature of whatever it touches — never a fixed
  sign) and Uranus/Neptune/Pluto are modern (post-1781) additions with
  no agreed valence at all — inventing a +/- for them would misrepresent
  a real "no consensus" as a citation, so don't. Instead call
  `astrocartography.total_significance(result)` (or read it off
  `score_explanation()["total_significance"]`, already wired in) — an
  unsigned, angle/orb-weighted sum across ALL 10 bodies. Report both
  numbers side by side. Concrete case that motivated this: Girona (this
  session) scores only +0.74 (weak Sun-Desc is the only classically
  scored contact) but has `total_significance` **3.58** — higher than
  Warsaw's 3.1 (score +5.72) — because Girona's Uranus-MC (0.37°) and
  Mercury-Desc (0.35°) are both razor-tight, just unscored. Without
  `total_significance` visible, a reader would wrongly conclude Girona
  is "quieter" than Warsaw; it isn't, it's just quiet in the specific
  classical-valence sense.
- **When the client is comparing "where to live" vs "where to work" —
  or asks about several candidate cities together — split by axis, not
  just by score.** (owner feedback, 2026-07-08: comparing Girona/
  Blanes/Barcelona against Brno/Ostrava/Plzeň for "live vs work"
  surfaced that a city's whole signal can sit on ONE life axis, which a
  single ranked list completely hides.) Call
  `astrocartography.home_vs_work_focus(result)` per candidate — it
  splits `total_significance` into a home axis (IC/Asc: houses 4/1) and
  a work axis (MC/Desc: houses 10/7) and returns a plain verdict ("work
  zone" / "home zone" / "mixed" / "quiet on both"). Concrete case: in
  the same session, Girona/Blanes/Barcelona carried ALL their
  significance on the work axis (Uranus-MC, Mercury-Desc, Sun-Desc) and
  literally 0 on the home axis, while Brno/Ostrava were the mirror
  image (Moon-Asc, Venus-IC, Mars-IC; 0 on the work axis) — so "which
  city is best" doesn't even have one answer; it's two different
  answers to two different questions. Whenever a report ranks or
  compares ≥2 cities, show the axis split, not just the composite score.
- Every PDF ends with the standard disclaimer block (reflective /
  entertainment; not medical, psychological, legal or financial
  advice; birth-time sensitivity).

## Tools used

Primary (house rule — skills consume MCP, not service classes):
`mcp__oneiro__calculate_natal_chart`, `mcp__oneiro__compare_relocations`,
`mcp__oneiro__scan_cities_by_theme`, `mcp__oneiro__compute_transits`,
`mcp__oneiro__transit_arc`, `mcp__oneiro__solar_return_suggest`,
`mcp__oneiro__synastry`, plus `mcp__oneiro__validate_birth_data` /
`mcp__oneiro__search_city` for input validation.

Fallback (bare repo checkout where the MCP server is not connected —
e.g. Claude Code on the web): direct imports from
`backend.services.astrology` (`historic_tz`, `astrocartography`,
`transits_engine`, `transit_arcs`, `solar_return`, `synastry`,
`report`) — the exact modules the MCP tools wrap.

Presentation layer (both modes): matplotlib for the map; Chromium at
`$PLAYWRIGHT_BROWSERS_PATH/chromium-*/chrome-linux/chrome` for the PDF;
without either, deliver `report.render_html` output (or the `/report`
HTTP endpoint's HTML) instead.

## PDF structure (keep this order)

1. Header: name-free label, birth data, resolved tz + source.
1b. «Как читать этот отчёт»: compact glossary box (angles, aspects,
   🟢/🔴, ✅/⚠️ flags, one line per theme) — see the jargon rule above.
2. «Личность — полный портрет»: one-sentence essence, placements
   table, strengths, challenges (Луна/ASC/MC first, then aspects; call
   out grand trines/stelliums explicitly).
3. «Родной город» and «Где живёт сейчас»: angles + summary pill each.
4. «Города по темам»: one table per theme, clean/mixed tags, 4–6 rows.
5. «Год по месяцам»: table with 🟢/🔴, bold the best window and the
   care-window; add the thematic arc if an acute topic exists.
6. «Solar Return»: angular planets of the year + where-to-celebrate
   verdict (often: «дома — отлично», when true).
7. «Итог простыми словами»: 4–6 bullet pill.
8. Embedded map, then the disclaimer block.

## Closing step

Send the PDF (+ map PNG) as attachments with a 2–3 sentence caption.
In chat, summarize the 3 most interesting findings. If this was the
session's substantial task, append a line to `docs/soul.md §9`.
