"""Tests for the analysis orchestrator (what can be computed, in what order)."""

from __future__ import annotations

from backend.services.strategic.analysis_plan import (
    BIRTH_DATE,
    BIRTH_PLACE,
    BIRTH_TIME,
    DREAM_TEXT,
    STAGES,
    TARGET_DATE,
    build_plan,
)


def _ids(entries):
    return [e["id"] for e in entries]


def test_no_inputs_offers_only_standalone_and_asks_for_birth_data():
    plan = build_plan([])
    # With nothing known, only the zero-input stages can run.
    assert _ids(plan["ready"]) == ["lunar-day"]
    # And the plan must tell the caller exactly what to ask for.
    asked = {q["input"] for q in plan["questions_to_ask"]}
    assert {BIRTH_DATE, BIRTH_PLACE, DREAM_TEXT} <= asked
    assert plan["next_step"]["id"] == "lunar-day"


def test_natal_chart_unlocks_first_with_date_and_place():
    plan = build_plan([BIRTH_DATE, BIRTH_PLACE])
    ready = _ids(plan["ready"])
    assert "natal-chart" in ready
    # Houses-dependent stages stay blocked until birth time is known.
    assert "money-contour" in _ids(plan["blocked"])
    natal = next(e for e in plan["ready"] if e["id"] == "natal-chart")
    assert natal["degraded_without"] == [BIRTH_TIME]
    assert "note" in natal


def test_full_birth_data_unlocks_the_core_reading_in_order():
    plan = build_plan([BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    ready = _ids(plan["ready"])
    # Canonical order: foundation → self → timing → place.
    assert ready.index("natal-chart") < ready.index("money-contour")
    assert ready.index("money-contour") < ready.index("transits")
    assert ready.index("transits") < ready.index("astrocartography")
    assert plan["next_step"]["id"] == "natal-chart"
    # Stages needing extra input stay blocked until it arrives.
    blocked = _ids(plan["blocked"])
    assert "event-forecast" in blocked and "compare-cities" in blocked


def test_stage_dependencies_are_surfaced_not_enforced():
    """Each tool recomputes the chart, so a prerequisite is advisory only."""
    plan = build_plan([BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    money = next(e for e in plan["ready"] if e["id"] == "money-contour")
    assert money["better_after"] == ["natal-chart"]

    after = build_plan(
        [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], completed=["natal-chart"]
    )
    money2 = next(e for e in after["ready"] if e["id"] == "money-contour")
    assert "better_after" not in money2


def test_completed_stages_stop_being_offered():
    plan = build_plan(
        [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], completed=["natal-chart"]
    )
    assert "natal-chart" in _ids(plan["completed"])
    assert "natal-chart" not in _ids(plan["ready"])
    assert plan["next_step"]["id"] != "natal-chart"


def test_target_date_unlocks_event_forecast():
    plan = build_plan([BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, TARGET_DATE])
    assert "event-forecast" in _ids(plan["ready"])


def test_locale_switches_language_of_names_and_questions():
    ru = build_plan([], locale="ru")
    en = build_plan([], locale="en")
    assert ru["locale"] == "ru" and en["locale"] == "en"
    ru_q = " ".join(q["question"] for q in ru["questions_to_ask"])
    en_q = " ".join(q["question"] for q in en["questions_to_ask"])
    assert "рождения" in ru_q
    assert "birth" in en_q.lower()
    assert ru["next_step"]["name"] != en["next_step"]["name"]


def test_every_stage_is_classified_exactly_once():
    plan = build_plan([BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    seen = _ids(plan["ready"]) + _ids(plan["blocked"]) + _ids(plan["completed"])
    assert sorted(seen) == sorted(s.id for s in STAGES)
    assert plan["total_stages"] == len(STAGES)


def test_stage_tools_exist_in_the_mcp_registry():
    """The plan must not point at tools the server does not expose.

    Tool modules pull in optional heavy deps (mcp, fastapi, mediapipe), so any
    module that cannot import in a bare environment is skipped rather than
    failing — CI installs the full set and checks all of them.
    """
    import importlib

    import pytest

    module_names = (
        "astrology", "dreams", "lunar", "strategic_astro",
        "strategic_patterns",
    )
    available: set[str] = set()
    for name in module_names:
        try:
            module = importlib.import_module(f"backend.mcp.tools.{name}")
        except Exception as exc:  # optional heavy dep absent here
            pytest.skip(f"backend.mcp.tools.{name} not importable: {exc}")
        available |= set(dir(module))

    missing = [s.tool for s in STAGES if s.tool not in available]
    assert not missing, f"plan references unknown tools: {missing}"


def test_plan_tool_disclaimer_follows_locale():
    """A Russian disclaimer under an English plan breaks the tool's contract."""
    from backend.mcp.tools.strategic_patterns import analysis_plan

    ru = analysis_plan(locale="ru")["disclaimer"]
    en = analysis_plan(locale="en")["disclaimer"]
    assert ru != en
    assert "рефлексивно-развлекательный" in ru
    assert "reflective" in en.lower()


def test_plan_tool_wrapper_shape():
    from backend.mcp.tools.strategic_patterns import analysis_plan

    out = analysis_plan(known_inputs=[BIRTH_DATE, BIRTH_PLACE], locale="en")
    assert out["pattern_id"] == "analysis-plan"
    assert out["layer"] == "astronomy" and out["confidence"] == 1.0
    assert out["disclaimer"]
    assert "how_to_use" in out
    assert out["computed"]["next_step"]["id"] == "natal-chart"
