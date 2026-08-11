"""MCP Apps (io.modelcontextprotocol/ui) — the view contract.

The extension is additive: a host that does not implement it must receive
exactly the response it received before. Most of what is asserted here is
therefore about NOT breaking the existing surface, plus the few things the
specification actually fixes — the reserved `ui://` scheme, the
`text/html;profile=mcp-app` mime type, and `_meta.ui.resourceUri` on the tool.
"""

from __future__ import annotations

import pytest

from backend.mcp import apps


def test_the_scheme_and_mime_type_are_the_reserved_ones():
    """Both are fixed by the specification — a typo here renders nothing."""
    assert apps.UI_SCHEME == "ui://"
    assert apps.UI_MIME == "text/html;profile=mcp-app"
    assert apps.UI_EXTENSION == "io.modelcontextprotocol/ui"
    for view in apps.VIEWS:
        assert view.uri.startswith("ui://"), view.uri


def test_every_declared_view_has_a_built_bundle():
    """The backend deploys with pip and no Node step, so the HTML is committed.

    A missing file here means production would serve a tool with a view that
    cannot load.
    """
    missing = [v.slug for v in apps.VIEWS if not v.exists()]
    assert not missing, (
        f"no built bundle for {missing} — run `npm run build` in packages/mcp-app"
    )


@pytest.mark.parametrize("view", apps.VIEWS, ids=lambda v: v.slug)
def test_the_view_is_self_contained_and_reaches_no_network(view):
    """The security claim that lets the resource declare no CSP domains.

    If a view ever needs a socket or an external asset, the host must be told
    through `_meta.ui.csp` — and users get warned about the domain. Keeping
    views offline is what makes that unnecessary, so it is asserted rather
    than assumed.

    The check targets fetching CONSTRUCTS, not URL-shaped strings: an SVG
    carries `xmlns="http://www.w3.org/2000/svg"`, which is an XML namespace
    identifier the parser never dereferences. Grepping for "http" would fail
    on that and teach the next person to weaken the test.
    """
    html = view.html()

    forbidden = {
        "fetch(": "network fetch",
        "XMLHttpRequest": "XHR",
        "WebSocket": "websocket",
        "EventSource": "server-sent events",
        "navigator.sendBeacon": "beacon",
        "@import": "external stylesheet",
        "importScripts": "worker import",
        "url(http": "remote CSS asset",
        'src="http': "remote element source",
        "src='http": "remote element source",
        'href="http': "remote link",
        "fonts.googleapis": "webfont host",
    }
    hits = [why for token, why in forbidden.items() if token in html]
    assert not hits, f"view is not offline — found: {', '.join(hits)}"

    # Belt and braces on the same claim: the ONLY URL-shaped string a view may
    # contain is the SVG namespace, which is an identifier the parser never
    # dereferences. (Inline SVG in HTML does not need it declared — the HTML
    # parser assigns the namespace — so its presence is optional, but anything
    # else URL-shaped is not.)
    leftovers = [
        html[i:i + 60]
        for i in range(len(html))
        if html.startswith(("http://", "https://"), i)
        and not html.startswith("http://www.w3.org/2000/svg", i)
    ]
    assert not leftovers, f"unexpected URL in {view.slug}: {leftovers[:2]}"


@pytest.mark.parametrize("view", apps.VIEWS, ids=lambda v: v.slug)
def test_every_view_can_hand_its_figures_back_to_the_chat(view):
    """`ui/message` is the seam, not a convenience.

    A view draws the deterministic layer (1.0); what it MEANS is the model's
    layer (0.7). The control that puts the exact figures back into the
    conversation is how a user crosses from one to the other without anyone
    paraphrasing the numbers in between — so every view must have it.
    """
    html = view.html()
    assert "data-ask=" in html, f"{view.slug} cannot ask the chat anything"
    assert "ui/message" in html, f"{view.slug} does not speak ui/message"


def test_asking_the_chat_is_not_a_network_call():
    """The ask goes to the HOST, in the open, as a visible turn.

    Worth stating as a test: adding an outbound-looking feature is exactly
    when someone reaches for fetch(), which would break the no-CSP-domains
    property every view depends on.
    """
    for view in apps.VIEWS:
        assert "postMessage" in view.html()


def test_tool_meta_points_at_a_registered_view():
    meta = apps.tool_ui_meta(apps.NATAL_WHEEL)
    assert meta["ui"]["resourceUri"] == apps.NATAL_WHEEL.uri
    # Visibility omitted → the spec default ["model", "app"], i.e. the model
    # keeps the tool. Pinning it to ["app"] would hide the chart from the model.
    assert "visibility" not in meta["ui"]


def test_a_missing_bundle_raises_rather_than_serving_a_blank_page(tmp_path):
    """§12: no silent degradation. An empty view is indistinguishable from a
    broken one, so the server must say which it is."""
    ghost = apps.View("ghost", "does-not-exist.html", "Ghost", "n/a")
    assert not ghost.exists()
    with pytest.raises(RuntimeError, match="npm run build"):
        ghost.html()


# --- integration with the live server ----------------------------------------


@pytest.mark.anyio
async def test_the_server_registers_every_view_as_a_ui_resource():
    from backend.mcp.server import mcp

    resources = await mcp.list_resources()
    by_uri = {str(r.uri): r for r in resources}
    for view in apps.VIEWS:
        assert view.uri in by_uri, sorted(by_uri)
        assert by_uri[view.uri].mimeType == apps.UI_MIME


@pytest.mark.anyio
@pytest.mark.parametrize("view", apps.VIEWS, ids=lambda v: v.slug)
async def test_reading_a_resource_returns_its_own_document(view):
    """Per view, not just one: a late-binding closure in the registration
    loop would happily serve the last view's HTML under every URI."""
    from backend.mcp.server import mcp

    contents = list(await mcp.read_resource(view.uri))
    assert contents, "resources/read returned nothing"
    body = contents[0]
    assert body.mime_type == apps.UI_MIME
    assert body.content.lstrip().startswith("<!doctype html")
    assert body.content == view.html(), f"{view.slug} served another view's body"


@pytest.mark.anyio
async def test_the_natal_tool_declares_the_view_without_changing_the_surface():
    from backend.mcp.server import mcp

    tools = await mcp.list_tools()
    # WP-10 fixed this at 19; the owner re-added the two face-reading tools.
    # The number is not the point — a view must not smuggle in a tool.
    assert len(tools) == 21, [t.name for t in tools]

    natal = next(t for t in tools if t.name == "calculate_natal_chart")
    dumped = natal.model_dump(by_alias=True, exclude_none=True)
    assert dumped["_meta"]["ui"]["resourceUri"] == apps.NATAL_WHEEL.uri


@pytest.mark.anyio
async def test_no_other_tool_accidentally_claims_a_view():
    from backend.mcp.server import mcp

    tools = await mcp.list_tools()
    with_ui = {
        t.name for t in tools
        if (t.model_dump(by_alias=True, exclude_none=True).get("_meta") or {}).get("ui")
    }
    assert with_ui == {
        "calculate_natal_chart",
        "analyze_dream",
        "get_lunar_period",
        "astrocartography_lines",
        "compare_relocations",
        "money_contour",
        "vocation_map",
    }, with_ui


@pytest.mark.anyio
async def test_no_declared_view_goes_unclaimed():
    """A view nothing points at is dead weight the host will never fetch.

    Note what is NOT asserted: that each view has exactly one tool. Sharing is
    correct where the payloads are the same shape — `money_contour` and
    `vocation_map` both render through `pattern-map`, and writing two
    near-identical renderers would give two places to fix one bug. An earlier
    version of this test forbade that, which was an assumption rather than a
    requirement.
    """
    from backend.mcp.server import mcp

    claimed = set()
    for tool in await mcp.list_tools():
        ui = (tool.model_dump(by_alias=True, exclude_none=True).get("_meta") or {}).get("ui")
        if ui:
            claimed.add(ui["resourceUri"])

    declared = {v.uri for v in apps.VIEWS}
    assert claimed == declared, f"unclaimed: {declared - claimed}, unknown: {claimed - declared}"


@pytest.fixture
def anyio_backend():
    return "asyncio"
