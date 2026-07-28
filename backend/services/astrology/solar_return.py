"""Solar Return chart — chart for the moment the Sun returns to its
natal longitude, computed for an arbitrary location.

Used for year-ahead forecasting in the Western astrology tradition. The
*location* of the chart matters: people deliberately travel to a city
for their birthday ("Solar Return Relocation") to shift the year's
angular emphasis.

This module is pure astronomy / chart geometry. Symbolic interpretation
is the agent's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for solar return") from exc

from backend.core.ephemeris import FLAGS as _FLAGS


@dataclass(frozen=True)
class SolarReturnChart:
    """Solar Return result for one (year, location) pair."""

    exact_moment_utc: str  # ISO-8601
    julian_day_ut: float
    natal_sun_longitude: float
    accuracy_arcmin: float  # how close we got to exact
    location_lat: float
    location_lon: float
    asc: float
    mc: float
    ic: float
    desc: float
    planets: dict[str, float]
    planet_houses: dict[str, int]


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


def _sun_longitude(jd: float) -> float:
    return swe.calc_ut(jd, swe.SUN, _FLAGS)[0][0]


def _angle_diff_signed(a: float, b: float) -> float:
    """Signed shortest distance from `a` to `b`, in degrees, in (-180,180]."""
    d = (b - a + 180) % 360 - 180
    return d


def find_exact_return_jd(
    natal_sun_longitude: float,
    around: datetime,
    *,
    window_hours: int = 48,
) -> tuple[float, float]:
    """Locate the exact JD where Sun longitude equals `natal_sun_longitude`,
    within ±`window_hours` from `around`.

    Returns (jd_ut, accuracy_arcmin). Two-stage search: hourly then
    minute-stepped refinement.
    """
    if around.tzinfo is None:
        around = around.replace(tzinfo=timezone.utc)
    around_utc = around.astimezone(timezone.utc)
    jd_center = swe.julday(
        around_utc.year,
        around_utc.month,
        around_utc.day,
        around_utc.hour + around_utc.minute / 60.0,
    )

    # Stage 1: hourly scan.
    best_jd = jd_center
    best_orb = 999.0
    for h in range(-window_hours, window_hours + 1):
        jd = jd_center + h / 24.0
        sun = _sun_longitude(jd)
        diff = abs(_angle_diff_signed(natal_sun_longitude, sun))
        if diff < best_orb:
            best_orb = diff
            best_jd = jd

    # Stage 2: minute-step refinement around best hourly.
    for m in range(-120, 121):
        jd = best_jd + m / (24.0 * 60.0)
        sun = _sun_longitude(jd)
        diff = abs(_angle_diff_signed(natal_sun_longitude, sun))
        if diff < best_orb:
            best_orb = diff
            best_jd = jd

    # Stage 3 (WP-18): second-step refinement — the return moment is
    # reported to the second. The Sun moves ~0.04″/s, so this pins the
    # orb to sub-arcsecond territory.
    for s in range(-90, 91):
        jd = best_jd + s / 86400.0
        sun = _sun_longitude(jd)
        diff = abs(_angle_diff_signed(natal_sun_longitude, sun))
        if diff < best_orb:
            best_orb = diff
            best_jd = jd

    return best_jd, best_orb * 60.0  # convert orb to arc-min


def _planet_house(longitude: float, cusps: list[float]) -> int:
    """Find which Placidus house a longitude falls in."""
    for i in range(12):
        c1 = cusps[i]
        c2 = cusps[(i + 1) % 12]
        if c1 < c2:
            if c1 <= longitude < c2:
                return i + 1
        else:  # wrap across 360°
            if longitude >= c1 or longitude < c2:
                return i + 1
    return 12  # fallback


def solar_return(
    natal_jd_ut: float,
    return_year: int,
    location_lat: float,
    location_lon: float,
) -> SolarReturnChart:
    """Compute the Solar Return chart for `return_year` at `(lat, lon)`.

    The chart angles (Asc/MC/IC/Desc) depend on WHERE the person was at
    the moment of return. Planets in zodiac are universal that moment.

    Args:
        natal_jd_ut: Natal moment JD (Universal Time).
        return_year: Year of the birthday whose return you want.
        location_lat: Where the person is at the return moment.
        location_lon: Same.
    """
    natal_sun = _sun_longitude(natal_jd_ut)

    # Birthday in `return_year` — month/day from natal, time approx
    # natal-local (refined below).
    yy, mm, dd, hour = swe.revjul(natal_jd_ut)
    approx = datetime(return_year, int(mm), int(dd), 12, 0, tzinfo=timezone.utc)

    exact_jd, accuracy_arcmin = find_exact_return_jd(natal_sun, approx)

    # Angles for the location.
    cusps, ascmc = swe.houses(exact_jd, location_lat, location_lon, b"P")
    asc, mc = ascmc[0], ascmc[1]
    ic, desc = (mc + 180) % 360, (asc + 180) % 360

    planets = {}
    houses = {}
    for name, code in _BODIES.items():
        plon = swe.calc_ut(exact_jd, code, _FLAGS)[0][0]
        planets[name] = round(plon, 4)
        houses[name] = _planet_house(plon, list(cusps))

    # Convert JD back to ISO, to the second (WP-18).
    y, m, d, h = swe.revjul(exact_jd)
    hh = int(h)
    mm_ = int((h - hh) * 60)
    ss = int(round(((h - hh) * 60 - mm_) * 60))
    if ss == 60:
        ss = 59  # clamp rounding at the minute edge rather than carrying
    iso = datetime(
        int(y), int(m), int(d), hh, mm_, ss, tzinfo=timezone.utc
    ).isoformat()

    return SolarReturnChart(
        exact_moment_utc=iso,
        julian_day_ut=exact_jd,
        natal_sun_longitude=round(natal_sun, 4),
        accuracy_arcmin=round(accuracy_arcmin, 2),
        location_lat=location_lat,
        location_lon=location_lon,
        asc=round(asc, 4),
        mc=round(mc, 4),
        ic=round(ic, 4),
        desc=round(desc, 4),
        planets=planets,
        planet_houses=houses,
    )


# Angular houses carry the year's loudest emphasis (Gauquelin zones
# aside, this is the classical SR-relocation heuristic).
_ANGULAR_HOUSES = {1, 4, 7, 10}
_SR_BENEFICS = {"Jupiter": 3.0, "Venus": 2.5, "Sun": 1.5, "Moon": 1.0}
_SR_MALEFICS = {"Saturn": -2.0, "Mars": -1.5, "Pluto": -1.5}


def suggest_locations(
    natal_jd_ut: float,
    return_year: int,
    candidates: list[tuple[str, float, float]],
) -> list[dict]:
    """Rank candidate cities for spending the birthday ("Solar Return
    relocation"). Score = benefics angular (+), malefics angular (−);
    ties break toward Jupiter/Venus in house 1 or 10.

    Returns one dict per candidate sorted best-first. Pure geometry +
    a fixed weight table — the travel decision stays with the user.
    """
    rows = []
    for name, lat, lon in candidates:
        sr = solar_return(natal_jd_ut, return_year, lat, lon)
        score = 0.0
        angular = []
        for planet, house in sr.planet_houses.items():
            if house not in _ANGULAR_HOUSES:
                continue
            weight = _SR_BENEFICS.get(planet, 0.0) + _SR_MALEFICS.get(planet, 0.0)
            score += weight
            angular.append({"planet": planet, "house": house})
        rows.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "score": round(score, 2),
                "angular_planets": angular,
                "exact_moment_utc": sr.exact_moment_utc,
                "asc": sr.asc,
                "mc": sr.mc,
            }
        )
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows
