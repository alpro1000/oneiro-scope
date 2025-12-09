"""Lunar calendar API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_date(date_str: str) -> datetime:
    """Parse ISO date string and raise HTTP 400 on failure."""

    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )


def _build_mock_payload(
    target_date: date,
    locale: str,
    timezone: str,
    message: str
):
    """Return a frontend-friendly payload that also preserves legacy fields."""

    is_ru = locale == "ru"

    moon_phase = "full_moon"
    description = (
        "Максимально вероятные вещие сны, пик лунной энергии"
        if is_ru
        else "Highly prophetic dreams, peak of lunar energy"
    )
    recommendation = (
        "Записывайте все детали сразу после пробуждения"
        if is_ru
        else "Record all details immediately upon waking"
    )

    return {
        "date": target_date.isoformat(),
        "lunar_day": 15,  # Placeholder
        "moon_phase": moon_phase,
        "moon_phase_name": "Полнолуние" if is_ru else "Full Moon",
        "illumination": 0.98,
        "significance": {
            "name": "День силы" if is_ru else "Power Day",
            "type": "highly_positive",
            "dream_quality": "prophetic",
            "interpretation": description,
            "confidence": 0.95,
            "prophetic_probability": 0.92
        },
        "recommendations": [
            recommendation,
            "Обратите внимание на эмоции во сне" if is_ru else "Pay attention to emotions in the dream"
        ],
        "phase": "Полнолуние" if is_ru else "Full Moon",
        "phase_key": moon_phase,
        "description": description,
        "recommendation": recommendation,
        "locale": locale,
        "timezone": timezone,
        "status": "mock_data",
        "source": "mock",
        "message": message
    }


@router.get("/lunar/current")
async def get_current_lunar_day(
    timezone: str = Query("UTC", description="IANA timezone (e.g. Europe/Moscow)"),
    locale: str = Query("en", regex="^(en|ru)$", description="Language: en or ru")
):
    """
    Get current lunar day and significance

    Returns lunar day (1-30), moon phase, and dream interpretation guidelines
    based on lunar calendar.
    """

    # TODO: Implement lunar calculation service
    message = "This is placeholder data. Lunar service implementation pending."

    return _build_mock_payload(
        target_date=datetime.now(timezone=None).date(),
        locale=locale,
        timezone=timezone,
        message=message
    )


@router.get("/lunar/date/{date}")
async def get_lunar_day_for_date(
    date: str,
    timezone: str = Query("UTC", description="IANA timezone"),
    locale: str = Query("en", regex="^(en|ru)$", description="Language")
):
    """
    Get lunar day for specific date

    Args:
        date: Date in YYYY-MM-DD format
        timezone: IANA timezone
        locale: Language (en or ru)
    """

    parsed_date = _parse_date(date)

    # TODO: Implement lunar calculation for specific date
    return _build_mock_payload(
        target_date=parsed_date.date(),
        locale=locale,
        timezone=timezone,
        message="Lunar service implementation pending."
    )


@router.get("/lunar")
async def get_lunar_day(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    timezone: str = Query("UTC", description="IANA timezone (e.g. Europe/Moscow)"),
    locale: str = Query("en", regex="^(en|ru)$", description="Language")
):
    """
    Fetch lunar data using query params compatible with the Next.js frontend.

    If `date` is omitted, the current date is used.
    """

    parsed_date = datetime.now(timezone=None) if date is None else _parse_date(date)

    return _build_mock_payload(
        target_date=parsed_date.date(),
        locale=locale,
        timezone=timezone,
        message="Query-style endpoint for frontend integration (mock data)."
    )
