"""Orb policies for natal and transit aspects."""

from __future__ import annotations

NATAL_DEFAULT = {
    "luminaries": 10.0,
    "personal": 8.0,
    "social": 7.0,
    "outer": 6.0,
    "angles": 5.0,
}

TRANSIT_DEFAULT = {
    "sun_moon": 2.5,
    "personal": 2.0,
    "social": 1.5,
    "outer": 1.0,
}


def natal_orb_for(body: str) -> float:
    if body in {"sun", "moon"}:
        return NATAL_DEFAULT["luminaries"]
    if body in {"mercury", "venus", "mars"}:
        return NATAL_DEFAULT["personal"]
    if body in {"jupiter", "saturn"}:
        return NATAL_DEFAULT["social"]
    return NATAL_DEFAULT["outer"]


def transit_orb_for(transit_body: str) -> float:
    if transit_body in {"sun", "moon"}:
        return TRANSIT_DEFAULT["sun_moon"]
    if transit_body in {"mercury", "venus", "mars"}:
        return TRANSIT_DEFAULT["personal"]
    if transit_body in {"jupiter", "saturn"}:
        return TRANSIT_DEFAULT["social"]
    return TRANSIT_DEFAULT["outer"]
