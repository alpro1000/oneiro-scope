"""Astrology MCP tools.

Thin async wrappers over `backend.services.astrology.AstrologyService`.
Tool docstrings are the contract the LLM reads to decide invocation —
keep them precise.
"""

from __future__ import annotations

from datetime import date as date_cls, time as time_cls
from typing import Any, Optional
from uuid import UUID

from backend.services.astrology import (
    AstrologyService,
    EventForecastRequest,
    HoroscopeRequest,
    NatalChartRequest,
)
from backend.services.astrology.schemas import EventType, HoroscopePeriod


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
    locale: str = "ru",
) -> dict[str, Any]:
    """Calculate a natal (birth) chart from birth data.

    Returns planet positions, houses (Placidus, only when birth_time is given),
    aspects, and a structured LLM interpretation across 6 sections:
    personality, strengths, challenges, relationships, career, life_purpose.
    Without birth_time, 12:00 noon is used and ascendant/houses are omitted.

    Args:
        birth_date: YYYY-MM-DD.
        birth_place: City name, optionally with country ("Moscow", "Прага, Чехия").
            Geocoded via GeoNames API with a 90-city fallback.
        birth_time: HH:MM (24h). Optional — omit if unknown.
        locale: "ru" or "en". Default "ru".
    """
    req = NatalChartRequest(
        birth_date=date_cls.fromisoformat(birth_date),
        birth_time=time_cls.fromisoformat(birth_time) if birth_time else None,
        birth_place=birth_place,
        locale=locale,
    )
    resp = await _svc().calculate_natal_chart(req)
    return resp.model_dump(mode="json")


async def generate_horoscope(
    period: str = "daily",
    target_date: Optional[str] = None,
    locale: str = "ru",
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
    return resp.model_dump(mode="json")


async def forecast_event(
    event_type: str,
    event_date: str,
    event_location: Optional[str] = None,
    event_description: Optional[str] = None,
    locale: str = "ru",
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
    return resp.model_dump(mode="json")


def list_event_types() -> list[str]:
    """List supported event types for `forecast_event`."""
    return [e.value for e in EventType]


def list_horoscope_periods() -> list[str]:
    """List supported horoscope periods."""
    return [p.value for p in HoroscopePeriod]
