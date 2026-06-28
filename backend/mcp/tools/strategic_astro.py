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
