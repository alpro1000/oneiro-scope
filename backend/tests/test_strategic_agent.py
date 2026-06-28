"""Tests for StrategicAnalystAgent + orchestrator routing of strategic intents."""

from __future__ import annotations

import pytest


def test_strategic_agent_imports():
    from agents.specialists import StrategicAnalystAgent

    a = StrategicAnalystAgent()
    assert a.name == "strategic"


def test_strategic_agent_has_all_decision_support_tools():
    from agents.specialists import StrategicAnalystAgent

    a = StrategicAnalystAgent()
    allowed = set(a.options.allowed_tools)
    expected = {
        "mcp__oneiro__calculate_natal_chart",
        "mcp__oneiro__validate_birth_data",
        "mcp__oneiro__search_city",
        "mcp__oneiro__compute_transits",
        "mcp__oneiro__solar_return_chart",
        "mcp__oneiro__astrocartography_scan",
        "mcp__oneiro__get_lunar_day",
        "mcp__oneiro__get_lunar_period",
        "mcp__oneiro__generate_horoscope",
        "mcp__oneiro__forecast_event",
        "mcp__oneiro__list_event_types",
        "mcp__oneiro__list_horoscope_periods",
    }
    assert allowed == expected


def test_strategic_agent_env_carries_agent_name():
    """ONEIRO_AGENT_NAME=strategic is propagated to spawned MCP child."""
    from agents.specialists import StrategicAnalystAgent

    a = StrategicAnalystAgent()
    env = a.options.mcp_servers["oneiro"]["env"]
    assert env["ONEIRO_AGENT_NAME"] == "strategic"


@pytest.mark.parametrize(
    "text",
    [
        "Стоит ли мне переехать в Мадрид?",
        "Стратегический анализ года вперёд",
        "Should I take a mortgage now?",
        "Where to live by my chart?",
        "Year ahead overview please",
        "Какая страна мне подходит для жизни и работы",
        "Мне нужна стратегия на следующий год",
        "Карьерный выбор: остаться или сменить компанию?",
    ],
)
def test_classify_routes_strategic_questions(text):
    from agents.orchestrator import classify_intent

    assert classify_intent(text) == ["strategic"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Натальная карта на 15 мая 1990", ["astrology"]),
        ("Дневной гороскоп", ["astrology"]),
        ("Лунный день сегодня", ["lunar"]),
        ("Мне приснилось что я лечу", ["dream"]),
    ],
)
def test_classify_keeps_domain_routing_when_no_strategic_intent(text, expected):
    from agents.orchestrator import classify_intent

    assert classify_intent(text) == expected


def test_strategic_wins_over_domain_when_both_present():
    """If a question mixes strategic intent + domain words, the
    Strategic Analyst handles the synthesis (it'll call domain tools
    itself)."""
    from agents.orchestrator import classify_intent

    # "Стоит ли" (strategic) + "гороск" (astrology) → strategic wins.
    assert classify_intent("Стоит ли мне делать гороскоп на год?") == ["strategic"]


def test_strategic_system_prompt_has_layer_separation():
    """The Strategic Analyst's prompt must enumerate all 8 layers."""
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "agents"
        / "prompts"
        / "strategic_system.md"
    ).read_text(encoding="utf-8").lower()
    required_layers = [
        "objective fact",
        "astronomy",
        "age psychology",
        "career cycle",
        "economics",
        "user context",
        "symbolic",
        "llm narrative",
    ]
    for layer in required_layers:
        assert layer in text, f"Missing layer in strategic prompt: {layer}"


def test_strategic_system_prompt_forbids_will_and_budet():
    """The prompt itself must call out the no-determinism rule."""
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "agents"
        / "prompts"
        / "strategic_system.md"
    ).read_text(encoding="utf-8")
    assert "будет" in text
    assert "will" in text.lower()
    # And it must propose alternative phrasings.
    assert "traditionally associated" in text.lower()


def test_astrology_prompt_inherits_strategic_posture():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "agents"
        / "prompts"
        / "astrology_system.md"
    ).read_text(encoding="utf-8").lower()
    assert "strategic analyst" in text
    assert "confidence" in text
    assert "compute_transits" in text


def test_dream_prompt_inherits_strategic_posture():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "agents"
        / "prompts"
        / "dream_system.md"
    ).read_text(encoding="utf-8").lower()
    assert "strategic analyst" in text
    assert "evidence matrix" in text
    assert "no diagnosis" in text


def test_orchestrator_registers_strategic_specialist():
    from agents.orchestrator import SuperOrchestrator

    assert "strategic" in SuperOrchestrator.SPECIALISTS
