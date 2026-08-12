"""WP-13: every claim says its provenance in words, not only as a decimal.

`"confidence": 0.7` is read by everyone — a model, a user, a directory
reviewer — as "70% likely to be true". It never meant that. It means "this
came from the model-synthesis tier", which is a statement about PROVENANCE.
On an astrology server the misreading is not cosmetic: a number that looks
like a likelihood turns a tradition's reading into a prediction with odds
attached, which is the one claim the product refuses to make.

The migration is ADDITIVE, and these tests pin both halves of that word: the
new name is present everywhere, and the old number is still there, unchanged,
for every client already reading it.
"""

from __future__ import annotations

import pytest

from backend.services.strategic.layers import (
    LADDER_RUNGS,
    LAYER_CONFIDENCE,
    LAYER_TIER,
    RuleSourceTier,
    TIER_CONFIDENCE,
    Layer,
    Source,
    tier_for_confidence,
    tier_for_sources,
)


# --- the taxonomy agrees with the ladder it renames ---------------------------


def test_every_layer_has_a_tier():
    """A layer without a tier would emit a number and no name — the exact
    half-migrated state this is meant to avoid."""
    missing = sorted(l.value for l in Layer if l not in LAYER_TIER)
    assert not missing, f"layers with no tier: {missing}"


def test_a_layer_tier_carries_that_layer_s_number():
    """The two vocabularies must describe the same ladder. If a tier ever
    disagreed with `LAYER_CONFIDENCE`, a response would carry a name and a
    number that contradict each other — worse than either alone."""
    for layer, tier in LAYER_TIER.items():
        assert TIER_CONFIDENCE[tier] == LAYER_CONFIDENCE[layer], (
            f"{layer.value}: tier {tier.value} says {TIER_CONFIDENCE[tier]}, "
            f"ladder says {LAYER_CONFIDENCE[layer]}"
        )


def test_the_four_documented_rungs_all_have_names():
    """CLAUDE.md quotes four rungs. Each must be nameable, or the
    documentation describes a ladder the code cannot speak."""
    for phrase, value in LADDER_RUNGS.items():
        assert tier_for_confidence(value), phrase


def test_the_physiognomy_tier_sits_below_the_lowest_rung():
    """Face reading is weaker than a symbol dictionary, and that ordering is
    the point: it is a tradition with no empirical validation at all."""
    assert (
        TIER_CONFIDENCE[RuleSourceTier.UNVALIDATED_TRADITION]
        < TIER_CONFIDENCE[RuleSourceTier.SYMBOL_DICTIONARY]
    )
    assert TIER_CONFIDENCE[RuleSourceTier.UNVALIDATED_TRADITION] == 0.6


def test_an_off_ladder_number_raises_instead_of_guessing():
    """No silent fallback (conventions.md §12). A combined score of 0.95 is
    not a tier — it is several sources agreeing — and forcing it into the
    nearest name would invent a provenance the claim does not have."""
    with pytest.raises(ValueError, match="not a tier"):
        tier_for_confidence(0.95)
    with pytest.raises(ValueError):
        tier_for_confidence(0.42)


def test_the_tier_of_a_claim_is_its_strongest_source():
    """A claim is as well-founded as its best evidence; stacking weak sources
    does not produce a strong one, so this takes the max, not a mean."""
    weak = Source(layer=Layer.LLM_NARRATIVE, kind="synthesis", detail="prose")
    hard = Source(layer=Layer.ASTRONOMY, kind="transit", detail="Saturn □ Sun")
    assert tier_for_sources([weak, hard]) is RuleSourceTier.COMPUTED
    assert tier_for_sources([weak]) is RuleSourceTier.MODEL_SYNTHESIS
    assert tier_for_sources([]) is RuleSourceTier.MODEL_SYNTHESIS


# --- additive: the name arrives, the number stays -----------------------------


def test_pattern_envelope_carries_both():
    from backend.mcp.tools.strategic_patterns import money_contour

    out = money_contour("1977-07-01", "22:30", "Europe/Kyiv", 47.85167, 35.11714)
    assert out["confidence"] == 1.0, "the old field must survive untouched"
    assert out["rule_source_tier"] == "computed"


def test_the_face_reading_names_its_tier():
    from backend.services.physiognomy.schemas import Reading

    r = Reading(system="mianxiang", topic="features.jaw_wide", text="…",
                source="Lin 1999")
    assert r.confidence == 0.6, "the old field must survive untouched"
    assert r.rule_source_tier == "unvalidated_tradition"


def test_the_archetype_lookup_names_its_tier():
    """0.9, not the 0.8 of a bare dictionary entry: these name their source,
    and a cited rule outranks a lookup. The tier has to carry that
    distinction, or the rename loses information the number had."""
    from backend.mcp.tools.archetypes import mc_in_sign

    out = mc_in_sign("sagittarius")
    assert out["confidence"] == 0.9
    assert out["rule_source_tier"] == "cited_rule"


# Tools that legitimately emit no `rule_source_tier`, each with the reason.
# This list is the whole point of the test below it: without it, a tool that
# emits NOTHING passes a "every emitted tier is valid" check vacuously —
# there is nothing to validate, so everything is valid. That is how the
# flagship tool went out carrying its provenance only as English prose in
# `how_to_read`, where no client can parse it.
_NO_TIER_BY_DESIGN: dict[str, str] = {
    "search_city": "geocoder output — a place, not a claim about a person",
    "validate_birth_data": "input validation; it asserts nothing to interpret",
    "analysis_plan": "a menu of what can be computed, not a computation",
    "lookup": "returns entries that carry their own per-item source",
    "get_lunar_day": "carries a full `provenance` block instead",
    "get_lunar_period": "carries a full `provenance` block instead",
    "dream_series_stats": "counts of the caller's own entries; no claim layer",
    "analyze_dream": "per-event evidence and citations, coded not interpreted",
    "astrocartography_lines": "GeoJSON geometry; the tier lives on the readings",
    "astrocartography_point": "geometry plus `score_explanation`",
    "astrocartography_scan": "geometry table; see `total_significance`",
    "compare_relocations": "geometry comparison, no interpretive claim",
    "compute_transits": "geometry: dated aspects, no reading attached",
    "solar_return_chart": "chart geometry, same contract as the natal core",
    "solar_return_suggest": "candidate dates, geometry only",
    "forecast_event": "returns its own weighted factors with sources",
}


def test_the_exemption_list_names_only_registered_tools():
    """A stale name here would silently excuse a tool that no longer exists,
    and worse, would keep excusing the one that replaced it."""
    import asyncio

    from backend.mcp.server import mcp

    served = {t.name for t in asyncio.new_event_loop().run_until_complete(
        mcp.list_tools()
    )}
    unknown = sorted(set(_NO_TIER_BY_DESIGN) - served)
    assert not unknown, f"exemptions for tools that are not served: {unknown}"


def test_every_registered_tool_either_carries_a_tier_or_is_exempt():
    """The gap the owner found: `calculate_natal_chart` shipped with no tier
    at all, and the "every emitted tier is valid" test passed on it vacuously
    — nothing emitted, nothing to invalidate. A test that proves correctness
    where a field exists and says nothing where it is missing cannot tell
    "deliberately exempt" from "forgotten".

    So the exemption is written down, and everything else must carry one.
    """
    import asyncio

    from backend.mcp.server import mcp

    served = {t.name for t in asyncio.new_event_loop().run_until_complete(
        mcp.list_tools()
    )}
    must_carry = sorted(served - set(_NO_TIER_BY_DESIGN))
    assert must_carry, "every tool got exempted — the list has eaten the rule"

    # These are the ones that must say their tier as a FIELD. Kept as an
    # explicit expectation rather than by calling each tool, because several
    # need birth data, an LLM or a database; the call-based checks below
    # cover the representative ones end to end.
    assert set(must_carry) == {
        "calculate_natal_chart", "money_contour", "vocation_map",
    }, must_carry


def test_every_emitted_tier_is_one_the_taxonomy_defines():
    """A typo in a hand-written literal ships a tier nobody defined, and
    nothing else notices — it is just a string in a dict.

    Written against real RESPONSES rather than by grepping source, because the
    literals are written four different ways (dict value, dict-of-dicts,
    Pydantic default, a module constant) and a regex that covers all four is
    itself the kind of thing that silently stops matching.
    """
    valid = {t.value for t in RuleSourceTier}

    from backend.mcp.tools.archetypes import mc_in_sign
    from backend.mcp.tools.strategic_patterns import money_contour, vocation_map
    from backend.services.physiognomy.schemas import Reading

    payloads: list[dict] = [
        money_contour("1977-07-01", "22:30", "Europe/Kyiv", 47.85167, 35.11714),
        vocation_map("1977-07-01", "22:30", "Europe/Kyiv", 47.85167, 35.11714),
        mc_in_sign("sagittarius"),
        Reading(system="mianxiang", topic="t", text="…", source="s").model_dump(),
    ]

    seen = 0
    for payload in payloads:
        found = _tiers_in(payload)
        assert found, f"a payload carries no tier at all: {sorted(payload)[:6]}"
        for value in found:
            seen += 1
            assert value in valid, f"unknown tier emitted: {value!r}"
    assert seen >= 4, f"only {seen} tiers found — the walk stopped working"


def _tiers_in(node) -> list[str]:
    """Every `rule_source_tier` value anywhere in a response, at any depth."""
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "rule_source_tier":
                out.extend([value] if isinstance(value, str) else list(value.values()))
            else:
                out.extend(_tiers_in(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_tiers_in(item))
    return out
