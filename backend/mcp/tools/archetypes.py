"""Archetype-interpretation MCP tools.

Exposes the deterministic archetype tables (MC / Sun / Houses / Aspects /
Dignities) as MCP tools the Strategic Analyst can cite as
ASTROLOGY_SYMBOLIC layer evidence with confidence 0.8-0.9 (cited
classical / modern tradition) — NOT as LLM_NARRATIVE (0.7).

All output carries `source` (citation) and `confidence` (numeric).
"""

from __future__ import annotations

from typing import Any

from backend.services.astrology.archetypes import (
    ASPECTS,
    HOUSES,
    MC_IN_SIGN,
    SUN_IN_SIGN,
    ZODIAC_SIGNS,
    essential_dignity,
)
from backend.services.astrology.archetypes.aspects import aspect_archetype
from backend.services.astrology.archetypes.houses import house_archetype
from backend.services.astrology.archetypes.mc_in_sign import mc_archetype
from backend.services.astrology.archetypes.sun_in_sign import sun_archetype
from backend.services.astrology.archetypes.zodiac_signs import sign_archetype
from backend.services.strategic.disclaimer import DISCLAIMER_RU


_LAYER = "astrology_symbolic"
_CONFIDENCE = 0.9  # cited modern/classical tradition


def mc_in_sign(sign: str, locale: str = "ru") -> dict[str, Any]:
    """Return the career-archetype interpretation for MC in a given sign.

    MC (Midheaven) is the public face / career direction, NOT
    "destiny" or "calling". Result includes archetype label, themes,
    description, source citation, layer + numeric confidence.

    Args:
        sign: lowercase English sign name (aries..pisces).
        locale: language for descriptive text (ru default; en supported).
    """
    arc = mc_archetype(sign)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": f"MC in {sign.capitalize()}",
        "archetype": arc["archetype"],
        "themes": arc["themes"],
        "description": arc["description"],
        "source": arc["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def sun_in_sign(sign: str, locale: str = "ru") -> dict[str, Any]:
    """Return the identity-archetype interpretation for Sun in a sign.

    Sun = "I am" / core identity. Different from MC (social role).

    Args:
        sign: lowercase English sign name.
        locale: language.
    """
    arc = sun_archetype(sign)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": f"Sun in {sign.capitalize()}",
        "core_identity": arc["core_identity"],
        "themes": arc["themes"],
        "growth_edge": arc["growth_edge"],
        "description": arc["description"],
        "source": arc["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def house_meaning(house_number: int, locale: str = "ru") -> dict[str, Any]:
    """Return the area-of-life interpretation for an astrological house (1-12).

    Houses describe WHERE energy is invested, not personality traits.

    Args:
        house_number: 1-12.
        locale: language.
    """
    h = house_archetype(house_number)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": f"House {house_number}",
        "name": h["name"],
        "themes": h["themes"],
        "natural_sign": h["natural_sign"],
        "ruler": h["ruler"],
        "description": h["description"],
        "source": h["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def aspect_meaning(aspect_name: str) -> dict[str, Any]:
    """Return the qualitative archetype for a major aspect.

    Args:
        aspect_name: one of conjunction / opposition / trine / square / sextile.
    """
    a = aspect_archetype(aspect_name)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": f"{aspect_name.capitalize()} aspect",
        "angle_deg": a["angle_deg"],
        "default_orb": a["default_orb"],
        "nature": a["nature"],
        "archetype": a["archetype"],
        "description": a["description"],
        "source": a["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def planet_dignity(planet: str, sign: str) -> dict[str, Any]:
    """Return the classical essential-dignity status of a planet in a sign.

    Status is one of: domicile (+5), exaltation (+4), peregrine (0),
    detriment (-5), fall (-4). Score quantifies traditional strength.

    Args:
        planet: lowercase classical planet name (sun/moon/mercury/venus/
            mars/jupiter/saturn).
        sign: lowercase sign name.
    """
    d = essential_dignity(planet, sign)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": f"{planet.capitalize()} in {sign.capitalize()}",
        "status": d["status"],
        "score": d["score"],
        "note": d["note"],
        "source": d["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def zodiac_sign(sign: str) -> dict[str, Any]:
    """Return the elemental archetype of a zodiac sign.

    Args:
        sign: lowercase sign name (aries..pisces).
    """
    s = sign_archetype(sign)
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "subject": sign.capitalize(),
        "element": s["element"],
        "modality": s["modality"],
        "ruler": s["ruler"],
        "keywords": s["keywords"],
        "shadow": s["shadow"],
        "description": s["description"],
        "source": s["source"],
        "disclaimer": DISCLAIMER_RU,
    }


def list_archetype_topics() -> dict[str, Any]:
    """Discoverability: list the available archetype topics + counts.

    Useful for the Strategic Analyst agent to know what hard-table
    archetypes are available before calling.
    """
    return {
        "layer": _LAYER,
        "confidence": _CONFIDENCE,
        "topics": {
            "zodiac_signs": list(ZODIAC_SIGNS.keys()),
            "mc_in_sign": list(MC_IN_SIGN.keys()),
            "sun_in_sign": list(SUN_IN_SIGN.keys()),
            "houses": list(HOUSES.keys()),
            "aspects": list(ASPECTS.keys()),
        },
        "disclaimer": DISCLAIMER_RU,
    }
