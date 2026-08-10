"""What a directory reviewer reads before a human ever tries the product.

Claude's connector directory and ChatGPT's app review both judge an MCP
server largely from its self-description: the instructions, the tool
descriptions, and the tool annotations. Those are promises, and this file
pins them to what the code actually does — because the review failure mode
is not "the server is bad" but "the server says something its behaviour
contradicts", and that class of rejection is entirely preventable.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def tools():
    import asyncio

    from backend.mcp.server import mcp

    return asyncio.new_event_loop().run_until_complete(mcp.list_tools())


# --- the server's own claim about itself --------------------------------------


def test_instructions_do_not_call_astrology_a_science():
    """"Science-grounded astrology" is the overclaim our own domain rules
    forbid (docs/steering/domain.md), and the exact phrase a reviewer reads
    as misleading. The defensible claim is the split: computed astronomy,
    labelled interpretation."""
    from backend.mcp.server import mcp

    text = mcp.instructions or ""
    assert "science-grounded" not in text.lower()
    assert "not science" in text.lower()


def test_instructions_carry_the_non_advice_position():
    """Both platforms' policies restrict tailored medical/legal/financial
    advice. The defence is that the server itself states the boundary and
    enforces it (`no_determinism.py`, `disclaimer.py`) — so the statement
    must actually be in the instructions the host shows."""
    from backend.mcp.server import mcp

    text = (mcp.instructions or "").lower()
    for word in ("medical", "legal", "financial", "entertainment"):
        assert word in text, f"instructions no longer state the {word} boundary"


# --- annotations: promises, checked against behaviour --------------------------


def test_every_tool_declares_its_annotations(tools):
    """A reviewer (and a host) treats a missing hint as "unknown", which
    reads as risk. Every tool states what it is."""
    missing = [t.name for t in tools if t.annotations is None
               or t.annotations.readOnlyHint is None]
    assert not missing, f"tools without annotations: {missing}"


def test_only_the_two_real_writers_are_marked_as_writers(tools):
    """`calculate_natal_chart` consumes the free tier's lifetime grant;
    `analyze_dream(remember=True)` appends to the caller's series. Nothing
    else on this server writes anything — and claiming otherwise in either
    direction is the kind of mismatch a review exists to catch."""
    writers = {t.name for t in tools if t.annotations.readOnlyHint is False}
    assert writers == {"calculate_natal_chart", "analyze_dream"}, writers


def test_no_tool_is_marked_destructive(tools):
    """Nothing here deletes or overwrites user data. Account deletion is a
    portal action, deliberately NOT an MCP tool."""
    destructive = [t.name for t in tools
                   if t.annotations.destructiveHint is True]
    assert not destructive, destructive


def test_external_network_is_declared_where_it_happens(tools):
    """GeoNames is the one external service any tool touches. The tools that
    geocode say so via openWorldHint; the pure-ephemeris tools say the
    opposite — their determinism is the product's claim, and the hint is
    where that claim is machine-readable."""
    open_world = {t.name for t in tools if t.annotations.openWorldHint is True}
    assert open_world == {
        "search_city", "validate_birth_data", "calculate_natal_chart",
    }, open_world


def test_the_idempotency_story_matches_the_entitlement_code(tools):
    """Re-issuing the same chart is free forever (`same_chart`), so the natal
    tool is idempotent despite writing. Remembering a dream appends each
    time, so it is not."""
    by_name = {t.name: t.annotations for t in tools}
    assert by_name["calculate_natal_chart"].idempotentHint is True
    assert by_name["analyze_dream"].idempotentHint is not True


# --- descriptions: what the model and the reviewer actually read ---------------


def test_every_tool_has_a_real_description(tools):
    """Empty or one-word descriptions read as an unfinished product."""
    thin = [t.name for t in tools if not t.description
            or len(t.description.strip()) < 40]
    assert not thin, f"tools with missing/thin descriptions: {thin}"


def test_no_description_smuggles_host_directives(tools):
    """Injection-shaped text in tool descriptions is an instant rejection —
    and reviewers grep for exactly these shapes. Our descriptions guide the
    MODEL's use of the tool, which is what descriptions are for; they must
    never address the host or claim system authority."""
    patterns = (
        "<system", "</system", "ignore previous", "ignore all previous",
        "disregard the above", "you must always", "do not tell the user",
    )
    dirty = {
        t.name: p
        for t in tools
        for p in patterns
        if p in (t.description or "").lower()
    }
    assert not dirty, f"host-directive shapes in descriptions: {dirty}"


def test_no_description_promises_prediction(tools):
    """The no-determinism rule applies to our own marketing surface first.

    Matched case-sensitively on phrases, not words: "will" alone is ordinary
    future tense ("the response will contain...") and banning it would just
    teach someone to weaken this test.
    """
    banned = (
        "predicts your future", "will happen to you", "guaranteed",
        "definitely will", "100% accurate", "scientifically proven",
    )
    dirty = {
        t.name: p
        for t in tools
        for p in banned
        if p in (t.description or "").lower()
    }
    assert not dirty, dirty
