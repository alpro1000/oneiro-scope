"""Essential dignities — classical strength of a planet in a sign.

A planet is "essentially dignified" when it sits in a sign it rules
(domicile) or is exalted in. It is "debilitated" when in detriment
(opposite of domicile) or fall (opposite of exaltation).

Sources:
- William Lilly, "Christian Astrology" (1647), Book I — the canonical
  source for traditional rulership tables.
- Deborah Houlding, "The Houses: Temples of the Sky" (Wessex, 2006),
  Appendix A — modern compilation.
- Robert Hand, "Horoscope Symbols" (1981), ch.4.

Confidence: 0.9 (cited classical tradition).

The tables use **traditional** rulerships (Mars rules Scorpio, Saturn
rules Aquarius, Jupiter rules Pisces) — modern rulers (Pluto/Uranus/
Neptune) are NOT used for dignity calculation because they postdate
the tradition. They appear in the data for reference but aren't part
of the dignity score.
"""

# Traditional rulerships: planet → sign(s) it rules.
TRADITIONAL_RULERS: dict[str, list[str]] = {
    "sun": ["leo"],
    "moon": ["cancer"],
    "mercury": ["gemini", "virgo"],
    "venus": ["taurus", "libra"],
    "mars": ["aries", "scorpio"],
    "jupiter": ["sagittarius", "pisces"],
    "saturn": ["capricorn", "aquarius"],
}

# Sign → traditional ruler (reverse).
SIGN_RULERS_TRAD: dict[str, str] = {
    "aries": "mars",
    "taurus": "venus",
    "gemini": "mercury",
    "cancer": "moon",
    "leo": "sun",
    "virgo": "mercury",
    "libra": "venus",
    "scorpio": "mars",
    "sagittarius": "jupiter",
    "capricorn": "saturn",
    "aquarius": "saturn",
    "pisces": "jupiter",
}

# Modern rulers (for reference; do NOT enter the score).
MODERN_RULERS: dict[str, str] = {
    "scorpio": "pluto",
    "aquarius": "uranus",
    "pisces": "neptune",
}

# Exaltations — classical, Lilly 1647.
EXALTATION: dict[str, str] = {
    "sun": "aries",
    "moon": "taurus",
    "mercury": "virgo",
    "venus": "pisces",
    "mars": "capricorn",
    "jupiter": "cancer",
    "saturn": "libra",
}

# Detriment = sign opposite to domicile.
_OPPOSITE = {
    "aries": "libra", "taurus": "scorpio", "gemini": "sagittarius",
    "cancer": "capricorn", "leo": "aquarius", "virgo": "pisces",
    "libra": "aries", "scorpio": "taurus", "sagittarius": "gemini",
    "capricorn": "cancer", "aquarius": "leo", "pisces": "virgo",
}


def _detriment_of(planet: str) -> list[str]:
    return [_OPPOSITE[s] for s in TRADITIONAL_RULERS.get(planet, [])]


def _fall_of(planet: str) -> str | None:
    if planet not in EXALTATION:
        return None
    return _OPPOSITE[EXALTATION[planet]]


DIGNITIES: dict[str, dict] = {}
for planet in TRADITIONAL_RULERS:
    DIGNITIES[planet] = {
        "domicile": TRADITIONAL_RULERS[planet],
        "exaltation": EXALTATION.get(planet),
        "detriment": _detriment_of(planet),
        "fall": _fall_of(planet),
    }


def essential_dignity(planet: str, sign: str) -> dict:
    """Compute classical essential dignity of `planet` in `sign`.

    Returns:
        {
          "status": "domicile" | "exaltation" | "detriment" | "fall" | "peregrine",
          "score": +5 / +4 / -5 / -4 / 0,
          "note": short explanation,
          "source": citation,
        }

    "Peregrine" = no major dignity (neutral baseline).
    """
    p = planet.lower()
    s = sign.lower()

    if p in TRADITIONAL_RULERS and s in TRADITIONAL_RULERS[p]:
        return {
            "status": "domicile",
            "score": 5,
            "note": f"{p.capitalize()} is at home in {s.capitalize()} — full strength.",
            "source": "William Lilly, Christian Astrology (1647), Book I",
        }
    if EXALTATION.get(p) == s:
        return {
            "status": "exaltation",
            "score": 4,
            "note": f"{p.capitalize()} is exalted in {s.capitalize()} — visible, elevated strength.",
            "source": "William Lilly, Christian Astrology (1647), Book I",
        }
    if s in _detriment_of(p):
        return {
            "status": "detriment",
            "score": -5,
            "note": f"{p.capitalize()} is in detriment in {s.capitalize()} — opposed to home sign, weakened.",
            "source": "William Lilly, Christian Astrology (1647), Book I",
        }
    if _fall_of(p) == s:
        return {
            "status": "fall",
            "score": -4,
            "note": f"{p.capitalize()} is in fall in {s.capitalize()} — opposed to exaltation, suppressed.",
            "source": "William Lilly, Christian Astrology (1647), Book I",
        }
    return {
        "status": "peregrine",
        "score": 0,
        "note": f"{p.capitalize()} in {s.capitalize()} has no major essential dignity (peregrine).",
        "source": "William Lilly, Christian Astrology (1647), Book I",
    }
