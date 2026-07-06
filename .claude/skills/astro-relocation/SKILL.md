# /astro-relocation — Astrogeography & relocation deep-dive

> **English TL;DR:** Reusable playbook for the full relocation
> consult refined live with the owner (2026-07-06 session): city
> angle reads, themed scans, the pan-continental MC-line hunt,
> Solar-Return location comparison, retro-transit verification
> against real life events, and the timing windows that gate every
> "when should I act" answer. Written so a smaller/cheaper model can
> execute it without rediscovering the module APIs or the honesty
> rules — everything hard-won is encoded below.

## When to use

User asks any of: "разбери мою астрогеографию", "какие города мне
подходят", "город A или город B", "где карьера / где бизнес",
"что изменил соляр в месте X", "что было в прошлом году (событие
Y — было ли видно по транзитам)", "когда переезжать / когда
действовать". Birth data required once (date, time, place); reuse
for the whole conversation.

## Environment bootstrap (fallback mode, no MCP)

If `mcp__oneiro__*` tools are absent (bare web checkout), use direct
imports. One-time setup:

```bash
python3 -m venv $SCRATCHPAD/venv
source $SCRATCHPAD/venv/bin/activate
pip install -q pydantic pydantic-settings pyswisseph matplotlib \
    httpx jinja2 pytz timezonefinder geopy
export PYTHONPATH=<repo root>   # scripts must run with repo root on path
```

MOSEPH warning about missing `seas_18.se1` is expected and harmless
(analytic ephemeris, still <1″ for the classical bodies).

## Module API cheat-sheet (exact signatures — do not guess)

```python
from datetime import date, time, datetime
from backend.services.astrology.historic_tz import resolve_birth_moment
from backend.services.astrology import astrocartography as acg
from backend.services.astrology import report as report_mod
from backend.services.astrology.transits_engine import find_transits
from backend.services.astrology import transit_arcs, solar_return as sr
from backend.services.astrology.natal_chart import NatalChartCalculator
from backend.services.astrology.ephemeris import SwissEphemeris
import swisseph as swe

m  = resolve_birth_moment(date(Y,M,D), time(h,mm), lat=LAT, lon=LON)
jd = m.jd_ut                     # NEVER hand-compute tz; USSR = decree time

# City angles (input order preserved; summary carries the clean flag):
acg.compare_locations(jd, [(name,lat,lon),...], locale="ru", orb_deg=8.0)

# Themed ranking (theme ∈ luck|career|relationships|home; only
# qualifying cities are returned — absence IS the finding):
acg.theme_scan(jd, pool, theme, top_n=10)      # pool += report_mod.DEFAULT_CITIES

# Line map (GeoJSON; matplotlib for the regional PNG):
acg.acg_lines(jd, lat_min=35, lat_max=62, step=0.5)

# Transits & phase arcs:
find_transits(jd, start_date, end_date, orb_deg=1.0)   # filter slow: Jup..Pluto
transit_arcs.compute_arc(jd, lat, lon, theme, start, end, orb_deg=1.2)
#   theme ∈ money_debt|career|relationships|home; .phases / .turning_point

# Solar Return + location comparison:
sr.solar_return(jd, YEAR, lat, lon)            # planets same, houses shift
sr.suggest_locations(jd, YEAR, candidates)
# per-house detail for a custom place: swe.houses(sr_jd, lat, lon, b"P")

# Natal placements/aspects for the personality layer:
calc = NatalChartCalculator(SwissEphemeris())  # ctor REQUIRES ephemeris arg
dtu  = datetime.fromisoformat(m.utc_iso)
pl   = calc.calculate_planets(dtu, LAT, LON, "UTC")
hs   = calc.calculate_houses(dtu, LAT, LON, "UTC")
pl   = calc.assign_planets_to_houses(pl, hs)
asp  = calc.calculate_aspects(pl)
```

## The ten canonical requests → exact recipe

1. **"Разбери астрогеографию + когда переезжать"** — birth moment →
   natal portrait (lead with the dominant axis, e.g. Sun–Moon
   opposition = home-vs-career) → `compare_locations` for birth city
   + every city the user names → year of slow transits grouped into
   act/consolidate/rest windows → regional line map PNG.
2. **"Города страны X"** — 8–15 cities of that country through
   `compare_locations` (orb 10 to catch near-misses) + check every
   theme via `theme_scan` with the full pool so ranks are global,
   not local. Report the gradient (e.g. Czechia: Moravia > Bohemia).
3. **"A или B"** — `compare_locations` on just the two, orb 10–12;
   name what each pole serves (home-pole vs work-pole), map to the
   natal axis, end with a question about the user's current priority.
4. **"Что было в прошлом году"** — `find_transits` over the window,
   plus ALL-planet pass at orb 2.0 around the named event month
   (fast planets time events; slow planets set the season). Then the
   Solar Return AT the city where they actually lived. Match events
   to houses honestly; if nothing matches, say so.
5. **"Что изменил соляр в месте X"** — same SR moment, two `swe.houses`
   calls (actual city vs counterfactual home city); diff the house
   placements. Usually only 1–2 planets shift house — say that
   plainly instead of overselling relocation SR magic.
6. **"Призвание"** — MC sign + 10th-house occupants + their tightest
   aspects; 6th/8th/12th house story; nodes. Synthesize into 2–3
   concrete work-format recommendations, not trait lists.
7. **"Где карьера / где бизнес (весь континент)"** — build a 100+
   city pool, run `compare_locations`, then filter `angle=="MC"`
   hits explicitly. Report which PLANET owns the MC line: for this
   chart class, no Sun/Saturn/Jupiter-MC anywhere = "no employment
   line, only an independence (Uranus) line" — that asymmetry IS the
   answer.
8. **"Таймлайн на N лет"** — `compute_arc` for the 1–2 themes the
   user actually has open; render a month table with 🟢/🔴, bold the best
   window and the care-window; pressure ≠ stop-working, it means
   don't-expand (say this explicitly — users mishear it).
9. **"Сколько копить / хватит ли на дом"** — NOT a chart question.
   Web-search real prices, build the deposit table (non-resident
   mortgage ≈ 60–70 % LTV), show months-to-goal at 3–4 saving rates,
   ask for the user's real numbers. Chart only supplies the timing
   windows.
10. **"Как начать практику"** — business-format advice anchored to
    the natal signature (e.g. Uranus-8 trine Sun → productized
    expertise, not hourly billing) + the transit windows for each
    step. Deterministic astronomy first, career advice second,
    clearly separated.

## Honesty rules (non-negotiable, verified against live session)

- **Never hide malefics.** Venus-IC with Mars-IC 0.8° nearby is
  "⚠️ с минусом", full stop. The `clean` flag decides.
- **Neutral ≠ blocked.** No MC hit means "no boost", never "you
  can't earn here". Users conflate these — pre-empt it.
- **Lines need physical presence.** ACG lines describe where the
  body is, not where the clients are. Remote work for a market ≠
  activating that market's line. Do not blur these two layers (a
  live correction from this session — the user caught it).
- **Life context beats geometry.** War, market size, visa, commute
  to a fixed office — if they contradict the chart read, they win
  and you say so.
- **Natal is portable.** A tight natal angularity at the birthplace
  (e.g. Saturn-Desc) travels with the person; the birthplace only
  shows it undiluted. Don't let users blame the city for the chart.
- No determinism language; every reply ends with the standard
  reflective/entertainment disclaimer incl. birth-time sensitivity.

## Output shape

Lead with the single most decision-relevant finding (not a section
list). Tables for city comparisons (Score · clean? · hits with orbs).
Month tables for timing. One regional map PNG via SendUserFile when
geography is the question. Russian by default; mirror the user.
