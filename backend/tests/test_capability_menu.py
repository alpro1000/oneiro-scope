"""Every substantive tool response offers what else can be computed.

The problem this guards. The server registers 46 tools; a chat that lands on
one of them sees only that one and cannot discover that the same birth data
also buys a money contour, a decade map, astrocartography over a city pool or
a Solar Return. `analysis_plan` answered this from the start, but only if the
model thought to ask — and it usually did not. So the menu now travels with
the data.

Offered, not run, on purpose: a decade map scans ten years at a 10-day step, a
city scan runs a whole pool, and a Solar Return suggestion computes one return
per candidate city. Running all of that on every call would spend minutes and
quota answering a question nobody asked.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.mcp.tools._menu import MENU_KEY, birth_inputs, with_menu
from backend.services.strategic.analysis_plan import (
    BIRTH_DATE,
    BIRTH_PLACE,
    BIRTH_TIME,
    REFERENCE_TOOLS,
    STAGES,
    capability_menu,
)

REPO = Path(__file__).resolve().parents[2]


# ── the menu itself ─────────────────────────────────────────────────────────

def test_ready_lists_only_steps_whose_inputs_are_satisfied():
    menu = capability_menu(
        "astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], ["natal-chart"]
    )
    ready_tools = {r["tool"] for r in menu["ready"]}
    assert "money_contour" in ready_tools
    assert "vocation_map" in ready_tools
    # Blocked on an input nobody supplied yet.
    blocked_tools = {r["tool"] for r in menu["needs_input"]}
    assert "synastry" in blocked_tools
    assert "compare_relocations" in blocked_tools
    assert ready_tools.isdisjoint(blocked_tools)


def test_blocked_steps_name_the_missing_input_and_ask_for_it():
    menu = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    synastry = next(r for r in menu["needs_input"] if r["tool"] == "synastry")
    assert synastry["missing"] == ["partner_birth_data"]
    assert menu["questions_to_ask"], "a blocked step must come with a question"


def test_a_ready_step_is_actually_callable_with_what_the_menu_knows():
    """`ready` is a promise: nothing further is needed to make this call.

    A stage that declares `requires=()` while its tool has a parameter with no
    default breaks that promise — the model follows the menu and gets a
    TypeError. Checked structurally so it holds for every stage, not just the
    one that was wrong (`get_lunar_day`, which now defaults to today).
    """
    import importlib
    import inspect

    menu = capability_menu("astro", [], max_items=50)
    for entry in menu["ready"]:
        fn = None
        for mod in ("astrology", "dreams", "lunar", "physiognomy",
                    "strategic_astro", "strategic_patterns"):
            module = importlib.import_module(f"backend.mcp.tools.{mod}")
            fn = getattr(module, entry["tool"], None)
            if fn is not None:
                break
        assert fn is not None, f"{entry['tool']} not found in any tool module"
        required = [
            p.name for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        ]
        assert not required, (
            f"menu offers {entry['tool']} as ready with no known inputs, but it "
            f"requires {required} — following the menu would raise TypeError"
        )


def test_completed_steps_are_not_offered_again():
    menu = capability_menu(
        "astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        ["natal-chart", "money-contour"],
    )
    offered = {r["tool"] for r in menu["ready"] + menu["needs_input"]}
    assert "money_contour" not in offered


def test_dependencies_are_a_soft_ordering_hint_not_a_gate():
    """`depends_on` must mean the same thing here as it does in `build_plan`.

    Each tool recomputes the chart geometry it needs, so a stage runs fine
    before its prerequisite — reading it first is merely confusing. An earlier
    version hard-gated on this, which forced every wrapper to claim
    `natal-chart` was complete just to unblock the rest, which in turn hid
    `calculate_natal_chart` from the menu entirely.
    """
    menu = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    ready = {r["tool"]: r for r in menu["ready"]}
    assert "money_contour" in ready, "a soft dependency must not remove the offer"
    assert ready["money_contour"]["better_after"] == ["natal-chart"]
    assert "calculate_natal_chart" in ready
    assert "better_after" not in ready["calculate_natal_chart"]


def test_the_chart_stops_being_flagged_once_it_has_run():
    menu = capability_menu(
        "astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], ["natal-chart"]
    )
    ready = {r["tool"]: r for r in menu["ready"]}
    assert "better_after" not in ready["money_contour"]


def test_a_wrapper_never_claims_a_prerequisite_it_cannot_observe():
    """A tool knows it ran. It does not know what else the session ran.

    Fabricating `natal-chart` in `completed` was how the old hard gate got
    worked around, and it suppressed the chart step from every menu that
    followed one of these tools.
    """
    stage_by_tool = {st.tool: st for st in STAGES}
    for name, wired in _menu_wiring().items():
        own = stage_by_tool[name].id
        extra = sorted(set(wired["completed"]) - {own})
        assert not extra, (
            f"{name} claims stage(s) it cannot verify ran: {extra}. "
            f"List only its own stage, {own!r}."
        )


def test_dreams_is_a_separate_domain_with_no_birth_data():
    dreams = capability_menu("dreams", ["dream_text"])
    tools = {r["tool"] for r in dreams["ready"] + dreams["needs_input"]}
    assert tools == {"analyze_dream"}
    astro = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    astro_tools = {r["tool"] for r in astro["ready"] + astro["needs_input"]}
    assert "analyze_dream" not in astro_tools
    assert dreams["reference_lookups"] != astro["reference_lookups"]


def test_face_lives_in_the_astro_domain():
    """The owner's split: chart and face both read one standing person."""
    menu = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    offered = {r["tool"] for r in menu["ready"] + menu["needs_input"]}
    assert "analyze_face_archive" in offered


def test_menu_is_capped_so_it_cannot_bloat_a_response():
    menu = capability_menu("astro", [BIRTH_DATE], max_items=3)
    assert len(menu["ready"]) <= 3
    assert len(menu["needs_input"]) <= 3


def test_menu_stays_within_a_size_budget():
    """This block rides on every response, so its cost is everyone's cost.

    ~3.5 KB buys discovery of 26 tools, which beats a round trip to
    `analysis_plan`. Ten times that would make the menu the response. If a new
    stage pushes past the ceiling, shorten the entries rather than raise it.
    """
    import json

    worst = max(
        len(json.dumps(capability_menu("astro", known, locale=loc), ensure_ascii=False))
        for loc in ("ru", "en")
        for known in ([], [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    )
    assert worst < 4500, f"menu grew to {worst} chars per response"


def test_blocked_entries_are_terser_than_ready_ones():
    """Prose about what a step answers is dead weight until it can run."""
    menu = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], ["natal-chart"])
    assert menu["needs_input"], "expected some blocked steps in this fixture"
    for entry in menu["needs_input"]:
        assert set(entry) == {"name", "tool", "missing"}
    for entry in menu["ready"]:
        assert "answers" in entry and "track" in entry


def test_locale_switches_the_offered_text():
    ru = capability_menu("astro", [BIRTH_DATE, BIRTH_PLACE], locale="ru")
    en = capability_menu("astro", [BIRTH_DATE, BIRTH_PLACE], locale="en")
    assert ru["hint"] != en["hint"]
    assert ru["ready"][0]["name"] != en["ready"][0]["name"]


# ── the attachment helper ───────────────────────────────────────────────────

def test_with_menu_attaches_to_a_dict():
    out = with_menu({"data": 1}, domain="astro", known_inputs=[BIRTH_DATE])
    assert MENU_KEY in out
    assert out["data"] == 1


def test_with_menu_leaves_non_dicts_alone():
    """Changing a tool's return shape to carry a hint would break callers."""
    payload = [1, 2, 3]
    assert with_menu(payload) is payload


def test_with_menu_never_double_attaches():
    once = with_menu({"a": 1}, known_inputs=[BIRTH_DATE])
    marker = object()
    once[MENU_KEY] = marker
    twice = with_menu(once, known_inputs=[BIRTH_DATE, BIRTH_TIME])
    assert twice[MENU_KEY] is marker


def test_birth_inputs_counts_coordinates_as_a_known_place():
    assert birth_inputs("1977-07-01", None, None, has_coordinates=True) == [
        BIRTH_DATE, BIRTH_PLACE
    ]
    assert birth_inputs("1977-07-01") == [BIRTH_DATE]
    assert birth_inputs() == []


# ── the menu must not drift from the registry ───────────────────────────────

def _registered_tool_names() -> set[str]:
    """Tool names as `backend/mcp/server.py` actually registers them."""
    src = (REPO / "backend" / "mcp" / "server.py").read_text()
    names: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        # mcp.tool()(module.function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Call):
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    names.add(arg.attr)
    return names


def test_every_stage_points_at_a_registered_tool():
    """The plan file asks for this by hand; a test enforces it.

    A stage naming a tool that does not exist would be offered to a model and
    then fail on call — the worst kind of menu entry.
    """
    registered = _registered_tool_names()
    assert registered, "could not parse the registry — the check would be vacuous"
    unknown = sorted({st.tool for st in STAGES} - registered)
    assert not unknown, f"stages reference unregistered tools: {unknown}"


def test_reference_lookups_are_registered_too():
    registered = _registered_tool_names()
    listed = {t for tools in REFERENCE_TOOLS.values() for t in tools}
    unknown = sorted(listed - registered)
    assert not unknown, f"reference list names unregistered tools: {unknown}"


def test_no_stage_is_both_offered_and_a_reference_lookup():
    """A computation over a person is not a dictionary lookup; keep them apart."""
    stage_tools = {st.tool for st in STAGES}
    listed = {t for tools in REFERENCE_TOOLS.values() for t in tools}
    assert stage_tools.isdisjoint(listed)


def test_stage_ids_and_orders_are_unique():
    ids = [st.id for st in STAGES]
    orders = [st.order for st in STAGES]
    assert len(ids) == len(set(ids)), "duplicate stage id"
    assert len(orders) == len(set(orders)), "duplicate order — offer sequence ambiguous"


def test_every_stage_declares_a_known_domain():
    assert {st.domain for st in STAGES} <= {"astro", "dreams"}


def test_dependencies_point_at_real_stages():
    ids = {st.id for st in STAGES}
    for st in STAGES:
        unknown = set(st.depends_on) - ids
        assert not unknown, f"{st.id} depends on missing stage(s): {sorted(unknown)}"


# ── the wiring must not drift from the plan ─────────────────────────────────
#
# These parse the tool modules instead of calling the tools, because calling
# them needs ephemeris work, photos or an LLM. An earlier pass wired three
# physiognomy tools to each other's stage ids and every runtime test still
# passed — the menus were present, just describing the wrong step. Only a
# structural check catches that, so here it is.

# `get_lunar_period` returns a bare list; see the note in its docstring.
_NO_MENU_BY_DESIGN = {"get_lunar_period"}


def _menu_wiring() -> dict[str, dict]:
    """function name → {domain, completed} for every with_menu call site."""
    found: dict[str, dict] = {}
    for path in sorted((REPO / "backend" / "mcp" / "tools").glob("*.py")):
        tree = ast.parse(path.read_text())
        for fn in tree.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            calls = [
                c for c in ast.walk(fn)
                if isinstance(c, ast.Call) and getattr(c.func, "id", None) == "with_menu"
            ]
            if not calls:
                continue
            assert len(calls) == 1, f"{fn.name} attaches the menu {len(calls)} times"
            kw = {k.arg: k.value for k in calls[0].keywords}
            domain = kw["domain"].value if "domain" in kw else "astro"
            completed = kw.get("completed")
            found[fn.name] = {
                "domain": domain,
                "completed": (
                    [e.value for e in completed.elts]
                    if isinstance(completed, ast.List) else []
                ),
            }
    return found


def test_every_stage_tool_attaches_the_menu():
    """The owner's ask: calling any tool should reveal the rest."""
    wiring = _menu_wiring()
    assert wiring, "could not parse the call sites — the check would be vacuous"
    missing = sorted(
        {st.tool for st in STAGES} - set(wiring) - _NO_MENU_BY_DESIGN
    )
    assert not missing, f"stage tools with no capability menu: {missing}"


def test_each_tool_marks_its_own_stage_completed():
    """Otherwise a tool offers itself back as the obvious next step."""
    stage_by_tool = {st.tool: st for st in STAGES}
    for name, wired in _menu_wiring().items():
        stage = stage_by_tool.get(name)
        assert stage is not None, f"{name} carries a menu but is not a plan stage"
        assert stage.id in wired["completed"], (
            f"{name} does not list its own stage {stage.id!r} as completed "
            f"(got {wired['completed']}) — it would offer itself back"
        )


def test_menu_domain_matches_the_stage_domain():
    stage_by_tool = {st.tool: st for st in STAGES}
    for name, wired in _menu_wiring().items():
        assert stage_by_tool[name].domain == wired["domain"], (
            f"{name} attaches the {wired['domain']!r} menu but its stage is "
            f"{stage_by_tool[name].domain!r}"
        )


def test_completed_ids_are_real_stages():
    ids = {st.id for st in STAGES}
    for name, wired in _menu_wiring().items():
        unknown = sorted(set(wired["completed"]) - ids)
        assert not unknown, f"{name} marks unknown stage(s) completed: {unknown}"


def test_reference_lookups_do_not_attach_a_menu():
    """A dictionary lookup is not a step in a reading; keep it quiet."""
    wired = set(_menu_wiring())
    listed = {t for tools in REFERENCE_TOOLS.values() for t in tools}
    assert wired.isdisjoint(listed)


# ── end to end through a real tool ─────────────────────────────────────────

def test_money_contour_response_carries_the_menu():
    from backend.mcp.tools.strategic_patterns import money_contour

    out = money_contour("1977-07-01", "22:30", "Europe/Kyiv", 47.85167, 35.11714)
    menu = out[MENU_KEY]
    assert menu["domain"] == "astro"
    ready = {r["tool"] for r in menu["ready"]}
    assert "vocation_map" in ready
    assert "money_contour" not in ready, "a tool must not offer itself back"
    assert menu["full_plan_tool"] == "analysis_plan"
    # The deterministic payload is untouched by the addition.
    assert "computed" in out and "provenance" in out


@pytest.mark.asyncio
async def test_profile_report_refuses_to_chart_null_island():
    """It used to default to 0.0/0.0 and report on the Gulf of Guinea.

    The menu then claimed the birth place was known, so it went on offering
    location-dependent steps off a placeholder. An error beats a confident
    wrong answer.
    """
    from backend.mcp.tools.astrology import profile_report_file

    with pytest.raises(ValueError, match="birth_lat and birth_lon are required"):
        await profile_report_file("1977-07-01", "22:30")


def test_lunar_day_needs_no_argument():
    """The plan has always declared this step as needing no input."""
    from backend.mcp.tools.lunar import get_lunar_day

    out = get_lunar_day(timezone="Europe/Moscow")
    assert 1 <= out["lunar_day"] <= 30
    assert out[MENU_KEY]["domain"] == "astro"


@pytest.mark.asyncio
async def test_analyze_dream_offers_only_the_dreams_domain(monkeypatch):
    from backend.mcp.tools import dreams as dream_tools

    class _Resp:
        def model_dump(self, mode=None):
            return {"symbols": [], "interpretation": "x"}

    class _Svc:
        async def analyze_dream(self, req):
            return _Resp()

    monkeypatch.setattr(dream_tools, "_svc", lambda: _Svc())
    out = await dream_tools.analyze_dream("Мне снилось, что я лечу над городом.")
    menu = out[MENU_KEY]
    assert menu["domain"] == "dreams"
    offered = {r["tool"] for r in menu["ready"] + menu["needs_input"]}
    assert "money_contour" not in offered, "dreams must not offer chart steps"
