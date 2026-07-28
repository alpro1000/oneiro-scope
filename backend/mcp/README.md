# OneiroScope MCP Server

Canonical tool surface for the OneiroScope domain (astrology, dreams, lunar,
geo). Wraps `backend/services/*` in-process — no HTTP hop to the FastAPI app.

## Why MCP?

Skills (`.claude/skills/*`) and the ADK agent (`agents/oneiro_agent.py`)
consume **MCP tools**, not FastAPI HTTP. This keeps one set of contracts and
one cost-tracking boundary, and lets external clients (Claude Desktop,
Cursor, custom agents) reuse the same tools.

## Install

The server uses the official Python `mcp` SDK:

```bash
pip install "mcp[cli]>=1.2"
```

The rest is the existing backend (`backend/requirements.txt`).

## Run

```bash
# stdio transport (Claude Desktop, Cursor, local agents)
python -m backend.mcp.server

# streamable-HTTP transport (remote agents, web clients)
python -m backend.mcp.server --http --port 8765
```

## Every response offers the rest of the surface

A client that lands on one tool used to see only that tool: nothing told it the
same birth data also buys a money contour, a decade map, a city scan or a Solar
Return. `analysis_plan` answered that from the start, but only when the model
thought to ask, and it usually did not. So every substantive response now
carries a `can_also_compute` block:

```jsonc
"can_also_compute": {
  "next": ["money_contour", "vocation_map", "compute_transits"],  // ≤3 ready tools, stage order
  "full_plan_tool": "analysis_plan"
}
```

Compact since WP-11: the first version attached the full ready/blocked/
questions structure and a live audit measured ~90k chars of menu across one
conversation. The block is now ≤200 chars (test-enforced); the ordered plan,
blocked steps and their questions live one call away in `analysis_plan`.
`next` lists only steps whose inputs the calling tool already had.

Two domains, per the product split: **astro** reads one standing person from
static data, **dreams** is per-episode and shares no inputs with it. The
`lookup` reference tool carries no menu — a dictionary read is not a step in
a reading. `get_lunar_period` also has none: it returns a bare list, and
wrapping a documented list shape in a dict to add a hint would break callers.

`depends_on` is a **soft** ordering hint, the same as in `build_plan`: each tool
recomputes the chart geometry it needs, so a stage runs fine before its
prerequisite — reading it first is merely confusing. Such a step stays in
`ready` and carries `better_after: ["natal-chart"]`. A tool reports **only its
own** stage as completed: it knows that it ran, it does not know what else the
session ran.

`backend/tests/test_capability_menu.py` holds the drift guards — every stage
tool attaches a menu, marks only its own stage completed, names a registered
tool, and every step offered as `ready` is verified callable with nothing
further supplied.

## Available tools (19 — WP-10 cut the surface from 47)

### Astrology
- `calculate_natal_chart(birth_date, birth_place, birth_time?, locale, latitude?, longitude?, timezone_name?)`
- `forecast_event(event_type, event_date, event_location?, event_description?, locale, natal_chart_id?)`

### Dreams
- `analyze_dream(dream_text, dream_date?, dreamer_gender?, dreamer_age_group?, locale)`
- `dream_series_stats(user_id, locale)` — personal baseline over a stored series (N≥15)

### Lunar
- `get_lunar_day(target_date?, timezone?, locale)` — pure
- `get_lunar_period(start_date, end_date, timezone?, locale, include_content?)` — pure

### Geo
- `search_city(query)` — GeoNames + small curated offline fallback; returns `candidates` + `ambiguous`/`name_matched` flags
- `validate_birth_data(birth_date, birth_place, birth_time?)` — validates before paying LLM cost

### Strategic astronomy (timing and place)
- `compute_transits(birth…, start, end, orb_deg?)`
- `astrocartography_scan(birth…, cities, orb_deg?)` · `astrocartography_lines(birth…)` · `astrocartography_point(birth…, lat, lon)`
- `compare_relocations(birth…, cities)`
- `solar_return_chart(birth…, return_year, location)` · `solar_return_suggest(birth…, cities)`

### Analysis patterns
- `analysis_plan(known_inputs?, completed?, locale)` — the ordered plan; entry point
- `money_contour(birth…)` · `vocation_map(birth…)`

### Reference lookups (folded, WP-10)
- `lookup(topic, …)` — one dispatcher for all KB reads: zodiac_sign, sun_in_sign,
  mc_in_sign, house_meaning, planet_in_house, planet_dignity, aspect_meaning,
  transit_meaning, archetype_topics, event_types, horoscope_periods,
  dream_symbols, dream_archetypes, hvdc_categories

Removed from MCP in WP-8/WP-10 (module code remains for the web API):
`generate_horoscope`, file reports (`horoscope_report`, `profile_report_file`,
`physiognomy_report`), the physiognomy family, `synastry`, `transit_arc`,
`scan_cities_by_theme`, `decade_map`, `life_pivots`, `electional_day`, and the
fifteen single-purpose lookup tools now behind `lookup`.

## Configuration

Reads the same env vars as the backend service:

- `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `TOGETHER_API_KEY` — at least one for LLM-using tools (natal chart,
  horoscope, dream analyze). Falls back to template interpretations if none.
- `GEONAMES_USERNAME` — for `search_city` and birth-place geocoding.
- `LUNAR_DEFAULT_TZ` — default timezone for lunar tools (e.g. `Europe/Moscow`).
- `SE_EPHE_PATH` — optional override for the Swiss Ephemeris binaries; the
  repo ships them in `backend/data/ephemeris/` and the server refuses to
  start when the required `.se1` files are missing (no analytic fallback).

## Wiring into Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "oneiro-scope": {
      "command": "python",
      "args": ["-m", "backend.mcp.server"],
      "cwd": "/absolute/path/to/oneiro-scope",
      "env": {
        "GROQ_API_KEY": "...",
        "GEONAMES_USERNAME": "alpro1000",
        "LUNAR_DEFAULT_TZ": "Europe/Moscow"
      }
    }
  }
}
```

## Smoke test

```bash
pytest backend/tests/test_mcp_smoke.py -v
```

Verifies all tools are registered and pure tools return data without hitting
LLM/network.
