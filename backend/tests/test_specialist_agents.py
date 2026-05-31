"""Specialist agent smoke tests (Phase B).

Each specialist must import cleanly, declare the right narrow tool
subset, and have a non-trivial domain-specific system prompt. We do not
exercise the Claude API here.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "agents" / "prompts"


def test_specialists_module_imports():
    from agents.specialists import AstrologyAgent, DreamAgent, LunarAgent  # noqa: F401


def test_astrology_agent_tools_subset():
    from agents.specialists import AstrologyAgent

    a = AstrologyAgent()
    allowed = set(a.options.allowed_tools)
    expected = {
        "mcp__oneiro__calculate_natal_chart",
        "mcp__oneiro__generate_horoscope",
        "mcp__oneiro__forecast_event",
        "mcp__oneiro__list_event_types",
        "mcp__oneiro__list_horoscope_periods",
        "mcp__oneiro__search_city",
        "mcp__oneiro__validate_birth_data",
    }
    assert allowed == expected
    # Must NOT have dream or lunar tools.
    forbidden = {
        "mcp__oneiro__analyze_dream",
        "mcp__oneiro__get_lunar_day",
        "mcp__oneiro__get_lunar_period",
    }
    assert not (allowed & forbidden)


def test_dream_agent_tools_subset():
    from agents.specialists import DreamAgent

    a = DreamAgent()
    allowed = set(a.options.allowed_tools)
    expected = {
        "mcp__oneiro__analyze_dream",
        "mcp__oneiro__list_dream_symbols",
        "mcp__oneiro__list_archetypes",
        "mcp__oneiro__list_hvdc_categories",
    }
    assert allowed == expected
    forbidden = {
        "mcp__oneiro__calculate_natal_chart",
        "mcp__oneiro__get_lunar_day",
    }
    assert not (allowed & forbidden)


def test_lunar_agent_tools_subset():
    from agents.specialists import LunarAgent

    a = LunarAgent()
    allowed = set(a.options.allowed_tools)
    assert allowed == {
        "mcp__oneiro__get_lunar_day",
        "mcp__oneiro__get_lunar_period",
    }


@pytest.mark.parametrize(
    "name,must_mention",
    [
        ("astrology", ("natal", "horoscope", "swiss ephemeris")),
        ("dream", ("hall/van de castle", "archetype", "rem")),
        ("lunar", ("lunar", "phase", "provenance")),
    ],
)
def test_system_prompt_present_and_domain_focused(name, must_mention):
    path = _PROMPTS_DIR / f"{name}_system.md"
    text = path.read_text(encoding="utf-8").lower()
    assert len(text) > 500
    for needle in must_mention:
        assert needle.lower() in text, f"{name} prompt missing '{needle}'"


def test_specialist_names_unique():
    from agents.specialists import AstrologyAgent, DreamAgent, LunarAgent

    names = {AstrologyAgent.name, DreamAgent.name, LunarAgent.name}
    assert names == {"astrology", "dream", "lunar"}


def test_base_agent_runs_qualifier_idempotently():
    """`_qualify` should leave already-qualified names alone."""
    from agents.base import _qualify

    out = _qualify(["calculate_natal_chart", "mcp__oneiro__get_lunar_day"])
    assert out == [
        "mcp__oneiro__calculate_natal_chart",
        "mcp__oneiro__get_lunar_day",
    ]


def test_generalist_still_works_after_refactor():
    """Backward compatibility: OneiroAgent keeps all 13 tools."""
    from agents.oneiro_agent import OneiroAgent, ALL_ONEIRO_TOOLS

    agent = OneiroAgent()
    assert len(agent.options.allowed_tools) == len(ALL_ONEIRO_TOOLS) == 13
