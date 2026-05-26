"""OneiroScope MCP server entry point.

Registers all tools and runs the server. Supports stdio (default) for local
clients (Claude Desktop, Cursor) and streamable-HTTP for remote agents.

Run:
    python -m backend.mcp.server                    # stdio
    python -m backend.mcp.server --http             # HTTP on :8765
    python -m backend.mcp.server --http --port 9000

Dependencies:
    pip install "mcp[cli]>=1.2"
"""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

from backend.mcp.tools import astrology as a
from backend.mcp.tools import dreams as d
from backend.mcp.tools import geo as g
from backend.mcp.tools import lunar as l

logger = logging.getLogger("oneiro.mcp")

mcp = FastMCP(
    "oneiro-scope",
    instructions=(
        "OneiroScope MCP server. Tools for science-grounded astrology "
        "(Swiss Ephemeris natal charts, horoscopes, event forecasts), "
        "dream analysis (Hall/Van de Castle + Jungian archetypes + REM/NREM + "
        "DreamBank norms), and lunar calendar. Geocoding via GeoNames. All "
        "interpretations are bilingual (ru/en) and traced to data — never "
        "invented. Use `validate_birth_data` before `calculate_natal_chart` "
        "to save LLM cost. Use `search_city` for autocomplete-style lookups."
    ),
)

# --- Astrology ---------------------------------------------------------------
mcp.tool()(a.calculate_natal_chart)
mcp.tool()(a.generate_horoscope)
mcp.tool()(a.forecast_event)
mcp.tool()(a.list_event_types)
mcp.tool()(a.list_horoscope_periods)

# --- Dreams ------------------------------------------------------------------
mcp.tool()(d.analyze_dream)
mcp.tool()(d.list_dream_symbols)
mcp.tool()(d.list_archetypes)
mcp.tool()(d.list_hvdc_categories)

# --- Lunar -------------------------------------------------------------------
mcp.tool()(l.get_lunar_day)
mcp.tool()(l.get_lunar_period)

# --- Geo ---------------------------------------------------------------------
mcp.tool()(g.search_city)
mcp.tool()(g.validate_birth_data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OneiroScope MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run streamable-HTTP transport instead of stdio.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP bind host (default 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="HTTP port (default 8765).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        logger.info(
            "Starting OneiroScope MCP (streamable-http) on %s:%d",
            args.host,
            args.port,
        )
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting OneiroScope MCP (stdio)")
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
