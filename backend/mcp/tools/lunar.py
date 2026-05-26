"""Lunar calendar MCP tools.

Pure synchronous wrappers over `backend.services.lunar.engine` and
`backend.services.lunar.content`. No LLM calls — fully deterministic
(Swiss Ephemeris or Moshier fallback).
"""

from __future__ import annotations

import os
from datetime import date as date_cls
from typing import Any

from backend.services.lunar.content import get_lunar_day_text
from backend.services.lunar.engine import LunarEngine


_engine = LunarEngine()

_DEFAULT_TZ = os.getenv("LUNAR_DEFAULT_TZ", "Europe/Moscow")


def get_lunar_day(
    target_date: str,
    timezone: str = "",
    locale: str = "ru",
) -> dict[str, Any]:
    """Return lunar-day information for a date.

    Combines astronomical computation (lunar day number, Moon phase, Moon sign,
    illumination %, Julian Day UT) with the bilingual narrative text from
    `lunar_tables.json` (themes, recommendations, do-not list). The astronomy
    is deterministic — uses Swiss Ephemeris when binary files are available,
    Moshier (analytic) otherwise. Provenance is included.

    Args:
        target_date: YYYY-MM-DD.
        timezone: IANA timezone (e.g., "Europe/Moscow"). Defaults to
            `LUNAR_DEFAULT_TZ` env var or "Europe/Moscow".
        locale: "ru" or "en" — language of narrative content.
    """
    tz = timezone or _DEFAULT_TZ
    d = date_cls.fromisoformat(target_date)
    info = _engine.get_lunar_day(d, tz)
    info["date"] = d.isoformat()
    info["content"] = get_lunar_day_text(info["lunar_day"], locale)
    return info


def get_lunar_period(
    start_date: str,
    end_date: str,
    timezone: str = "",
    locale: str = "ru",
    include_content: bool = False,
) -> list[dict[str, Any]]:
    """Return lunar-day info for each day in a range (inclusive).

    Args:
        start_date: YYYY-MM-DD.
        end_date: YYYY-MM-DD. Must be ≤ 60 days after start.
        timezone: IANA timezone. Defaults to env / "Europe/Moscow".
        locale: "ru" or "en".
        include_content: If true, attach narrative text per day (heavier
            response). Default false — just astronomy.
    """
    tz = timezone or _DEFAULT_TZ
    start = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date)
    if (end - start).days > 60:
        raise ValueError("Period exceeds 60 days; split the request.")
    rows = _engine.get_lunar_info_for_period(start, end, tz)
    if include_content:
        for row in rows:
            row["content"] = get_lunar_day_text(row["lunar_day"], locale)
    return rows
