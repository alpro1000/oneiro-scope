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
    full_angle_breakdown,
    home_vs_work_focus,
    relocate,
    relocation_summary,
    scan_cities,
    score_explanation,
)
from backend.services.astrology.astrocartography import (
    compare_locations as _compare_locations,
    theme_scan as _theme_scan,
)
from backend.services.astrology.solar_return import (
    solar_return as _solar_return,
    suggest_locations as _sr_suggest,
)
from backend.services.astrology.synastry import (
    compute_synastry as _compute_synastry,
    synastry_summary as _synastry_summary,
)
from backend.mcp.tools._menu import (
    CITIES,
    PARTNER_BIRTH,
    TARGET_DATE,
    birth_inputs,
    with_menu,
)
from backend.services.astrology.transit_arcs import compute_arc as _compute_arc
from backend.services.astrology.transits_engine import find_transits


def _known(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    *extra: str,
) -> list[str]:
    """Plan input keys these tools' own arguments already imply.

    A caller able to name the birth timezone has resolved the birth place
    already — the plan cares that the location is pinned down, not how it got
    there — so `birth_timezone` counts as a known place.
    """
    return birth_inputs(birth_date, birth_time, birth_place=birth_timezone) + list(extra)


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
    return with_menu(
        {
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
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone),
        completed=["natal-chart", "transits"],
    )


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
    return with_menu(
        {
            "layer": "astronomy",
            "methodology": (
                "Placidus house system; Astro*Carto*Graphy (Lewis 1976); "
                "Swiss Ephemeris MOSEPH"
            ),
            "orb_deg": orb_deg,
            "city_count": len(results),
            "results": [_result_to_dict(r) for r in results],
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone, CITIES),
        completed=["natal-chart", "astrocartography"],
    )


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
    EVERY natal planet within `orb_deg` of any angle (not pre-filtered to
    one theme) with a cited archetype description each, a rule-based
    work/life summary, and an explanation of what actually drives the
    composite score (so a low score is never mistaken for "nothing here"
    when a real, tight, unweighted-planet contact exists). Angle geometry
    is ASTRONOMY (conf 1.0); descriptions are cited archetype (conf 0.9);
    the one-line summary is a symbol-tier reflection (conf 0.8) — never a
    prediction. Let the reader decide what matters to them (business,
    love, home) instead of the tool pre-filtering into a single lens.
    Also returns `axis_focus`: a place's significance split into a home
    axis (IC/Asc) and a work axis (MC/Desc) — some cities carry their
    entire signal on one axis only (e.g. all career/partnership, nothing
    home), which a single blended score would hide.

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
        "full_breakdown": full_angle_breakdown(result, orb_deg=orb_deg),
        "score": result.score,
        "score_explanation": score_explanation(result, locale=locale),
        "axis_focus": home_vs_work_focus(result, orb_deg=orb_deg, locale=locale),
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
    return with_menu(
        {
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
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone),
        completed=["natal-chart", "solar-return"],
    )


# --- Pattern features (session retrospective) --------------------------------


async def compare_relocations(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    locations: list[dict[str, Any]],
    locale: str = "ru",
) -> dict[str, Any]:
    """Side-by-side relocation read for 2–6 places — 'birth city vs
    current city vs candidate' in one call.

    Returns, per location: the four relocated angles, planets on angles
    (orb ≤8°), the heuristic score, and a plain-language work/life
    summary with a `clean` luck flag. Input order preserved.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local clock.
        birth_timezone: IANA tz of birth.
        locations: List of {"name":..., "lat":..., "lon":...}.
        locale: "ru" or "en" for summaries.
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    tuples = [(l["name"], float(l["lat"]), float(l["lon"])) for l in locations]
    return with_menu(
        {
            "layer": "astronomy+symbolic",
            "methodology": "Placidus relocation angles; classical angle orbs",
            "locations": _compare_locations(jd, tuples, locale=locale),
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone, CITIES),
        completed=["natal-chart", "compare-cities"], locale=locale,
    )


async def scan_cities_by_theme(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    theme: str,
    cities: list[dict[str, Any]],
    top_n: int = 10,
) -> dict[str, Any]:
    """Rank cities for ONE life theme: "luck" (Jupiter/Venus angular),
    "career" (Sun/Jupiter/Uranus/Mercury/Saturn on MC), "relationships"
    (benefics/luminaries on Desc), or "home" (Venus/Moon/Jupiter on
    IC/Asc).

    Each row carries a `clean` flag — benefic present with NO malefic
    (Mars/Saturn/Pluto) on any angle within orb — because a Venus line
    next to a tight Mars-IC reads completely differently.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local.
        birth_timezone: IANA tz of birth.
        theme: "luck" | "career" | "relationships" | "home".
        cities: List of {"name":..., "lat":..., "lon":...}.
        top_n: Max rows returned (default 10).
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    tuples = [(c["name"], float(c["lat"]), float(c["lon"])) for c in cities]
    return with_menu(
        {
            "layer": "astronomy+symbolic",
            "theme": theme,
            "results": _theme_scan(jd, tuples, theme, top_n=top_n),
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone, CITIES),
        completed=["natal-chart", "cities-by-theme"],
    )


async def transit_arc(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    birth_lat: float,
    birth_lon: float,
    theme: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    """Phase timeline of slow transits for one life theme — the
    "crisis → turning point → support" storyline instead of a flat list.

    Significators are derived from the natal chart (occupants + rulers
    of the theme's houses + natural planets), then Jupiter→Pluto
    transits to them are grouped into pressure/support phases. Output
    includes the first sustained turning point month, if any. Phases
    describe pressure vs support — they are NOT outcome verdicts.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local.
        birth_timezone: IANA tz of birth.
        birth_lat: Birth latitude (houses need it).
        birth_lon: Birth longitude.
        theme: "money_debt" | "career" | "relationships" | "home".
        start: Window start YYYY-MM-DD.
        end: Window end YYYY-MM-DD.
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    arc = _compute_arc(
        jd, birth_lat, birth_lon, theme,
        date_cls.fromisoformat(start), date_cls.fromisoformat(end),
    )
    return with_menu(
        {
            "layer": "astronomy+symbolic",
            "theme": arc.theme,
            "significators": arc.significators,
            "events": [
                {
                    "date": e.exact_date,
                    "transiting": e.transiting,
                    "aspect": e.aspect,
                    "natal": e.natal,
                    "orb": e.orb_at_midnight,
                }
                for e in arc.events
            ],
            "phases": [
                {
                    "start": p.start,
                    "end": p.end,
                    "kind": p.kind,
                    "event_count": len(p.events),
                }
                for p in arc.phases
            ],
            "turning_point": arc.turning_point,
            "note": "phases describe transit pressure/support, not outcomes",
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone, TARGET_DATE),
        completed=["natal-chart", "transit-arc"],
    )


async def synastry(
    person_a: dict[str, str],
    person_b: dict[str, str],
    locale: str = "ru",
) -> dict[str, Any]:
    """Compatibility (synastry) between two people: every inter-chart
    aspect plus dimension scores — attraction, emotional bond,
    communication, stability, tension — and a reflective summary.

    Geometry is astronomy (1.0); dimension scores are a classical
    rule-set (0.8). Never a verdict on a relationship.

    Args:
        person_a: {"birth_date": "YYYY-MM-DD", "birth_time": "HH:MM:SS",
            "birth_timezone": "Europe/Kyiv"}.
        person_b: Same structure.
        locale: "ru" or "en" for the summary.
    """
    jd_a = _natal_jd(
        person_a["birth_date"], person_a["birth_time"],
        person_a.get("birth_timezone", "UTC"),
    )
    jd_b = _natal_jd(
        person_b["birth_date"], person_b["birth_time"],
        person_b.get("birth_timezone", "UTC"),
    )
    result = _compute_synastry(jd_a, jd_b)
    return with_menu(
        {
            "layer": "astronomy+symbolic",
            "methodology": "inter-chart aspects; classical synastry weights",
            "aspect_count": len(result.aspects),
            "aspects": [
                {
                    "a": a.person_a_planet,
                    "b": a.person_b_planet,
                    "aspect": a.aspect,
                    "orb_deg": a.orb_deg,
                    "nature": a.nature,
                }
                for a in sorted(result.aspects, key=lambda x: x.orb_deg)
            ],
            "summary": _synastry_summary(result, locale=locale),
        },
        domain="astro",
        # Person A is the one the rest of the plan would be about.
        known_inputs=_known(
            person_a.get("birth_date"), person_a.get("birth_time"),
            person_a.get("birth_timezone"), PARTNER_BIRTH,
        ),
        completed=["natal-chart", "synastry"], locale=locale,
    )


async def solar_return_suggest(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    return_year: int,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rank candidate cities for spending a birthday (Solar Return
    relocation): benefics angular score (+), malefics angular (−).

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM:SS local.
        birth_timezone: IANA tz of birth.
        return_year: Birthday year to plan.
        candidates: List of {"name":..., "lat":..., "lon":...}.
    """
    jd = _natal_jd(birth_date, birth_time, birth_timezone)
    tuples = [(c["name"], float(c["lat"]), float(c["lon"])) for c in candidates]
    return with_menu(
        {
            "layer": "astronomy+symbolic",
            "return_year": return_year,
            "ranking": _sr_suggest(jd, return_year, tuples),
        },
        domain="astro",
        known_inputs=_known(birth_date, birth_time, birth_timezone, CITIES),
        completed=["natal-chart", "solar-return", "solar-return-where"],
    )
