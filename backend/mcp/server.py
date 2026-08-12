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
from mcp.types import ToolAnnotations

from backend.mcp import apps
from backend.mcp.tools._meta import with_meta

from backend.mcp.tools import astrology as a
from backend.mcp.tools import dreams as d
from backend.mcp.tools import geo as g
from backend.mcp.tools import lookup as lk
from backend.mcp.tools import lunar as l
from backend.mcp.tools import physiognomy as ph
from backend.mcp.tools import strategic_astro as sa
from backend.mcp.tools import strategic_patterns as sp

logger = logging.getLogger("oneiro.mcp")

# WP-1 startup verification: importing the config verifies the .se1 files
# (or raises, refusing to start the server) and pins SWIEPH globally.
from backend.core.ephemeris import startup_summary as _ephemeris_summary
from backend.core.ephemeris import warm_ephemeris as _warm_ephemeris

logger.info("Ephemeris: %s", _ephemeris_summary())
# The stdio server is its own process, so it pays its own page-in cost. Doing
# it here means the first chart a desktop client asks for is fast, not the
# 11-second one production served after every restart.
logger.info("Ephemeris: warmed the chart path in %.0f ms", _warm_ephemeris())

# The instructions used to open with "science-grounded astrology" — an
# overclaim this project's own domain rules forbid, and precisely the kind of
# phrase a directory reviewer reads as misleading. What is defensible, and
# what the code actually enforces, is the split: the astronomy is computed,
# the interpretation is a tradition and says so.
mcp = FastMCP(
    "oneiro-scope",
    instructions=(
        "OneiroScope MCP server: deterministic astronomy and structural "
        "dream analysis, with interpretation as a separate, labelled layer. "
        "Astronomy (Swiss Ephemeris): natal charts with houses and "
        "applying/separating aspects, transits, solar returns, "
        "astrocartography line sets, relocation comparison, lunar calendar. "
        "Dreams: Hall/Van de Castle structural coding where every count "
        "cites the clause it came from, plus DreamBank norm comparison. "
        "Geocoding via GeoNames; bilingual ru/en. Every response carries "
        "provenance and a per-claim confidence: computed 1.0, cited rule "
        "0.9, symbol dictionary 0.8, model synthesis 0.7. Astrology and "
        "dream interpretation are traditions of reading, not sciences; "
        "results are reflective/entertainment material and never medical, "
        "psychological, legal or financial advice — the server refuses "
        "deterministic prediction language. Use `validate_birth_data` "
        "before `calculate_natal_chart`. Use `search_city` for "
        "autocomplete-style lookups. Knowledge-base reads live behind the "
        "single `lookup` tool."
    ),
)

# --- Tool annotations (MCP spec) ----------------------------------------------
# Directory reviews (Claude connectors, ChatGPT apps) read these hints to
# decide how much friction a tool call deserves. They are promises, so they
# are set from what the code does, not from what looks nicest:
#
# - READ: pure computation over the arguments. No state written, no network
#   beyond our own process. Everything ephemeris-shaped is here.
# - GEO: still read-only, but resolves place names through the GeoNames API —
#   an external service, hence openWorldHint.
# - `calculate_natal_chart` is NOT read-only: issuing a chart consumes the
#   free tier's lifetime grant (`mark_chart_issued`). It is idempotent — the
#   same chart re-issues forever without further effect (`same_chart`) — and
#   it geocodes when coordinates are not passed.
# - `analyze_dream` is NOT read-only: `remember=True` appends coded features
#   to the caller's own series. Not idempotent — each call appends.
#
# `test_mcp_moderation.py` asserts every tool carries these and that the two
# writers are the only tools not marked read-only.
READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
GEO_READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
NATAL_WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True,
    openWorldHint=True,
)
DREAM_WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False,
    openWorldHint=False,
)

# WP-10: the surface is deliberately small. 47 tools drowned the ones that
# compute something over a person; the registry now carries the working set
# and ONE folded reference lookup. Removed families (physiognomy, file
# reports, generate_horoscope, per-key archetype lookups, decade/electional
# extras) keep their module code for the web API — they are just no longer
# MCP tools. Every stage in analysis_plan.STAGES must name a tool from this
# registry; tests enforce the sync in both directions.

# --- Interactive views (MCP Apps) --------------------------------------------
# `ui://` resources the host renders in a sandboxed iframe beside the answer.
# Purely additive: hosts without the io.modelcontextprotocol/ui extension
# ignore the metadata and receive the same JSON they always did.
_ui_views = apps.register(mcp)

# --- Astrology ---------------------------------------------------------------
# The natal chart is the one tool whose result is a DRAWING as much as a table,
# so it carries a view. The tool stays visible to the model either way — the
# chart is useful as data even where nothing is rendered.
mcp.tool(
    meta=apps.tool_ui_meta(apps.NATAL_WHEEL) if _ui_views else None,
    annotations=NATAL_WRITE,
)(with_meta(a.calculate_natal_chart))
mcp.tool(annotations=READ)(with_meta(a.forecast_event))

# --- Dreams ------------------------------------------------------------------
# The coding view shows the dream text with each coded clause marked — the one
# place a count and its evidence can be read in a single glance.
mcp.tool(
    meta=apps.tool_ui_meta(apps.DREAM_EVIDENCE) if _ui_views else None,
    annotations=DREAM_WRITE,
)(with_meta(d.analyze_dream))
mcp.tool(annotations=READ)(with_meta(d.dream_series_stats))

# --- Lunar -------------------------------------------------------------------
mcp.tool(annotations=READ)(with_meta(l.get_lunar_day))
mcp.tool(
    meta=apps.tool_ui_meta(apps.LUNAR_MONTH) if _ui_views else None,
    annotations=READ,
)(with_meta(l.get_lunar_period))

# --- Geo (the natal chain's input control) -----------------------------------
mcp.tool(annotations=GEO_READ)(with_meta(g.search_city))
mcp.tool(annotations=GEO_READ)(with_meta(g.validate_birth_data))

# --- Strategic astronomy: timing and place -----------------------------------
# Deterministic chart geometry cited as ASTRONOMY-layer evidence.
mcp.tool(annotations=READ)(with_meta(sa.compute_transits))
mcp.tool(annotations=READ)(with_meta(sa.astrocartography_scan))
# The line set is a MAP; a list of coordinates is not the same object.
mcp.tool(
    meta=apps.tool_ui_meta(apps.ACG_MAP) if _ui_views else None,
    annotations=READ,
)(with_meta(sa.astrocartography_lines))
mcp.tool(annotations=READ)(with_meta(sa.astrocartography_point))
mcp.tool(
    meta=apps.tool_ui_meta(apps.RELOCATIONS) if _ui_views else None,
    annotations=READ,
)(with_meta(sa.compare_relocations))
mcp.tool(annotations=READ)(with_meta(sa.solar_return_chart))
mcp.tool(annotations=READ)(with_meta(sa.solar_return_suggest))

# --- Analysis patterns -------------------------------------------------------
# analysis_plan is the entry point: what can be computed, in which order.
mcp.tool(annotations=READ)(with_meta(sp.analysis_plan))
# Both return the same envelope and the same nested shapes, so they share one
# view rather than two renderers that would need the same bug fixed twice.
mcp.tool(
    meta=apps.tool_ui_meta(apps.PATTERN_MAP) if _ui_views else None,
    annotations=READ,
)(with_meta(sp.money_contour))
mcp.tool(
    meta=apps.tool_ui_meta(apps.PATTERN_MAP) if _ui_views else None,
    annotations=READ,
)(with_meta(sp.vocation_map))

# --- Face reading: built, tested, and deliberately NOT registered -------------
#
# `ph.read_face_traits` is connector-safe (questionnaire only, no photo path,
# no image, no biometric template) and every property that makes it safe is
# pinned by `test_mcp_moderation.py`. It is still not on this surface, and the
# reason is submission risk, not the tool:
#
# a directory reviewer who reads "face reading" in a tool list and closes the
# application without opening the schema rejects THE WHOLE SERVER — all
# nineteen tools, the ephemeris, astrocartography. Two tools that add almost
# nothing to a catalog listing are not worth that trade, especially since the
# funnel that needs face reading lives on the WEB (`/[locale]/face`, the HTTP
# API), which needs no one's approval.
#
# To restore it after the listing is approved: add the two `mcp.tool(...)`
# lines back, put `read_face_traits`/`physiognomy_methods` back into
# `REFERENCE_TOOLS["face"]`, and bump the surface count in the tests that pin
# it. `test_the_face_reading_is_staged_not_shipped` will fail until you delete
# it — deliberately, so the decision is re-read rather than re-guessed. Do NOT
# rename the tool to read as something other than physiognomy: on a re-review
# that scans as an attempt to slip it past, which is worse than the honest
# name. The description already opens with what it is.
#
# Note for whoever does this on the OpenAI side: publishing an updated tool
# list is not free there. The server is re-scanned, the new version goes
# through review, and only the approved version publishes — so plan it as its
# own cycle, not as a push.

# --- Reference lookups, folded into one tool (WP-10) --------------------------
mcp.tool(annotations=READ)(with_meta(lk.lookup))


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
