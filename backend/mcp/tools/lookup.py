"""One reference-lookup tool for the whole knowledge base (WP-10).

Fifteen single-purpose lookup tools (list_* + per-key archetype readings)
used to crowd the registry: every one was a dictionary access with a
different name, and together they drowned the ~15 tools that actually
compute something over a person. They are folded into this single
dispatcher; the underlying module functions stay where they were, so the
web API and tests keep calling them directly.

A lookup is not a step in a reading — it attaches no capability menu
(the same rule the individual lookup tools followed).
"""

from __future__ import annotations

from typing import Any, Optional

from backend.mcp.tools import archetypes as ar
from backend.mcp.tools import astrology as a
from backend.mcp.tools import dreams as d

# topic → (callable, required argument names in call order)
_TOPICS: dict[str, tuple[Any, tuple[str, ...]]] = {
    "zodiac_sign": (ar.zodiac_sign, ("sign",)),
    "sun_in_sign": (ar.sun_in_sign, ("sign",)),
    "mc_in_sign": (ar.mc_in_sign, ("sign",)),
    "house_meaning": (ar.house_meaning, ("house_number",)),
    "planet_in_house": (ar.planet_in_house, ("planet", "house_number")),
    "planet_dignity": (ar.planet_dignity, ("planet", "sign")),
    "aspect_meaning": (ar.aspect_meaning, ("aspect",)),
    "transit_meaning": (ar.transit_meaning, ("transiting", "aspect", "natal")),
    "archetype_topics": (ar.list_archetype_topics, ()),
    "event_types": (a.list_event_types, ()),
    "horoscope_periods": (a.list_horoscope_periods, ()),
    "dream_symbols": (d.list_dream_symbols, ()),
    "dream_archetypes": (d.list_archetypes, ()),
    "hvdc_categories": (d.list_hvdc_categories, ()),
}

# Which functions accept a locale keyword.
_LOCALE_AWARE = {
    "zodiac_sign": False,
    "sun_in_sign": True,
    "mc_in_sign": True,
    "house_meaning": True,
    "planet_in_house": False,
    "planet_dignity": False,
    "aspect_meaning": False,
    "transit_meaning": False,
    "archetype_topics": False,
    "event_types": False,
    "horoscope_periods": False,
    "dream_symbols": True,
    "dream_archetypes": True,
    "hvdc_categories": True,
}


def lookup(
    topic: str,
    sign: Optional[str] = None,
    planet: Optional[str] = None,
    house_number: Optional[int] = None,
    aspect: Optional[str] = None,
    transiting: Optional[str] = None,
    natal: Optional[str] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Reference lookups from the knowledge base — one tool, many topics.

    Pure dictionary reads with cited sources (confidence 0.8–0.9, never
    computed over a person). Topics and their required arguments:

    - "zodiac_sign" (sign) — sign profile: element, ruler, traits.
    - "sun_in_sign" (sign) — Sun-in-sign reading.
    - "mc_in_sign" (sign) — Midheaven in sign: vocation themes.
    - "house_meaning" (house_number 1-12) — what the house governs.
    - "planet_in_house" (planet, house_number) — placement reading.
    - "planet_dignity" (planet, sign) — rulership/exaltation/fall/detriment.
    - "aspect_meaning" (aspect: conjunction/sextile/square/trine/quincunx/
      opposition) — how the angle works.
    - "transit_meaning" (transiting, aspect, natal) — transit reading.
    - "archetype_topics" — index of available archetype tables.
    - "event_types" — event kinds `forecast_event` accepts.
    - "horoscope_periods" — periods the horoscope API accepts.
    - "dream_symbols" — the dream symbol dictionary (56 symbols).
    - "dream_archetypes" — Jungian archetypes used by dream analysis.
    - "hvdc_categories" — Hall/Van de Castle content categories.

    Args:
        topic: One of the topics above.
        sign: Zodiac sign name, where required ("leo", "лев" accepted by
            the underlying tables' matching).
        planet: Planet name, where required.
        house_number: House 1-12, where required.
        aspect: Aspect name, where required.
        transiting: Transiting planet (transit_meaning only).
        natal: Natal planet (transit_meaning only).
        locale: "ru" or "en" for topics that carry bilingual text.
    """
    entry = _TOPICS.get(topic)
    if entry is None:
        return {
            "error": f"unknown topic {topic!r}",
            "topics": sorted(_TOPICS),
        }
    fn, required = entry
    provided = {
        "sign": sign,
        "planet": planet,
        "house_number": house_number,
        "aspect": aspect,
        "transiting": transiting,
        "natal": natal,
    }
    missing = [name for name in required if provided[name] is None]
    if missing:
        return {
            "error": f"topic {topic!r} requires: {', '.join(required)}",
            "missing": missing,
        }

    args = [provided[name] for name in required]
    # aspect_meaning's parameter is aspect_name; transit_meaning's middle
    # argument is the aspect — positional call keeps both simple.
    out = fn(*args, locale=locale) if _LOCALE_AWARE[topic] else fn(*args)

    if isinstance(out, dict):
        out.setdefault("topic", topic)
        return out
    return {"topic": topic, "items": out}
