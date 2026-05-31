"""ADK agent smoke tests.

We do NOT exercise the Claude API here — that requires credentials and
network. We only verify the agent module imports, the system prompt is
non-trivial, and the MCP server config wires to a real Python module.
"""

from __future__ import annotations

import importlib

import pytest


def test_agent_module_imports():
    mod = importlib.import_module("agents.oneiro_agent")
    assert hasattr(mod, "OneiroAgent")


def test_system_prompt_present_and_non_trivial():
    from agents.oneiro_agent import _SYSTEM_PROMPT_PATH

    text = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    assert len(text) > 800
    assert "OneiroScope" in text
    assert "natal" in text.lower()
    assert "dream" in text.lower()
    assert "lunar" in text.lower()


def test_agent_allowed_tools_match_mcp_server():
    from agents.oneiro_agent import OneiroAgent

    agent = OneiroAgent()
    allowed = set(agent.options.allowed_tools)

    expected = {
        "mcp__oneiro__calculate_natal_chart",
        "mcp__oneiro__generate_horoscope",
        "mcp__oneiro__forecast_event",
        "mcp__oneiro__list_event_types",
        "mcp__oneiro__list_horoscope_periods",
        "mcp__oneiro__analyze_dream",
        "mcp__oneiro__list_dream_symbols",
        "mcp__oneiro__list_archetypes",
        "mcp__oneiro__list_hvdc_categories",
        "mcp__oneiro__get_lunar_day",
        "mcp__oneiro__get_lunar_period",
        "mcp__oneiro__search_city",
        "mcp__oneiro__validate_birth_data",
    }
    assert allowed == expected


def test_mcp_server_module_referenced_is_real():
    """The MCP server module the agent will spawn must actually exist."""
    mod = importlib.import_module("backend.mcp.server")
    assert mod.mcp.name == "oneiro-scope"


def test_cli_module_imports():
    mod = importlib.import_module("agents.cli")
    assert hasattr(mod, "main")
