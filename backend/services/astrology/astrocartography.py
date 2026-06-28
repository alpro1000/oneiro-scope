"""Astrocartography & relocation analysis.

Given a natal chart (date + time + place), compute:

- `relocate(natal_jd, lat, lon)` — the relocated Asc/MC/IC/Desc for any
  city on Earth. House cusps shift; planet zodiacal positions don't.
- `scan_cities(natal_jd, cities, orb)` — for a list of (name, lat, lon),
  return for each city the natal planets that fall on any angle within
  the given orb. The angles are the "doors" planets enter your life
  through in that location.

This is pure astronomy / chart geometry — symbolic interpretation is
the agent's job, not this module's. Output goes into the Strategic
Layer as `Layer.ASTRONOMY` evidence.

Reference: Jim Lewis, "Astro*Carto*Graphy" (1976).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyswisseph is required for astrocartography"
    ) from exc

# Outer-planet calc flags use MOSEPH (analytic Moshier) so the code runs
# without binary ephemeris files. Swap to FLG_SWIEPH at deploy if .se1
# files are present at SE_EPHE_PATH.
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

_PLANET_NAMES = {
    swe.SUN: "Sun",
    swe.MOON: "Moon",
    swe.MERCURY: "Mercury",
    swe.VENUS: "Venus",
    swe.MARS: "Mars",
    swe.JUPITER: "Jupiter",
    swe.SATURN: "Saturn",
    swe.URANUS: "Uranus",
    swe.NEPTUNE: "Neptune",
    swe.PLUTO: "Pluto",
}

_ANGLE_NAMES = ("Asc", "MC", "IC", "Desc")


@dataclass(frozen=True)
class AngleHit:
    """One planet sitting on one of the four angles in a relocated chart."""

    planet: str
    angle: str  # "Asc" | "MC" | "IC" | "Desc"
    orb_deg: float
    planet_longitude: float
    angle_longitude: float


@dataclass(frozen=True)
class RelocationResult:
    """A relocation analysis for one city."""

    city: str
    latitude: float
    longitude: float
    asc: float
    mc: float
    ic: float
    desc: float
    angle_hits: list[AngleHit]
    # Weighted score for ranking (Venus/Jupiter on angles boost it,
    # Saturn/Pluto on angles deduct).
    score: float


def natal_planets(jd_ut: float) -> dict[str, float]:
    """Compute zodiacal longitudes of the main bodies at natal moment."""
    out: dict[str, float] = {}
    for p, name in _PLANET_NAMES.items():
        res, _ = swe.calc_ut(jd_ut, p, _FLAGS)
        out[name] = res[0]
    return out


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest angular distance between two longitudes (0-180°)."""
    d = abs(a - b) % 360
    if d > 180:
        d = 360 - d
    return d


def relocate(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    planets: Optional[dict[str, float]] = None,
    orb_deg: float = 7.0,
) -> RelocationResult:
    """Compute the relocated Asc/MC/IC/Desc for `(lat, lon)` at the given
    natal moment and list which natal planets fall on any angle within
    `orb_deg`.
    """
    if planets is None:
        planets = natal_planets(jd_ut)

    cusps, ascmc = swe.houses(jd_ut, latitude, longitude, b"P")
    asc = ascmc[0]
    mc = ascmc[1]
    ic = (mc + 180.0) % 360.0
    desc = (asc + 180.0) % 360.0

    angles = {"Asc": asc, "MC": mc, "IC": ic, "Desc": desc}

    hits: list[AngleHit] = []
    for angle_name, angle_lon in angles.items():
        for planet_name, plon in planets.items():
            orb = _angle_diff_deg(plon, angle_lon)
            if orb <= orb_deg:
                hits.append(
                    AngleHit(
                        planet=planet_name,
                        angle=angle_name,
                        orb_deg=round(orb, 2),
                        planet_longitude=round(plon, 4),
                        angle_longitude=round(angle_lon, 4),
                    )
                )

    score = _score_hits(hits)
    return RelocationResult(
        city=f"({latitude:.4f},{longitude:.4f})",
        latitude=latitude,
        longitude=longitude,
        asc=round(asc, 4),
        mc=round(mc, 4),
        ic=round(ic, 4),
        desc=round(desc, 4),
        angle_hits=hits,
        score=score,
    )


# Weights for the heuristic score. Astrology tradition treats Venus/Jupiter
# as benefics, Saturn/Pluto/Mars as challenging on angles. Sun/Moon are
# strong but neutral.
_BENEFICS = {"Venus": 3.0, "Jupiter": 3.0, "Sun": 1.0, "Moon": 1.0}
_MALEFICS = {"Saturn": -1.5, "Pluto": -1.5, "Mars": -1.0}
_ANGLE_WEIGHT = {"Asc": 2.0, "MC": 2.0, "IC": 1.5, "Desc": 1.0}


def _score_hits(hits: list[AngleHit]) -> float:
    """Heuristic: sum of (planet weight) * (angle weight) * orb falloff."""
    total = 0.0
    for h in hits:
        pw = _BENEFICS.get(h.planet, 0) + _MALEFICS.get(h.planet, 0)
        aw = _ANGLE_WEIGHT[h.angle]
        # Linear falloff to zero at orb_deg=7.
        falloff = max(0.0, 1.0 - h.orb_deg / 7.0)
        total += pw * aw * falloff
    return round(total, 2)


def scan_cities(
    jd_ut: float,
    cities: list[tuple[str, float, float]],
    *,
    orb_deg: float = 7.0,
) -> list[RelocationResult]:
    """Run `relocate` for each `(name, lat, lon)` city, sorted by score
    descending. Planets are computed once."""
    planets = natal_planets(jd_ut)
    results = []
    for name, lat, lon in cities:
        r = relocate(jd_ut, lat, lon, planets=planets, orb_deg=orb_deg)
        results.append(
            RelocationResult(
                city=name,
                latitude=lat,
                longitude=lon,
                asc=r.asc,
                mc=r.mc,
                ic=r.ic,
                desc=r.desc,
                angle_hits=r.angle_hits,
                score=r.score,
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
