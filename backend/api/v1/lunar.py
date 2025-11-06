"""Lunar calendar API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
    # This is a placeholder response

    return {
        "date": datetime.now().date().isoformat(),
        "lunar_day": 15,  # Placeholder
        "moon_phase": "full_moon",
        "moon_phase_name": "Полнолуние" if locale == "ru" else "Full Moon",
        "illumination": 0.98,
        "significance": {
            "name": "День силы" if locale == "ru" else "Power Day",
            "type": "highly_positive",
            "dream_quality": "prophetic",
            "interpretation": (
                "Максимально вероятные вещие сны, пик лунной энергии"
                if locale == "ru"
                else "Highly prophetic dreams, peak of lunar energy"
            ),
            "confidence": 0.95,
            "prophetic_probability": 0.92
        },
        "recommendations": [
            "Записывайте все детали сразу после пробуждения" if locale == "ru"
            else "Record all details immediately upon waking",
            "Обратите внимание на эмоции во сне" if locale == "ru"
            else "Pay attention to emotions in the dream"
        ],
        "status": "mock_data",
        "message": "This is placeholder data. Lunar service implementation pending."
    }


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

    # Validate date format
    try:
        parsed_date = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # TODO: Implement lunar calculation for specific date

    return {
        "date": date,
        "lunar_day": 10,  # Placeholder
        "moon_phase": "waxing_gibbous",
        "status": "mock_data",
        "message": "Lunar service implementation pending."
    }
