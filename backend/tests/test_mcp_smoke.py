"""MCP server smoke tests.

Verifies tools register correctly and pure tools (no LLM, no network) return
sensible data. LLM-bound tools (`calculate_natal_chart`,
`analyze_dream`) are intentionally NOT exercised here — they need API keys
and would inflate CI cost.
"""

from __future__ import annotations

import pytest


def test_mcp_module_imports():
    """The MCP server module imports without side effects beyond construction."""
    from backend.mcp import server  # noqa: F401

    assert server.mcp is not None
    assert server.mcp.name == "oneiro-scope"


@pytest.mark.asyncio
async def test_all_tools_registered():
    """Every tool we shipped is present in the server registry."""
    from backend.mcp.server import mcp

    expected = {
        # astrology
        "calculate_natal_chart",
        "forecast_event",
        # dreams
        "analyze_dream",
        "dream_series_stats",
        # lunar
        "get_lunar_day",
        "get_lunar_period",
        # geo
        "search_city",
        "validate_birth_data",
        # strategic astronomy: timing and place
        "compute_transits",
        "astrocartography_scan",
        "astrocartography_lines",
        "astrocartography_point",
        "compare_relocations",
        "solar_return_chart",
        "solar_return_suggest",
        # analysis patterns
        "analysis_plan",
        "money_contour",
        "vocation_map",
        # folded reference lookups (WP-10)
        "lookup",
    }
    tools = await mcp.list_tools()
    registered = {t.name for t in tools}
    # Exact equality in BOTH directions: a missing tool breaks the product,
    # a stray one re-grows the surface WP-10 just cut (47 -> 19).
    assert registered == expected, (
        f"missing: {sorted(expected - registered)}; "
        f"unexpected: {sorted(registered - expected)}"
    )


def test_list_event_types_returns_known_set():
    from backend.mcp.tools.astrology import list_event_types

    types = list_event_types()
    assert "wedding" in types
    assert "interview" in types
    assert len(types) >= 5
    # WP-8: no medical events — a favourability forecast for surgery is
    # medical advice territory, excluded by the disclaimer.
    assert "surgery" not in types


def test_list_horoscope_periods():
    from backend.mcp.tools.astrology import list_horoscope_periods

    assert set(list_horoscope_periods()) == {"daily", "weekly", "monthly", "yearly"}


def test_list_archetypes():
    from backend.mcp.tools.dreams import list_archetypes

    result = list_archetypes()
    assert "shadow" in result["items"]
    assert "self" in result["items"]
    assert result["disclaimer"]


def test_list_hvdc_categories():
    from backend.mcp.tools.dreams import list_hvdc_categories

    result = list_hvdc_categories()
    assert "characters" in result["items"]
    assert "emotions" in result["items"]
    assert result["disclaimer"]


def test_get_lunar_day_returns_provenance():
    """Lunar tools must work fully offline (repo-shipped SWIEPH files) and include provenance."""
    from backend.mcp.tools.lunar import get_lunar_day

    info = get_lunar_day("2026-05-26", timezone="UTC", locale="en")
    assert "lunar_day" in info
    assert "phase" in info
    assert "provenance" in info
    assert 1 <= info["lunar_day"] <= 30


def test_get_lunar_period_caps_length():
    from backend.mcp.tools.lunar import get_lunar_period

    with pytest.raises(ValueError):
        get_lunar_period("2026-01-01", "2026-06-01", timezone="UTC")


def test_get_lunar_period_short_range():
    from backend.mcp.tools.lunar import get_lunar_period

    out = get_lunar_period(
        "2026-05-26", "2026-05-28", timezone="UTC", include_content=False
    )
    # Dict envelope since the Qodo round: a bare list could not carry the
    # WP-6 meta block or the capability menu.
    rows = out["days"]
    assert out["count"] == 3
    assert len(rows) == 3
    assert all("lunar_day" in r and "date" in r for r in rows)
