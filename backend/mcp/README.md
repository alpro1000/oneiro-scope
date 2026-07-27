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
  "domain": "astro",                 // "astro" = chart + face; "dreams" is separate
  "hint": "…call the tool you need. Full ordered plan: analysis_plan.",
  "ready":       [ {"name", "tool", "answers", "track"} ],   // inputs satisfied — one call away
  "needs_input": [ {"name", "tool", "missing"} ],            // terser: exists, and wants X
  "questions_to_ask": ["Which cities should we compare?"],
  "reference_lookups": ["house_meaning", "planet_dignity", …],
  "full_plan_tool": "analysis_plan"
}
```

Offered, not run. A decade map scans ten years at a 10-day step, a city scan
runs a whole pool, and a Solar Return suggestion computes one return per
candidate city — firing all of it on every call would spend minutes and quota
answering a question nobody asked. The menu costs ~3.5 KB and lists only what
is already runnable, so the next call is one step away.

Two domains, per the product split: **astro** covers chart *and* face (both
read one standing person from static data), **dreams** is per-episode and
shares no inputs with them. Dictionary lookups (`house_meaning`,
`list_dream_symbols`, …) carry no menu of their own — they are not steps in a
reading. `get_lunar_period` also has none: it returns a bare list, and wrapping
a documented list shape in a dict to add a hint would break callers.

`backend/tests/test_capability_menu.py` holds the drift guards — every stage
tool attaches a menu, marks its own stage completed, and names a registered
tool.

## Available tools

### Astrology
- `calculate_natal_chart(birth_date, birth_place, birth_time?, locale)`
- `generate_horoscope(period, target_date?, locale, natal_chart_id?)`
- `forecast_event(event_type, event_date, event_location?, event_description?, locale, natal_chart_id?)`
- `list_event_types()` — pure
- `list_horoscope_periods()` — pure

### Dreams
- `analyze_dream(dream_text, dream_date?, dreamer_gender?, dreamer_age_group?, locale)`
- `list_dream_symbols(locale)` — pure
- `list_archetypes()` — pure
- `list_hvdc_categories()` — pure

### Lunar
- `get_lunar_day(target_date, timezone?, locale)` — pure
- `get_lunar_period(start_date, end_date, timezone?, locale, include_content?)` — pure

### Geo
- `search_city(query)` — GeoNames + small curated offline fallback; returns `candidates` + `ambiguous`/`name_matched` flags
- `validate_birth_data(birth_date, birth_place, birth_time?)` — validates before paying LLM cost

## Configuration

Reads the same env vars as the backend service:

- `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `TOGETHER_API_KEY` — at least one for LLM-using tools (natal chart,
  horoscope, dream analyze). Falls back to template interpretations if none.
- `GEONAMES_USERNAME` — for `search_city` and birth-place geocoding.
- `LUNAR_DEFAULT_TZ` — default timezone for lunar tools (e.g. `Europe/Moscow`).
- `SE_EPHE_PATH` — optional path to Swiss Ephemeris binaries (falls back to
  Moshier analytic).

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
