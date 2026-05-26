"""MCP server smoke tests.

Verifies tools register correctly and pure tools (no LLM, no network) return
sensible data. LLM-bound tools (`calculate_natal_chart`, `generate_horoscope`,
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
        "generate_horoscope",
        "forecast_event",
        "list_event_types",
        "list_horoscope_periods",
        # dreams
        "analyze_dream",
        "list_dream_symbols",
        "list_archetypes",
        "list_hvdc_categories",
        # lunar
        "get_lunar_day",
        "get_lunar_period",
        # geo
        "search_city",
        "validate_birth_data",
    }
    tools = await mcp.list_tools()
    registered = {t.name for t in tools}
    missing = expected - registered
    assert not missing, f"Missing MCP tools: {missing}"


def test_list_event_types_returns_known_set():
    from backend.mcp.tools.astrology import list_event_types

    types = list_event_types()
    assert "wedding" in types
    assert "interview" in types
    assert len(types) >= 5


def test_list_horoscope_periods():
    from backend.mcp.tools.astrology import list_horoscope_periods

    assert set(list_horoscope_periods()) == {"daily", "weekly", "monthly", "yearly"}


def test_list_archetypes():
    from backend.mcp.tools.dreams import list_archetypes

    archetypes = list_archetypes()
    assert "shadow" in archetypes
    assert "self" in archetypes


def test_list_hvdc_categories():
    from backend.mcp.tools.dreams import list_hvdc_categories

    cats = list_hvdc_categories()
    assert "characters" in cats
    assert "emotions" in cats


def test_get_lunar_day_returns_provenance():
    """Lunar tools must work fully offline (Moshier fallback) and include provenance."""
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

    rows = get_lunar_period(
        "2026-05-26", "2026-05-28", timezone="UTC", include_content=False
    )
    assert len(rows) == 3
    assert all("lunar_day" in r and "date" in r for r in rows)
