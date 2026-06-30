# Interactive Astrocartography

Relocation / Astro\*Carto\*Graphy feature: a user enters birth data, sees their
planetary **lines** on a world map, and can **click any point** to get the four
relocated angles (Asc/MC/IC/Desc), the natal planets sitting on them, and a
plain-language "good to work / hard to live" summary. The birth city is marked.

Deterministic-first per project rules: **angle geometry is astronomy**
(Swiss Ephemeris, confidence 1.0); the work/life **summary is a rule-based
reflection** (confidence 0.8) — never a prediction. Every response carries a
disclaimer.

## Backend

`backend/services/astrology/astrocartography.py`
- `chart_geometry(jd, lat, lon, name)` — compact payload (sidereal time,
  obliquity, each body's ecliptic longitude + RA/Dec, birth point). A thin
  client can compute the four angles for any location from this alone — no
  ephemeris needed client-side.
- `acg_lines(jd)` — GeoJSON `FeatureCollection` of every planet's MC/IC
  meridians and Asc/Desc horizon curves (coordinates `[lon, lat]`, curves
  split at the antimeridian).
- `relocation_summary(result, locale)` — reflective work/home/relationship/
  tension buckets + a one-line plain verdict (ru/en).

## HTTP API (`/api/v1/astrology`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/astrocartography/chart` | Lines (GeoJSON) + chart payload for the map |
| POST | `/astrocartography/point` | Four angles + contacts + plain summary for one clicked location |

Request body (both): `birth_date`, optional `birth_time` (noon if omitted),
`birth_timezone` (IANA), `birth_lat`, `birth_lon`, optional `birth_place`.
`/point` additionally needs `lat`, `lon`, and `locale` (`ru`/`en`).

## MCP tools (for agents / skills)

`backend/mcp/tools/strategic_astro.py`
- `astrocartography_lines` — lines + chart payload (ASTRONOMY layer).
- `astrocartography_point` — angles + contacts + reflective summary.

Registered in `backend/mcp/server.py`; covered by
`backend/tests/test_strategic_astro_tools.py`.

## Frontend

`frontend/public/astrocartography.html` — a self-contained, responsive
(desktop + mobile) Leaflet map. Works offline against the built-in default
chart; enter an API base URL to build the map from custom birth data via
`/astrocartography/chart`. Angle math is computed client-side and is
verified against the backend `relocate()` to the arc-minute.

Verification: pure-trig browser angle formulas reproduce `relocate()` (Placidus)
exactly for Brno / Barcelona / Zaporizhzhia (ASC and MC match to the arc-minute).
