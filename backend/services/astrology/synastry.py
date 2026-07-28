"""Synastry — inter-chart aspects between two people.

Computes the classical compatibility geometry: every aspect between
person A's natal bodies and person B's natal bodies, categorised into
relationship dimensions (attraction, emotional bond, communication,
stability, tension) with a deterministic weighted score per dimension.

The geometry is ASTRONOMY (confidence 1.0). Dimension scores and the
summary are a classical rule-set (symbol tier, ~0.8) — reflective
phrasing only, never a verdict on a relationship.
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for synastry") from exc

from backend.core.ephemeris import FLAGS as _FLAGS

_BODIES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

# Aspect angles with synastry orbs (tighter for minor personal contacts).
_ASPECTS = {
    "conjunction": (0.0, 7.0),
    "sextile": (60.0, 4.0),
    "square": (90.0, 6.0),
    "trine": (120.0, 6.0),
    "opposition": (180.0, 7.0),
}

_HARMONIOUS = {"trine", "sextile"}
_TENSE = {"square", "opposition"}
# Conjunction nature depends on the planet pair (resolved below).
_SOFT_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Jupiter"}

# Dimension membership: which planet pairs feed which relationship theme.
_PERSONAL = {"Sun", "Moon", "Mercury", "Venus", "Mars"}


@dataclass(frozen=True)
class SynastryAspect:
    person_a_planet: str
    person_b_planet: str
    aspect: str
    orb_deg: float
    nature: str  # "harmonious" | "tense" | "intense"


@dataclass
class SynastryResult:
    aspects: list[SynastryAspect] = field(default_factory=list)
    dimensions: dict[str, float] = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)
    overall_score: float = 0.0


def natal_longitudes(jd_ut: float) -> dict[str, float]:
    return {
        name: swe.calc_ut(jd_ut, code, _FLAGS)[0][0]
        for name, code in _BODIES.items()
    }


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def _conjunction_nature(pa: str, pb: str) -> str:
    """Conjunction reads by the heavier planet: soft pairs bond,
    Saturn/Mars/Pluto contacts are intense rather than plainly tense."""
    if pa in _SOFT_PLANETS and pb in _SOFT_PLANETS:
        return "harmonious"
    return "intense"


def _pair_key(pa: str, pb: str) -> frozenset:
    return frozenset((pa, pb))


def compute_synastry(jd_a: float, jd_b: float) -> SynastryResult:
    """All inter-aspects between chart A and chart B + dimension scores."""
    lons_a = natal_longitudes(jd_a)
    lons_b = natal_longitudes(jd_b)

    aspects: list[SynastryAspect] = []
    for pa, la in lons_a.items():
        for pb, lb in lons_b.items():
            sep = _angle_diff(la, lb)
            for name, (angle, orb) in _ASPECTS.items():
                dev = abs(sep - angle)
                if dev <= orb:
                    if name in _HARMONIOUS:
                        nature = "harmonious"
                    elif name in _TENSE:
                        nature = "tense"
                    else:
                        nature = _conjunction_nature(pa, pb)
                    aspects.append(
                        SynastryAspect(pa, pb, name, round(dev, 2), nature)
                    )
                    break

    result = SynastryResult(aspects=aspects)
    _score_dimensions(result)
    return result


def _weight(orb: float, max_orb: float = 7.0) -> float:
    return max(0.0, 1.0 - orb / max_orb)


def _score_dimensions(result: SynastryResult) -> None:
    """Classical dimension scoring. Each dimension accumulates weighted
    contributions; final value normalised to 0–100 via a soft cap."""
    dims = {
        "attraction": 0.0,      # Venus/Mars/Pluto cross-contacts
        "emotional": 0.0,       # Moon and Sun-Moon contacts
        "communication": 0.0,   # Mercury contacts
        "stability": 0.0,       # harmonious Saturn/Jupiter contacts
        "tension": 0.0,         # squares/oppositions of personal planets
    }
    highlights: list[str] = []

    for a in result.aspects:
        pair = _pair_key(a.person_a_planet, a.person_b_planet)
        w = _weight(a.orb_deg)
        harmonious = a.nature == "harmonious"
        tense = a.nature == "tense"

        if pair & {"Venus", "Mars"} and pair & {"Venus", "Mars", "Pluto", "Sun"}:
            if harmonious or a.aspect == "conjunction":
                dims["attraction"] += 2.0 * w
            elif tense:
                dims["attraction"] += 1.0 * w  # friction still magnetises
                dims["tension"] += 1.0 * w
        if "Moon" in pair:
            if harmonious:
                dims["emotional"] += 2.0 * w
            elif tense:
                dims["tension"] += 1.5 * w
            elif a.nature == "intense":
                dims["emotional"] += 1.0 * w
        if pair == frozenset({"Sun", "Moon"}):
            dims["emotional"] += 2.0 * w
            if harmonious or a.aspect == "conjunction":
                highlights.append(
                    "Sun–Moon contact — the classical marriage signature"
                )
        if "Mercury" in pair and (pair & _PERSONAL) - {"Mercury"}:
            if harmonious or a.aspect == "conjunction":
                dims["communication"] += 1.5 * w
            elif tense:
                dims["tension"] += 0.8 * w
        if "Saturn" in pair and pair & _PERSONAL:
            if harmonious:
                dims["stability"] += 2.0 * w
            else:
                dims["tension"] += 1.2 * w
                highlights.append(
                    f"Saturn contact ({a.person_a_planet}–{a.person_b_planet} "
                    f"{a.aspect}) — commitment that asks for work"
                )
        if "Jupiter" in pair and pair & _PERSONAL and harmonious:
            dims["stability"] += 1.0 * w
        if tense and pair <= _PERSONAL:
            dims["tension"] += 0.5 * w

    # Normalise each dimension to 0–100 with a soft cap at raw 6.0.
    for k, raw in dims.items():
        dims[k] = round(min(100.0, raw / 6.0 * 100.0), 1)

    positive = (
        dims["attraction"] + dims["emotional"]
        + dims["communication"] + dims["stability"]
    ) / 4.0
    result.dimensions = dims
    result.highlights = highlights[:6]
    result.overall_score = round(
        max(0.0, min(100.0, positive - dims["tension"] * 0.25)), 1
    )


def synastry_summary(result: SynastryResult, locale: str = "ru") -> dict:
    """Plain-language reflective summary of the dimension profile."""
    d = result.dimensions
    strongest = max(d, key=lambda k: d[k] if k != "tension" else -1)
    ru = locale == "ru"
    names_ru = {
        "attraction": "притяжение",
        "emotional": "эмоциональная связь",
        "communication": "общение",
        "stability": "устойчивость",
    }
    if ru:
        lead = (
            f"Сильнейшая сторона пары — {names_ru.get(strongest, strongest)}."
        )
        if d["tension"] >= 50:
            caveat = (
                " Напряжённых контактов много: связь живая, но требует "
                "работы и терпения."
            )
        elif d["tension"] >= 25:
            caveat = " Есть рабочие трения — они дают паре динамику."
        else:
            caveat = " Фон спокойный, с небольшим количеством трений."
    else:
        lead = f"The pair's strongest side is {strongest}."
        if d["tension"] >= 50:
            caveat = (
                " Tense contacts are numerous: a vivid bond that asks for "
                "work and patience."
            )
        elif d["tension"] >= 25:
            caveat = " Some working friction — it keeps the pair dynamic."
        else:
            caveat = " A calm background with little friction."
    return {
        "plain": lead + caveat,
        "dimensions": d,
        "highlights": result.highlights,
        "overall_score": result.overall_score,
        "confidence": 0.8,
        "source": "classical synastry rule-set (inter-chart aspects)",
    }
