"""Strategic-astronomy MCP tools.

Adds three new tools that surface deterministic chart computations as
ASTRONOMY-layer evidence the Strategic Life Cycle Analyst agent can
cite. None of these return interpretation — only data.

- `compute_transits` — list exact-date transits over a window.
- `astrocartography_scan` — for a list of cities, which natal planets
  fall on the relocated angles.
- `solar_return_chart` — birthday-return chart for an arbitrary city
  (Solar Return Relocation).
"""

from __future__ import annotations

from datetime import date as date_cls, datetime, time as time_cls, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph required") from exc


from backend.services.astrology.astrocartography import (
    AngleHit,
    RelocationResult,
    acg_lines,
    chart_geometry,
    relocate,
    relocation_summary,
    scan_cities,
)
from backend.services.astrology.solar_return import solar_return as _solar_return
from backend.services.astrology.transits_engine import find_transits


def _natal_jd(
    birth_date: str, birth_time: str, birth_tz: str = "UTC"
) -> float:
    """Convert local birth datetime → JD UT."""
    d = date_cls.fromisoformat(birth_date)
    t = time_cls.fromisoformat(birth_time)
    local = datetime(
        d.year, d.month, d.day, t.hour, t.minute, t.second,
        tzinfo=ZoneInfo(birth_tz),
    )
    utc = local.astimezone(timezone.utc)
    return swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60.0 + utc.second / 3600.0,
    )


async def compute_transits(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    start: str,
    end: str,
    orb_deg: float = 3.0,
) -> dict[str, Any]:
    """Compute exact-date major transits over a window.

    Returns a deterministic list of (transiting_planet, aspect, natal_planet,
    exact_date, orb) — the agent uses this as ASTRONOMY-layer evidence
    before any symbolic interpretation.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM:SS of birth (local clock).
        birth_timezone: IANA tz of birth (e.g. "Europe/Kyiv").
        start: YYYY-MM-DD window start (inclusive).
        end: YYYY-MM-DD window end (inclusive).
        orb_deg: Max orb at midnight UT to register an event. 3° is the
            standard for "tight" transits; 5° for "wider."
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    start_d = date_cls.fromisoformat(start)
    end_d = date_cls.fromisoformat(end)
    events = find_transits(jd, start_d, end_d, orb_deg=orb_deg)
    return {
        "layer": "astronomy",
        "methodology": "Swiss Ephemeris (MOSEPH analytic); orb at midnight UT",
        "window": {"start": start, "end": end, "orb_deg": orb_deg},
        "transit_count": len(events),
        "transits": [
            {
                "transiting": e.transiting,
                "aspect": e.aspect,
                "natal": e.natal,
                "exact_date": e.exact_date,
                "orb_at_midnight": e.orb_at_midnight,
            }
            for e in events
        ],
    }


def _hit_to_dict(h: AngleHit) -> dict:
    return {
        "planet": h.planet,
        "angle": h.angle,
        "orb_deg": h.orb_deg,
        "planet_longitude": h.planet_longitude,
        "angle_longitude": h.angle_longitude,
    }


def _result_to_dict(r: RelocationResult) -> dict:
    return {
        "city": r.city,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "asc": r.asc,
        "mc": r.mc,
        "ic": r.ic,
        "desc": r.desc,
        "angle_hits": [_hit_to_dict(h) for h in r.angle_hits],
        "score": r.score,
    }


async def astrocartography_scan(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    cities: list[dict[str, Any]],
    orb_deg: float = 7.0,
) -> dict[str, Any]:
    """Scan a list of cities and report which natal planets fall on the
    relocated Asc/MC/IC/Desc within `orb_deg`.

    Returns deterministic geometry — NOT interpretation. The agent
    treats output as ASTRONOMY-layer evidence and explains symbolism
    separately at the ASTROLOGY_SYMBOLIC layer.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local.
        birth_timezone: IANA tz of birth.
        cities: List of `{"name":..., "lat":..., "lon":...}` dicts.
        orb_deg: Aspect orb (default 7°, classical for angles).
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    tuples = [(c["name"], float(c["lat"]), float(c["lon"])) for c in cities]
    results = scan_cities(jd, tuples, orb_deg=orb_deg)
    return {
        "layer": "astronomy",
        "methodology": (
            "Placidus house system; Astro*Carto*Graphy (Lewis 1976); "
            "Swiss Ephemeris MOSEPH"
        ),
        "orb_deg": orb_deg,
        "city_count": len(results),
        "results": [_result_to_dict(r) for r in results],
    }


_ANGLE_THEME = {
    "Asc": "personality / how you come across",
    "MC": "career, status, public role",
    "IC": "home, roots, family, inner base",
    "Desc": "partnerships, allies, close relationships",
}


async def astrocartography_lines(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    birth_lat: float = 0.0,
    birth_lon: float = 0.0,
    birth_name: str = "birth",
) -> dict[str, Any]:
    """Compute the full astrocartography line set for an interactive map.

    Returns a GeoJSON FeatureCollection of every planet's MC/IC meridians
    and Asc/Desc horizon curves, plus a compact `chart` payload (sidereal
    time, obliquity, each body's ecliptic longitude + RA/Dec, birth point)
    that a thin client can use to compute the four angles for any clicked
    location without an ephemeris. Pure geometry — ASTRONOMY layer.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local clock.
        birth_timezone: IANA tz of birth (e.g. "Europe/Kyiv").
        birth_lat: Birth latitude (for the birth marker).
        birth_lon: Birth longitude.
        birth_name: Label for the birth place.
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    return {
        "layer": "astronomy",
        "methodology": (
            "Astro*Carto*Graphy (Lewis 1976); Swiss Ephemeris MOSEPH; "
            "MC/IC = meridian loci, Asc/Desc = horizon curves"
        ),
        "chart": chart_geometry(jd, birth_lat, birth_lon, birth_name),
        "lines": acg_lines(jd),
    }


async def astrocartography_point(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
    locale: str = "ru",
    orb_deg: float = 8.0,
) -> dict[str, Any]:
    """Relocate the chart to one clicked point and explain it in plain words.

    Returns the four relocated angles (Asc/MC/IC/Desc ecliptic longitudes),
    the natal planets sitting on those angles within `orb_deg`, and a
    rule-based work/life summary. Angle geometry is ASTRONOMY (conf 1.0);
    the summary is a symbol-tier reflection (conf 0.8) — never a prediction.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local clock.
        birth_timezone: IANA tz of birth.
        lat: Latitude of the location to inspect.
        lon: Longitude of the location to inspect.
        locale: "ru" or "en" for the summary text.
        orb_deg: Max orb for an angle contact (default 8°).
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    result = relocate(jd, lat, lon, orb_deg=orb_deg)
    return {
        "layer": "astronomy+symbolic",
        "methodology": "Placidus angles; classical angle orbs; reflective summary",
        "location": {"lat": lat, "lon": lon},
        "angles": {
            "asc": result.asc,
            "mc": result.mc,
            "ic": result.ic,
            "desc": result.desc,
        },
        "angle_themes": _ANGLE_THEME,
        "contacts": [_hit_to_dict(h) for h in result.angle_hits],
        "score": result.score,
        "summary": relocation_summary(result, locale=locale),
    }


async def solar_return_chart(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    return_year: int,
    location_lat: float,
    location_lon: float,
) -> dict[str, Any]:
    """Compute a Solar Return chart for `return_year` at a chosen location.

    Used for year-ahead analysis. Output is pure geometry — angles +
    planet houses at the moment the Sun returns to natal longitude,
    for the given physical location.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local.
        birth_timezone: IANA tz of birth.
        return_year: The year whose birthday-return chart you want.
        location_lat: Where the person is at the return moment.
        location_lon: Same.
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    sr = _solar_return(jd, return_year, location_lat, location_lon)
    return {
        "layer": "astronomy",
        "methodology": (
            "Swiss Ephemeris exact-return search (arc-minute precision); "
            "Placidus houses at chosen location"
        ),
        "return_year": return_year,
        "exact_moment_utc": sr.exact_moment_utc,
        "accuracy_arcmin": sr.accuracy_arcmin,
        "natal_sun_longitude": sr.natal_sun_longitude,
        "location": {"lat": sr.location_lat, "lon": sr.location_lon},
        "angles": {
            "asc": sr.asc,
            "mc": sr.mc,
            "ic": sr.ic,
            "desc": sr.desc,
        },
        "planets": sr.planets,
        "planet_houses": sr.planet_houses,
    }
