"""Every substantive tool response offers what else can be computed — compactly.

History. The first menu carried the full ready/blocked/questions structure on
every response; a live audit measured ~90k chars of menu across one
conversation — the menu had become the payload (WP-11). The block is now
`{"next": [≤3 ready tools], "full_plan_tool": "analysis_plan"}` with a hard
≤200-char budget; the ordered plan and its questions live one call away in
`analysis_plan`.

The structural guards remain: the plan must not drift from the registry
(WP-10 cut it 47 → 19), and every stage tool must attach the menu for its own
stage and domain.
"""

from __future__ import annotations

import ast
import json
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


# ── the compact menu itself ──────────────────────────────────────────────────

def test_next_lists_only_ready_tools_in_stage_order():
    menu = capability_menu(
        "astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE], ["natal-chart"]
    )
    assert menu["full_plan_tool"] == "analysis_plan"
    assert menu["next"][0] == "money_contour", "canonical order: self after foundation"
    assert len(menu["next"]) <= 3
    # Steps whose inputs are missing are not offered at all — compare_cities
    # needs a city list nobody supplied.
    assert "compare_relocations" not in menu["next"]


def test_completed_steps_are_not_offered_again():
    menu = capability_menu(
        "astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        ["natal-chart", "money-contour"],
    )
    assert "money_contour" not in menu["next"]
    assert "calculate_natal_chart" not in menu["next"]


def test_chart_is_the_first_offer_when_nothing_ran_yet():
    menu = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    assert menu["next"][0] == "calculate_natal_chart"


def test_dreams_is_a_separate_domain_with_no_birth_data():
    dreams = capability_menu("dreams", ["dream_text"])
    assert set(dreams["next"]) <= {"analyze_dream", "dream_series_stats"}
    astro = capability_menu("astro", [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    assert "analyze_dream" not in astro["next"]
    assert "dream_series_stats" not in astro["next"]


def test_a_ready_step_is_actually_callable_with_what_the_menu_knows():
    """`next` is a promise: nothing further is needed to make this call.

    A stage that declares `requires=()` while its tool has a parameter with no
    default breaks that promise — the model follows the menu and gets a
    TypeError. Checked structurally so it holds for every stage.
    """
    import importlib
    import inspect

    menu = capability_menu("astro", [])
    for tool_name in menu["next"]:
        fn = None
        for mod in ("astrology", "dreams", "lunar", "strategic_astro",
                    "strategic_patterns"):
            module = importlib.import_module(f"backend.mcp.tools.{mod}")
            fn = getattr(module, tool_name, None)
            if fn is not None:
                break
        assert fn is not None, f"{tool_name} not found in any tool module"
        required = [
            p.name for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        ]
        assert not required, (
            f"menu offers {tool_name} as ready with no known inputs, but it "
            f"requires {required} — following the menu would raise TypeError"
        )


def test_menu_stays_within_the_wp11_size_budget():
    """The audit measured ~90k chars of menu across one live conversation.

    The compact block must stay under 200 chars in every state — if a new
    stage pushes past the ceiling, shorten the block, never raise the bar.
    """
    worst = max(
        len(json.dumps(capability_menu(domain, known, locale=loc), ensure_ascii=False))
        for loc in ("ru", "en")
        for domain in ("astro", "dreams")
        for known in ([], [BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE])
    )
    assert worst <= 200, f"menu grew to {worst} chars per response"


# ── the attachment helper ───────────────────────────────────────────────────

def test_with_menu_attaches_to_a_dict():
    out = with_menu({"data": 1}, domain="astro", known_inputs=[BIRTH_DATE])
    assert MENU_KEY in out
    assert out["data"] == 1
    assert set(out[MENU_KEY]) == {"next", "full_plan_tool"}


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


# ── the plan must not drift from the registry ───────────────────────────────

def _registered_tool_names() -> set[str]:
    """Tool names as `backend/mcp/server.py` actually registers them.

    Understands the WP-6 form `mcp.tool()(with_meta(module.function))` —
    the attribute is unwrapped from however many call layers wrap it."""
    src = (REPO / "backend" / "mcp" / "server.py").read_text()
    names: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Call):
            for arg in node.args:
                for inner in ast.walk(arg):
                    if isinstance(inner, ast.Attribute):
                        names.add(inner.attr)
    return names


def test_registry_matches_the_wp10_surface():
    """47 tools drowned the working set; the cut is enforced, not aspirational."""
    registered = _registered_tool_names()
    assert registered, "could not parse the registry — the check would be vacuous"
    assert len(registered) == 19, (
        f"registry has {len(registered)} tools — WP-10 fixed the surface at 19; "
        f"a new tool needs an explicit owner decision, not a drive-by add"
    )
    for gone in ("generate_horoscope", "horoscope_report", "profile_report_file",
                 "analyze_face", "physiognomy_report", "mc_in_sign",
                 "list_event_types", "decade_map", "synastry"):
        assert gone not in registered, f"{gone} came back after WP-8/WP-10"


def test_every_stage_points_at_a_registered_tool():
    """A stage naming an unregistered tool would be offered and then fail."""
    registered = _registered_tool_names()
    unknown = sorted({st.tool for st in STAGES} - registered)
    assert not unknown, f"stages reference unregistered tools: {unknown}"


def test_every_registered_computation_is_a_stage_or_reference():
    """The other direction: nothing registered may be undiscoverable."""
    registered = _registered_tool_names()
    stage_tools = {st.tool for st in STAGES}
    reference = {t for tools in REFERENCE_TOOLS.values() for t in tools}
    # analysis_plan is the plan itself — the one tool that needs no menu entry.
    orphans = registered - stage_tools - reference - {"analysis_plan"}
    assert not orphans, f"registered but undiscoverable: {sorted(orphans)}"


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
# them needs ephemeris work or an LLM. An earlier pass wired three tools to
# each other's stage ids and every runtime test still passed — the menus were
# present, just describing the wrong step. Only a structural check catches
# that. The guards apply to REGISTERED tools: module functions that left the
# registry in WP-10 keep their legacy with_menu calls but are no longer part
# of the product surface.

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


def _registered_wiring() -> dict[str, dict]:
    registered = _registered_tool_names()
    return {k: v for k, v in _menu_wiring().items() if k in registered}


def test_every_stage_tool_attaches_the_menu():
    """The owner's ask: calling any tool should reveal the rest."""
    wiring = _menu_wiring()
    assert wiring, "could not parse the call sites — the check would be vacuous"
    missing = sorted(
        {st.tool for st in STAGES} - set(wiring) - _NO_MENU_BY_DESIGN
    )
    assert not missing, f"stage tools with no capability menu: {missing}"


def test_each_registered_tool_marks_its_own_stage_completed():
    """Otherwise a tool offers itself back as the obvious next step."""
    stage_by_tool = {st.tool: st for st in STAGES}
    for name, wired in _registered_wiring().items():
        stage = stage_by_tool.get(name)
        if stage is None:
            continue  # analysis_plan itself, or a non-stage registered tool
        assert stage.id in wired["completed"], (
            f"{name} does not list its own stage {stage.id!r} as completed "
            f"(got {wired['completed']}) — it would offer itself back"
        )
        extra = sorted(set(wired["completed"]) - {stage.id})
        assert not extra, (
            f"{name} claims stage(s) it cannot verify ran: {extra}. "
            f"List only its own stage, {stage.id!r}."
        )


def test_menu_domain_matches_the_stage_domain():
    stage_by_tool = {st.tool: st for st in STAGES}
    for name, wired in _registered_wiring().items():
        if name not in stage_by_tool:
            continue
        assert stage_by_tool[name].domain == wired["domain"], (
            f"{name} attaches the {wired['domain']!r} menu but its stage is "
            f"{stage_by_tool[name].domain!r}"
        )


def test_registered_completed_ids_are_real_stages():
    ids = {st.id for st in STAGES}
    for name, wired in _registered_wiring().items():
        unknown = sorted(set(wired["completed"]) - ids)
        assert not unknown, f"{name} marks unknown stage(s) completed: {unknown}"


def test_reference_lookups_do_not_attach_a_menu():
    """A dictionary lookup is not a step in a reading; keep it quiet."""
    wired = set(_menu_wiring())
    listed = {t for tools in REFERENCE_TOOLS.values() for t in tools}
    assert wired.isdisjoint(listed)


# ── end to end through real tools ───────────────────────────────────────────

def test_money_contour_response_carries_the_compact_menu():
    from backend.mcp.tools.strategic_patterns import money_contour

    out = money_contour("1977-07-01", "22:30", "Europe/Kyiv", 47.85167, 35.11714)
    menu = out[MENU_KEY]
    assert set(menu) == {"next", "full_plan_tool"}
    assert "money_contour" not in menu["next"], "a tool must not offer itself back"
    assert "vocation_map" in menu["next"]
    assert len(json.dumps(menu, ensure_ascii=False)) <= 200
    # The deterministic payload is untouched by the addition.
    assert "computed" in out and "provenance" in out


def test_lunar_day_needs_no_argument():
    """The plan has always declared this step as needing no input."""
    from backend.mcp.tools.lunar import get_lunar_day

    out = get_lunar_day(timezone="Europe/Moscow")
    assert 1 <= out["lunar_day"] <= 30
    assert set(out[MENU_KEY]) == {"next", "full_plan_tool"}


@pytest.mark.asyncio
async def test_analyze_dream_offers_only_the_dreams_domain(monkeypatch):
    from backend.mcp.tools import dreams as dream_tools

    class _Resp:
        def model_dump(self, mode=None):
            return {"symbols": [], "interpretation": "x"}

    class _Svc:
        async def analyze_dream(self, req, interpret=True):
            return _Resp()

    monkeypatch.setattr(dream_tools, "_svc", lambda: _Svc())
    out = await dream_tools.analyze_dream("Мне снилось, что я лечу над городом.")
    menu = out[MENU_KEY]
    assert "money_contour" not in menu["next"], "dreams must not offer chart steps"
    assert set(menu["next"]) <= {"analyze_dream", "dream_series_stats"}


@pytest.mark.asyncio
async def test_profile_report_refuses_to_chart_null_island():
    """Regression kept at module level: the function left the MCP registry in
    WP-10 but still backs the web report path. It used to default to 0.0/0.0
    and report on the Gulf of Guinea."""
    from backend.mcp.tools.astrology import profile_report_file

    with pytest.raises(ValueError, match="birth_lat and birth_lon are required"):
        await profile_report_file("1977-07-01", "22:30")
