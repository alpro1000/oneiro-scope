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

from backend.mcp.tools._meta import with_meta

from backend.mcp.tools import astrology as a
from backend.mcp.tools import dreams as d
from backend.mcp.tools import geo as g
from backend.mcp.tools import lookup as lk
from backend.mcp.tools import lunar as l
from backend.mcp.tools import strategic_astro as sa
from backend.mcp.tools import strategic_patterns as sp

logger = logging.getLogger("oneiro.mcp")

# WP-1 startup verification: importing the config verifies the .se1 files
# (or raises, refusing to start the server) and pins SWIEPH globally.
from backend.core.ephemeris import startup_summary as _ephemeris_summary

logger.info("Ephemeris: %s", _ephemeris_summary())

mcp = FastMCP(
    "oneiro-scope",
    instructions=(
        "OneiroScope MCP server. Tools for science-grounded astrology "
        "(Swiss Ephemeris natal charts, horoscopes, event forecasts), "
        "dream analysis (Hall/Van de Castle + Jungian archetypes + REM/NREM + "
        "DreamBank norms), and lunar calendar. Geocoding via GeoNames. All "
        "interpretations are bilingual (ru/en) and traced to data — never "
        "invented. Use `validate_birth_data` before `calculate_natal_chart` "
        "to save LLM cost. Use `search_city` for autocomplete-style lookups. "
        "Knowledge-base reads (sign/house/aspect/dignity meanings, symbol "
        "and category lists) live behind the single `lookup` tool."
    ),
)

# WP-10: the surface is deliberately small. 47 tools drowned the ones that
# compute something over a person; the registry now carries the working set
# and ONE folded reference lookup. Removed families (physiognomy, file
# reports, generate_horoscope, per-key archetype lookups, decade/electional
# extras) keep their module code for the web API — they are just no longer
# MCP tools. Every stage in analysis_plan.STAGES must name a tool from this
# registry; tests enforce the sync in both directions.

# --- Astrology ---------------------------------------------------------------
mcp.tool()(with_meta(a.calculate_natal_chart))
mcp.tool()(with_meta(a.forecast_event))

# --- Dreams ------------------------------------------------------------------
mcp.tool()(with_meta(d.analyze_dream))
mcp.tool()(with_meta(d.dream_series_stats))

# --- Lunar -------------------------------------------------------------------
mcp.tool()(with_meta(l.get_lunar_day))
mcp.tool()(with_meta(l.get_lunar_period))

# --- Geo (the natal chain's input control) -----------------------------------
mcp.tool()(with_meta(g.search_city))
mcp.tool()(with_meta(g.validate_birth_data))

# --- Strategic astronomy: timing and place -----------------------------------
# Deterministic chart geometry cited as ASTRONOMY-layer evidence.
mcp.tool()(with_meta(sa.compute_transits))
mcp.tool()(with_meta(sa.astrocartography_scan))
mcp.tool()(with_meta(sa.astrocartography_lines))
mcp.tool()(with_meta(sa.astrocartography_point))
mcp.tool()(with_meta(sa.compare_relocations))
mcp.tool()(with_meta(sa.solar_return_chart))
mcp.tool()(with_meta(sa.solar_return_suggest))

# --- Analysis patterns -------------------------------------------------------
# analysis_plan is the entry point: what can be computed, in which order.
mcp.tool()(with_meta(sp.analysis_plan))
mcp.tool()(with_meta(sp.money_contour))
mcp.tool()(with_meta(sp.vocation_map))

# --- Reference lookups, folded into one tool (WP-10) --------------------------
mcp.tool()(with_meta(lk.lookup))


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
