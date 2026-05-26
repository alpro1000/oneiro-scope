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
- `search_city(query)` — GeoNames + 90-city fallback
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
