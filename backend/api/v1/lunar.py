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


@router.get("/lunar")
async def get_lunar_day(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    tz: str = Query("UTC", description="IANA timezone (e.g. Europe/Moscow)"),
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

