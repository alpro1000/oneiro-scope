"""Lunar calendar API endpoints backed by Swiss Ephemeris."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

import pytz
from fastapi import APIRouter, HTTPException, Query

from backend.services.lunar.content import get_lunar_day_text
from backend.services.lunar.engine import compute_lunar

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from exc


def _resolve_date(date_str: Optional[str], tz: str) -> date:
    if date_str:
        return _parse_date(date_str)
    tzinfo = pytz.timezone(tz)
    return datetime.now(tzinfo).date()


@router.get("/timezones")
async def get_timezones():
    """Get list of popular timezones for lunar calendar."""
    timezones = [
        {"value": "Europe/Moscow", "label": "Москва (UTC+3)", "region": "Европа", "utc_offset": "+03:00"},
        {"value": "Europe/Kiev", "label": "Киев (UTC+2)", "region": "Европа", "utc_offset": "+02:00"},
        {"value": "Asia/Almaty", "label": "Алматы (UTC+6)", "region": "Азия", "utc_offset": "+06:00"},
        {"value": "Europe/Minsk", "label": "Минск (UTC+3)", "region": "Европа", "utc_offset": "+03:00"},
        {"value": "Asia/Yekaterinburg", "label": "Екатеринбург (UTC+5)", "region": "Азия", "utc_offset": "+05:00"},
        {"value": "Asia/Novosibirsk", "label": "Новосибирск (UTC+7)", "region": "Азия", "utc_offset": "+07:00"},
        {"value": "Asia/Vladivostok", "label": "Владивосток (UTC+10)", "region": "Азия", "utc_offset": "+10:00"},
        {"value": "Europe/Prague", "label": "Прага (UTC+1)", "region": "Европа", "utc_offset": "+01:00"},
        {"value": "Europe/Berlin", "label": "Берлин (UTC+1)", "region": "Европа", "utc_offset": "+01:00"},
        {"value": "Europe/Paris", "label": "Париж (UTC+1)", "region": "Европа", "utc_offset": "+01:00"},
        {"value": "Europe/London", "label": "Лондон (UTC+0)", "region": "Европа", "utc_offset": "+00:00"},
        {"value": "America/New_York", "label": "Нью-Йорк (UTC-5)", "region": "Америка", "utc_offset": "-05:00"},
        {"value": "America/Los_Angeles", "label": "Лос-Анджелес (UTC-8)", "region": "Америка", "utc_offset": "-08:00"},
        {"value": "America/Chicago", "label": "Чикаго (UTC-6)", "region": "Америка", "utc_offset": "-06:00"},
        {"value": "Asia/Tokyo", "label": "Токио (UTC+9)", "region": "Азия", "utc_offset": "+09:00"},
        {"value": "Asia/Shanghai", "label": "Шанхай (UTC+8)", "region": "Азия", "utc_offset": "+08:00"},
        {"value": "Asia/Dubai", "label": "Дубай (UTC+4)", "region": "Азия", "utc_offset": "+04:00"},
        {"value": "Australia/Sydney", "label": "Сидней (UTC+11)", "region": "Австралия", "utc_offset": "+11:00"},
        {"value": "UTC", "label": "UTC (универсальное время)", "region": "Общее", "utc_offset": "+00:00"},
    ]
    return {"timezones": timezones}


@router.get("/lunar")
async def get_lunar_day(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    tz: str = Query("Europe/Moscow", description="IANA timezone (e.g. Europe/Moscow)"),
    locale: str = Query("en", description="Language code")
):
    target_date = _resolve_date(date, tz)

    try:
        lunar = compute_lunar(target_date.isoformat(), tz)
        content = get_lunar_day_text(lunar.lunar_day, locale)
    except pytz.UnknownTimeZoneError as exc:
        raise HTTPException(status_code=400, detail="Invalid timezone") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected lunar calculation failure")
        raise HTTPException(status_code=500, detail="Failed to compute lunar data") from exc

    phase_label = lunar.phase_key.replace("_", " ").title()

    return {
        "date": lunar.date,
        "phase": phase_label,
        "phase_key": lunar.phase_key,
        "phase_angle": lunar.phase_angle,
        "illumination": lunar.illumination,
        "age": lunar.moon_age_days,
        "lunar_day": lunar.lunar_day,
        "moon_sign": lunar.moon_sign,
        "description": content.get("notes", ""),
        "recommendation": content.get("type", ""),
        "locale": locale,
        "timezone": tz,
        "provenance": lunar.provenance,
        "source": "backend",
    }

