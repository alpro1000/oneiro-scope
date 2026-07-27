"""Astrology MCP tools.

Thin async wrappers over `backend.services.astrology.AstrologyService`.
Tool docstrings are the contract the LLM reads to decide invocation —
keep them precise.
"""

from __future__ import annotations

from datetime import date as date_cls, time as time_cls
from typing import Any, Optional
from uuid import UUID

from backend.mcp.tools._menu import TARGET_DATE, birth_inputs, with_menu
from backend.services.astrology import (
    AstrologyService,
    EventForecastRequest,
    HoroscopeRequest,
    NatalChartRequest,
)
from backend.services.astrology.schemas import EventType, HoroscopePeriod
from backend.services.strategic.disclaimer import DISCLAIMERS, DISCLAIMER_RU


_service: Optional[AstrologyService] = None


def _svc() -> AstrologyService:
    global _service
    if _service is None:
        _service = AstrologyService()
    return _service


async def calculate_natal_chart(
    birth_date: str,
    birth_place: str,
    birth_time: Optional[str] = None,
    locale: str = "ru",  # ru | en | de | es | fr
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone_name: Optional[str] = None,
    include_interpretation: bool = False,
) -> dict[str, Any]:
    """Calculate a natal (birth) chart from birth data.

    Returns DETERMINISTIC data (astronomy, confidence 1.0): planet positions in
    sign and degree, retrograde flags, houses (Placidus, only when birth_time is
    given) with cusps, ascendant/midheaven, and aspects with orbs. Without
    birth_time, 12:00 noon is used and ascendant/houses are omitted.

    You (the calling model) are expected to READ this chart yourself — signs,
    dignities, houses and aspects are yours to interpret. Do so labelled: the
    positions are astronomy (1.0), classical rules you cite are 0.9, your
    synthesis is 0.7, and every reading carries the disclaimer. That is why
    interpretation is OFF by default here: a second, weaker, server-side LLM
    hop would be redundant and worse than your own reading.

    Set `include_interpretation=True` only for a client with no model of its own
    (e.g. a plain web page); it adds a server-generated prose interpretation and
    requires a server LLM provider key, degrading to a template without one.

    Args:
        birth_date: YYYY-MM-DD.
        birth_place: City name, optionally with country ("Moscow", "Прага, Чехия").
            Used as the geocoding query, or as a plain label when latitude and
            longitude are supplied.
        birth_time: HH:MM (24h). Optional — omit if unknown.
        locale: "ru" or "en". Default "ru".
        latitude: Birth latitude. Pass together with longitude to skip geocoding
            entirely — preferred when you already know the place (you read the
            user's script directly and can ask them which city they mean, which
            a name lookup cannot). Geocoding a name you already resolved only
            adds a chance of picking the wrong place.
        longitude: Birth longitude. Must accompany latitude.
        timezone_name: IANA zone ("Europe/Kyiv"). Optional. Leave it out and the
            zone is derived from the coordinates via tzdata — safer than naming
            it from memory, because an hour of timezone error moves the MC by
            ~15° while a degree of longitude moves it by ~1°. Historical offsets
            (Soviet decree time, wartime DST) always come from tzdata, never
            from the caller.
        include_interpretation: Add a server-side prose interpretation. Default
            False — interpret the returned data yourself.
    """
    req = NatalChartRequest(
        birth_date=date_cls.fromisoformat(birth_date),
        birth_time=time_cls.fromisoformat(birth_time) if birth_time else None,
        birth_place=birth_place,
        locale=locale,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
    )
    resp = await _svc().calculate_natal_chart(req, interpret=include_interpretation)
    out = resp.model_dump(mode="json")
    if not include_interpretation:
        # Drop the empty interpretation fields and tell the caller to read it.
        out.pop("interpretation", None)
        out.pop("structured_interpretation", None)
        out["how_to_read"] = (
            "Deterministic chart (astronomy 1.0). Interpret it yourself and "
            "label: positions 1.0, cited classical rule 0.9, your synthesis "
            "0.7. Cover personality, strengths, challenges, relationships, "
            "career, life purpose as fits the question."
        )
        out["disclaimer"] = DISCLAIMERS.get(locale, DISCLAIMER_RU)
    return with_menu(
        out,
        domain="astro",
        known_inputs=birth_inputs(
            birth_date, birth_time, birth_place,
            has_coordinates=latitude is not None and longitude is not None,
        ),
        completed=["natal-chart"],
        locale=locale,
    )


async def generate_horoscope(
    period: str = "daily",
    target_date: Optional[str] = None,
    locale: str = "ru",  # ru | en | de | es | fr
    natal_chart_id: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a horoscope for a period.

    Length is 600–1000 words for daily/weekly, longer for monthly/yearly.
    If `natal_chart_id` is given, output is personalized using a previously
    calculated natal chart (Sun, Moon, Ascendant context). Without it, output
    is general (current transits + lunar phase, no birth context).

    Args:
        period: "daily" | "weekly" | "monthly" | "yearly".
        target_date: Anchor date YYYY-MM-DD. Defaults to today.
        locale: "ru" or "en".
        natal_chart_id: Optional UUID of a previously calculated chart.
    """
    req = HoroscopeRequest(
        natal_chart_id=UUID(natal_chart_id) if natal_chart_id else None,
        period=HoroscopePeriod(period),
        target_date=date_cls.fromisoformat(target_date) if target_date else None,
        locale=locale,
    )
    resp = await _svc().generate_horoscope(req)
    return with_menu(
        resp.model_dump(mode="json"), domain="astro",
        known_inputs=[TARGET_DATE], completed=["horoscope"], locale=locale,
    )


async def forecast_event(
    event_type: str,
    event_date: str,
    event_location: Optional[str] = None,
    event_description: Optional[str] = None,
    locale: str = "ru",  # ru | en | de | es | fr
    natal_chart_id: Optional[str] = None,
) -> dict[str, Any]:
    """Forecast favorability of an event on a given date.

    Uses current transits, Moon phase, and retrograde planets. Returns a
    favorability score (0–100), narrative reasoning, positive/risk factors,
    and — if unfavorable — alternative dates within ±14 days.

    Args:
        event_type: One of: travel, wedding, business, interview, surgery,
            moving, contract, exam, date, other.
        event_date: YYYY-MM-DD.
        event_location: Optional city/place of the event.
        event_description: Optional free-text context (max 1000 chars).
        locale: "ru" or "en".
        natal_chart_id: Optional UUID for personalized forecast.
    """
    req = EventForecastRequest(
        natal_chart_id=UUID(natal_chart_id) if natal_chart_id else None,
        event_type=EventType(event_type),
        event_date=date_cls.fromisoformat(event_date),
        event_location=event_location,
        event_description=event_description,
        locale=locale,
    )
    resp = await _svc().forecast_event(req)
    return with_menu(
        resp.model_dump(mode="json"), domain="astro",
        known_inputs=[TARGET_DATE], completed=["event-forecast"], locale=locale,
    )


def list_event_types() -> list[str]:
    """List supported event types for `forecast_event`."""
    return [e.value for e in EventType]


def list_horoscope_periods() -> list[str]:
    """List supported horoscope periods."""
    return [p.value for p in HoroscopePeriod]


async def horoscope_report(
    period: str = "daily",
    target_date: Optional[str] = None,
    locale: str = "ru",
    natal_chart_id: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a horoscope AND write a self-contained HTML report file
    (print-to-PDF ready). Two-layer structure: full narrative first
    (summary + love/career/health), then compact takeaways, then the
    astronomical context (transits, retrogrades, Moon) with provenance.

    Args: same as generate_horoscope, plus:
        output_path: Where to write the .html; default — a unique file
            in the system temp directory.
    """
    from backend.mcp.tools._files import write_report
    from backend.services.astrology.horoscope_report import render_horoscope_html
    from backend.services.astrology.schemas import HoroscopeRequest

    req = HoroscopeRequest(
        natal_chart_id=UUID(natal_chart_id) if natal_chart_id else None,
        period=HoroscopePeriod(period),
        target_date=date_cls.fromisoformat(target_date) if target_date else None,
        locale=locale,
    )
    resp = await _svc().generate_horoscope(req)
    html = render_horoscope_html(resp, locale=locale)
    path = write_report(html, output_path, prefix=f"horoscope_{period}")
    return with_menu(
        {
            "report_path": str(path),
            "period": period,
            "period_start": str(resp.period_start),
            "period_end": str(resp.period_end),
            "summary_preview": resp.summary[:200],
            "recommendations_count": len(resp.recommendations),
        },
        domain="astro",
        known_inputs=[TARGET_DATE], completed=["horoscope-report"], locale=locale,
    )


async def profile_report_file(
    birth_date: str,
    birth_time: Optional[str] = None,
    birth_lat: float = 0.0,
    birth_lon: float = 0.0,
    birth_place: Optional[str] = None,
    current_place_name: Optional[str] = None,
    current_lat: Optional[float] = None,
    current_lon: Optional[float] = None,
    locale: str = "ru",
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Build the full astrology profile report (natal snapshot + birth/
    current city relocation reads + thematic city shortlist + a year of
    slow transits) AND write it as a self-contained HTML file.

    Args:
        birth_date: YYYY-MM-DD.
        birth_time: HH:MM local time; noon fallback drops houses/angles.
        birth_lat / birth_lon: Birth coordinates (drive historical tz).
        birth_place: Display name of the birth place.
        current_place_name / current_lat / current_lon: Optional city of
            residence for the side-by-side relocation read.
        locale: "ru" or "en".
        output_path: Where to write the .html; default — temp dir.
    """
    from backend.mcp.tools._files import write_report
    from backend.services.astrology.historic_tz import resolve_birth_moment
    from backend.services.astrology.report import build_report, render_html

    moment = resolve_birth_moment(
        date_cls.fromisoformat(birth_date),
        time_cls.fromisoformat(birth_time) if birth_time else None,
        lat=birth_lat, lon=birth_lon,
    )
    current = (
        (current_place_name or "current", current_lat, current_lon)
        if current_lat is not None and current_lon is not None else None
    )
    report = build_report(
        moment,
        birth_place=(birth_place or "birth", birth_lat, birth_lon),
        current_place=current,
        locale=locale,
    )
    html = render_html(report, locale=locale)
    path = write_report(html, output_path, prefix="astro_profile")
    return with_menu(
        {
            "report_path": str(path),
            "timezone": report["birth"]["timezone"],
            "utc_offset_hours": report["birth"]["utc_offset_hours"],
            "themes": {k: len(v) for k, v in report["themes"].items()},
            "year_transits_count": len(report["year_transits"]),
        },
        domain="astro",
        known_inputs=birth_inputs(
            birth_date, birth_time, birth_place, has_coordinates=True,
        ),
        completed=["profile-report"], locale=locale,
    )
