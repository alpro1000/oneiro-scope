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

from backend.mcp.tools import archetypes as ar
from backend.mcp.tools import astrology as a
from backend.mcp.tools import dreams as d
from backend.mcp.tools import geo as g
from backend.mcp.tools import lunar as l
from backend.mcp.tools import physiognomy as ph
from backend.mcp.tools import strategic_astro as sa
from backend.mcp.tools import strategic_patterns as sp

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
mcp.tool()(with_meta(a.calculate_natal_chart))
mcp.tool()(with_meta(a.generate_horoscope))
mcp.tool()(with_meta(a.forecast_event))
mcp.tool()(with_meta(a.horoscope_report))
mcp.tool()(with_meta(a.profile_report_file))
mcp.tool()(with_meta(a.list_event_types))
mcp.tool()(with_meta(a.list_horoscope_periods))

# --- Dreams ------------------------------------------------------------------
mcp.tool()(with_meta(d.analyze_dream))
mcp.tool()(with_meta(d.dream_series_stats))
mcp.tool()(with_meta(d.list_dream_symbols))
mcp.tool()(with_meta(d.list_archetypes))
mcp.tool()(with_meta(d.list_hvdc_categories))

# --- Lunar -------------------------------------------------------------------
mcp.tool()(with_meta(l.get_lunar_day))
mcp.tool()(with_meta(l.get_lunar_period))

# --- Geo ---------------------------------------------------------------------
mcp.tool()(with_meta(g.search_city))
mcp.tool()(with_meta(g.validate_birth_data))

# --- Strategic astronomy (Phase 7) -------------------------------------------
# Deterministic chart geometry that the Strategic Life Cycle Analyst agent
# cites as ASTRONOMY-layer evidence. Output is data, not interpretation.
mcp.tool()(with_meta(sa.compute_transits))
mcp.tool()(with_meta(sa.astrocartography_scan))
mcp.tool()(with_meta(sa.astrocartography_lines))
mcp.tool()(with_meta(sa.astrocartography_point))
mcp.tool()(with_meta(sa.solar_return_chart))

# --- Pattern features (Phase 9: session-retrospective) -----------------------
# Side-by-side relocation, thematic city ranking with clean-luck flags,
# thematic transit arcs (pressure/support phases), synastry, and Solar
# Return location suggestions.
mcp.tool()(with_meta(sa.compare_relocations))
mcp.tool()(with_meta(sa.scan_cities_by_theme))
mcp.tool()(with_meta(sa.transit_arc))
mcp.tool()(with_meta(sa.synastry))
mcp.tool()(with_meta(sa.solar_return_suggest))

# --- Archetypes (Phase 8) ----------------------------------------------------
# Hard-table interpretations (MC/Sun/Houses/Aspects/Dignities) with cited
# classical/modern sources. Layer = astrology_symbolic; confidence 0.9 —
# above LLM narrative (0.7), below astronomy (1.0).
mcp.tool()(with_meta(ar.mc_in_sign))
mcp.tool()(with_meta(ar.sun_in_sign))
mcp.tool()(with_meta(ar.house_meaning))
mcp.tool()(with_meta(ar.planet_in_house))
mcp.tool()(with_meta(ar.transit_meaning))
mcp.tool()(with_meta(ar.aspect_meaning))
mcp.tool()(with_meta(ar.planet_dignity))
mcp.tool()(with_meta(ar.zodiac_sign))
mcp.tool()(with_meta(ar.list_archetype_topics))

# --- Analysis patterns (Phase 10: patterns catalog) ---------------------------
# One tool per pattern in strategic/knowledge_base/analysis_patterns.json.
# Deterministic data + catalog ref; the paired skill interprets, labelled.
# analysis_plan is the entry point: it tells the model what can be computed
# and in which order, so nothing gets forgotten in a reading.
mcp.tool()(with_meta(sp.analysis_plan))
mcp.tool()(with_meta(sp.money_contour))
mcp.tool()(with_meta(sp.vocation_map))
mcp.tool()(with_meta(sp.decade_map))
mcp.tool()(with_meta(sp.life_pivots))
mcp.tool()(with_meta(sp.electional_day))
mcp.tool()(with_meta(sp.reverse_physiognomy_prompt))

# --- Physiognomy (reflective face reading) -----------------------------------
# Deterministic FaceMesh geometry (1.0) + cited tradition dictionary (0.6 —
# own tier BELOW symbol dictionaries: physiognomy is not scientifically
# validated). Self-reflection only; disclaimer in every response/report.
mcp.tool()(with_meta(ph.analyze_face))
mcp.tool()(with_meta(ph.analyze_face_archive))
mcp.tool()(with_meta(ph.physiognomy_report))
mcp.tool()(with_meta(ph.physiognomy_methods))
mcp.tool()(with_meta(ph.physiognomy_timeline))


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
