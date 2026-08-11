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


# --- face reading: staged, and safe for the day it ships ----------------------
#
# `read_face_traits` is written, tested and NOT registered. The owner's call:
# a reviewer who reads "face reading" in a tool list and closes the
# application without opening the schema rejects the whole server, and the
# funnel that needs this feature lives on the web, which needs no approval.
#
# These tests therefore run against the FUNCTION, not the served tool list.
# That is the point: the guarantees have to outlive the registration, or the
# day someone re-adds the two lines they will be re-adding something nobody
# has checked in months. Three properties make it publishable, and all three
# must be legible to a reviewer who only reads the schema:
#
#   1. It takes no image and no photo path. The input is a QUESTIONNAIRE — the
#      person's own words about their own face — which is not biometric
#      processing at all: no image, no measurement, no template.
#   2. It says physiognomy is not scientifically validated, and cites who says
#      so, rather than presenting a reading as a finding.
#   3. It rules out assessing other people, by name and by use case.


@pytest.fixture(scope="module")
def face_tool():
    from backend.mcp.tools.physiognomy import read_face_traits

    return read_face_traits


def _flat(text: str | None) -> str:
    """Docstrings wrap; a phrase split across a newline still counts."""
    return " ".join((text or "").split()).lower()


def test_the_face_reading_is_staged_not_shipped(tools):
    """The submission decision, in executable form.

    Delete this test when the listing is approved and the tools go back —
    that is the intended way past it. It exists so the re-add is a decision
    someone makes on purpose, having read why it was staged, rather than a
    drive-by two-line edit. See the block in `backend/mcp/server.py`.
    """
    served = {t.name for t in tools}
    assert not served & {"read_face_traits", "physiognomy_methods"}, (
        "face reading is back on the MCP surface. If that is deliberate and "
        "the directory listing is already approved, delete this test. If it "
        "is not, the whole server is now carrying a rejection risk for two "
        "tools whose users are on the web."
    )


def test_the_face_tool_takes_no_photo(face_tool):
    import inspect

    params = set(inspect.signature(face_tool).parameters)
    assert params == {"features", "metrics", "landmarks", "locale"}, params
    assert not params & {"photo_path", "photo_paths", "image", "image_url"}


def test_the_face_tool_does_not_present_itself_as_measurement(face_tool):
    text = _flat(face_tool.__doc__)
    assert "not scientifically validated" in text
    assert "todorov" in text, "the claim needs its source, like every other claim"


def test_the_face_tool_rules_out_assessing_other_people(face_tool):
    """The owner asked for this feature "for everyone, including HR". The
    feature was built; that one use was not. Reading a stranger's face to
    decide about them is prohibited by the EU AI Act (Art. 5) and by both
    platforms, and facial features correlate with protected characteristics —
    so the refusal is in the tool's own description, where a model calling it
    reads it before deciding what to do."""
    text = _flat(face_tool.__doc__)
    assert "do not use it to assess another person" in text
    for forbidden_use in ("hiring", "lending", "insurance", "tenancy", "policing"):
        assert forbidden_use in text, f"the description no longer rules out {forbidden_use}"


def test_the_face_tool_says_what_it_is_in_its_first_line(face_tool):
    """No euphemism at the top of the description.

    The temptation on a re-review is to name it something that does not scan
    as physiognomy. That reads as an attempt to slip it past, which is worse
    than the honest name — so the opening line states the thing itself, and
    that it runs on self-description rather than photographs. A reviewer
    should have the answer before they have the question.
    """
    first = _flat((face_tool.__doc__ or "").strip().splitlines()[0])
    assert "face reading" in first, first
    assert "self-described" in first or "no photo" in first, first


def test_the_face_reading_carries_its_disclaimer_at_runtime(face_tool):
    """A description a reviewer reads is a promise; this is the behaviour."""
    import asyncio

    out = asyncio.new_event_loop().run_until_complete(
        face_tool(features={"face_shape": "square", "jaw_wide": True})
    )
    assert out["readings"], "a questionnaire answer produced no reading"
    assert out["disclaimer"].strip(), "reading returned without its disclaimer"
    assert "how_to_read" in out
    for r in out["readings"]:
        assert r["source"], f"reading without a source: {r}"


def test_the_face_reading_refuses_an_empty_call(face_tool):
    """No silent empty reading (conventions.md §12): nothing in, error out."""
    import asyncio

    with pytest.raises(ValueError, match="Nothing to read"):
        asyncio.new_event_loop().run_until_complete(face_tool())


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
