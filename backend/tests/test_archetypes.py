"""Tests for hard archetype tables (MC / Sun / Houses / Aspects /
Dignities) and the corresponding MCP tools.

These tables are pure data — tests verify structure, completeness
(all 12 signs / 12 houses / 5 aspects), required fields, and that
every entry carries a source citation.
"""

from __future__ import annotations

import pytest


# ---------- Zodiac signs ---------------------------------------------------


def test_zodiac_signs_complete():
    from backend.services.astrology.archetypes import ZODIAC_SIGNS

    expected = {
        "aries", "taurus", "gemini", "cancer",
        "leo", "virgo", "libra", "scorpio",
        "sagittarius", "capricorn", "aquarius", "pisces",
    }
    assert set(ZODIAC_SIGNS) == expected


@pytest.mark.parametrize("sign", [
    "aries", "taurus", "gemini", "cancer",
    "leo", "virgo", "libra", "scorpio",
    "sagittarius", "capricorn", "aquarius", "pisces",
])
def test_every_zodiac_sign_has_required_fields(sign):
    from backend.services.astrology.archetypes import ZODIAC_SIGNS

    data = ZODIAC_SIGNS[sign]
    for field in ("element", "modality", "ruler", "keywords",
                  "shadow", "description", "source"):
        assert field in data, f"{sign} missing {field}"
    assert data["element"] in ("fire", "earth", "air", "water")
    assert data["modality"] in ("cardinal", "fixed", "mutable")
    assert len(data["keywords"]) >= 3
    assert len(data["source"]) > 10  # non-trivial citation


def test_sign_archetype_lookup():
    from backend.services.astrology.archetypes.zodiac_signs import sign_archetype

    cancer = sign_archetype("Cancer")
    assert cancer["element"] == "water"
    assert cancer["ruler"] == "moon"


def test_sign_archetype_unknown_raises():
    from backend.services.astrology.archetypes.zodiac_signs import sign_archetype

    with pytest.raises(KeyError):
        sign_archetype("nonexistent")


# ---------- MC in sign -----------------------------------------------------


def test_mc_in_sign_complete():
    from backend.services.astrology.archetypes import MC_IN_SIGN

    assert len(MC_IN_SIGN) == 12


@pytest.mark.parametrize("sign", [
    "scorpio", "sagittarius", "capricorn", "leo",
])
def test_mc_in_sign_has_archetype_and_source(sign):
    from backend.services.astrology.archetypes import MC_IN_SIGN

    data = MC_IN_SIGN[sign]
    for field in ("archetype", "themes", "description", "source"):
        assert field in data
    assert "(" in data["source"] and ")" in data["source"]  # year citation


def test_mc_scorpio_is_investigator_archetype():
    """MC Scorpio = "Investigator/Transformer" archetype (deep work)."""
    from backend.services.astrology.archetypes.mc_in_sign import mc_archetype

    arc = mc_archetype("scorpio")
    assert "Investigator" in arc["archetype"]


# ---------- Sun in sign ----------------------------------------------------


def test_sun_in_sign_complete():
    from backend.services.astrology.archetypes import SUN_IN_SIGN

    assert len(SUN_IN_SIGN) == 12


@pytest.mark.parametrize("sign", ["aries", "cancer", "leo", "capricorn", "pisces"])
def test_sun_in_sign_has_growth_edge(sign):
    """Sun archetype must include 'growth_edge' — the developmental task."""
    from backend.services.astrology.archetypes import SUN_IN_SIGN

    assert "growth_edge" in SUN_IN_SIGN[sign]
    assert len(SUN_IN_SIGN[sign]["growth_edge"]) > 15


# ---------- Houses ---------------------------------------------------------


def test_houses_1_through_12():
    from backend.services.astrology.archetypes import HOUSES

    assert set(HOUSES) == set(range(1, 13))


@pytest.mark.parametrize("house_num", range(1, 13))
def test_house_has_natural_ruler_and_source(house_num):
    from backend.services.astrology.archetypes import HOUSES

    h = HOUSES[house_num]
    for field in ("name", "themes", "natural_sign", "ruler",
                  "description", "source"):
        assert field in h


def test_house_lookup_invalid_raises():
    from backend.services.astrology.archetypes.houses import house_archetype

    with pytest.raises(KeyError):
        house_archetype(13)


# ---------- Aspects --------------------------------------------------------


def test_all_five_aspects_present():
    from backend.services.astrology.archetypes import ASPECTS

    assert set(ASPECTS) == {
        "conjunction", "opposition", "trine", "square", "sextile"
    }


def test_aspect_orbs_match_domain_defaults():
    """Defaults must match docs/steering/domain.md §2.3 table."""
    from backend.services.astrology.archetypes import ASPECTS

    assert ASPECTS["conjunction"]["default_orb"] == 8.0
    assert ASPECTS["opposition"]["default_orb"] == 8.0
    assert ASPECTS["trine"]["default_orb"] == 7.0
    assert ASPECTS["square"]["default_orb"] == 7.0
    assert ASPECTS["sextile"]["default_orb"] == 5.0


def test_aspect_angles_correct():
    from backend.services.astrology.archetypes import ASPECTS

    assert ASPECTS["conjunction"]["angle_deg"] == 0
    assert ASPECTS["opposition"]["angle_deg"] == 180
    assert ASPECTS["trine"]["angle_deg"] == 120
    assert ASPECTS["square"]["angle_deg"] == 90
    assert ASPECTS["sextile"]["angle_deg"] == 60


# ---------- Dignities ------------------------------------------------------


def test_dignity_sun_in_leo_is_domicile():
    from backend.services.astrology.archetypes import essential_dignity

    d = essential_dignity("sun", "leo")
    assert d["status"] == "domicile"
    assert d["score"] == 5


def test_dignity_mars_in_capricorn_is_exaltation():
    from backend.services.astrology.archetypes import essential_dignity

    d = essential_dignity("mars", "capricorn")
    assert d["status"] == "exaltation"
    assert d["score"] == 4


def test_dignity_sun_in_aquarius_is_detriment():
    from backend.services.astrology.archetypes import essential_dignity

    d = essential_dignity("sun", "aquarius")
    assert d["status"] == "detriment"
    assert d["score"] == -5


def test_dignity_saturn_in_aries_is_fall():
    from backend.services.astrology.archetypes import essential_dignity

    d = essential_dignity("saturn", "aries")
    assert d["status"] == "fall"
    assert d["score"] == -4


def test_dignity_peregrine_when_no_status():
    from backend.services.astrology.archetypes import essential_dignity

    # Venus in Sagittarius — no major dignity.
    d = essential_dignity("venus", "sagittarius")
    assert d["status"] == "peregrine"
    assert d["score"] == 0


def test_traditional_rulership_table():
    """Mars rules both Aries and Scorpio (traditional)."""
    from backend.services.astrology.archetypes.dignities import TRADITIONAL_RULERS

    assert "aries" in TRADITIONAL_RULERS["mars"]
    assert "scorpio" in TRADITIONAL_RULERS["mars"]
    assert "capricorn" in TRADITIONAL_RULERS["saturn"]
    assert "aquarius" in TRADITIONAL_RULERS["saturn"]


# ---------- MCP tool wrappers ----------------------------------------------


def test_mc_in_sign_tool_carries_layer_confidence_disclaimer():
    from backend.mcp.tools.archetypes import mc_in_sign

    r = mc_in_sign("scorpio")
    assert r["layer"] == "astrology_symbolic"
    assert r["confidence"] == 0.9
    assert "disclaimer" in r
    assert len(r["disclaimer"]) > 30


def test_house_meaning_tool_returns_full_record():
    from backend.mcp.tools.archetypes import house_meaning

    r = house_meaning(10)
    assert r["subject"] == "House 10"
    assert r["name"] == "House of Career and Public Role"
    assert r["natural_sign"] == "capricorn"


def test_planet_dignity_tool_for_sun_leo():
    from backend.mcp.tools.archetypes import planet_dignity

    r = planet_dignity("sun", "leo")
    assert r["status"] == "domicile"
    assert r["score"] == 5


def test_list_archetype_topics_includes_all_categories():
    from backend.mcp.tools.archetypes import list_archetype_topics

    r = list_archetype_topics()
    topics = r["topics"]
    assert set(topics) == {
        "zodiac_signs", "mc_in_sign", "sun_in_sign", "houses", "aspects",
    }
    assert len(topics["zodiac_signs"]) == 12
    assert len(topics["mc_in_sign"]) == 12
    assert len(topics["sun_in_sign"]) == 12
    assert len(topics["houses"]) == 12
    assert len(topics["aspects"]) == 5
