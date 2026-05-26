"""Geo / city-search MCP tools.

Wraps `backend.services.astrology.geocoder.Geocoder` (GeoNames API +
90-city fallback). Used standalone by skills and as a validator before
calling `calculate_natal_chart`.
"""

from __future__ import annotations

from datetime import date as date_cls, time as time_cls
from typing import Any, Optional

from backend.services.astrology.geocoder import Geocoder, GeocodingError


_geocoder: Optional[Geocoder] = None


def _geo() -> Geocoder:
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder()
    return _geocoder


async def search_city(query: str) -> dict[str, Any]:
    """Geocode a city/place name → coordinates + timezone + provenance.

    Uses GeoNames API (30k req/day, username from env). Supports Russian
    queries via transliteration (Москва → Moscow). Falls back to a curated
    90-city database when the API is unavailable. Refuses to guess: raises
    if the place can't be resolved.

    Args:
        query: City name, optionally with country ("Moscow", "Прага, Чехия").
    """
    try:
        loc = await _geo().geocode(query)
    except GeocodingError as exc:
        return {"resolved": False, "error": str(exc), "query": query}
    return {
        "resolved": True,
        "name": loc.name,
        "country": loc.country,
        "admin_area": loc.admin_area,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "timezone": loc.timezone,
        "provider": loc.provider,
        "query": loc.query,
        "raw_response_id": loc.raw_response_id,
    }


async def validate_birth_data(
    birth_date: str,
    birth_place: str,
    birth_time: Optional[str] = None,
) -> dict[str, Any]:
    """Validate birth data before calling `calculate_natal_chart`.

    Checks: (a) birth_date parses and is between 1900-01-01 and today,
    (b) birth_time parses if provided, (c) birth_place geocodes to a real
    location. Returns a structured report so the caller can correct input
    before paying the LLM cost of full chart calculation.

    Args:
        birth_date: YYYY-MM-DD.
        birth_place: City name.
        birth_time: HH:MM. Optional.
    """
    issues: list[str] = []
    try:
        d = date_cls.fromisoformat(birth_date)
        if d < date_cls(1900, 1, 1) or d > date_cls.today():
            issues.append("birth_date out of supported range (1900 — today)")
    except ValueError:
        issues.append("birth_date is not a valid YYYY-MM-DD")

    if birth_time is not None:
        try:
            time_cls.fromisoformat(birth_time)
        except ValueError:
            issues.append("birth_time is not a valid HH:MM")

    geo = await search_city(birth_place)
    if not geo.get("resolved"):
        issues.append(f"birth_place could not be geocoded: {geo.get('error')}")

    return {
        "valid": not issues,
        "issues": issues,
        "geocoded": geo if geo.get("resolved") else None,
    }
