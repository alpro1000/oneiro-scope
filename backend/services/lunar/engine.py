"""Lunar calculations powered by Swiss Ephemeris (SWIEPH only).

Ephemeris configuration — path, flags, file hashes — is owned by
backend.core.ephemeris, which verifies the repo-shipped .se1 files at
import. There is no Moshier branch and no analytic fallback here
(conventions.md §12): a broken ephemeris setup fails the process at
startup instead of silently degrading the numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import pytz
import swisseph as swe

from backend.core import ephemeris as ephe_config

SYNODIC_MONTH = 29.53058867
SUN = swe.SUN
MOON = swe.MOON
SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


@dataclass
class LunarResult:
    date: str
    timezone: str
    jd_ut: float
    sun_longitude: float
    moon_longitude: float
    phase_angle: float
    illumination: float
    moon_age_days: float
    lunar_day: int
    lunar_day_start_time: Optional[str]  # Time when current lunar day started (HH:MM format)
    moon_sign: str
    phase_key: str
    provenance: dict


def _phase_key(angle: float) -> str:
    if angle < 22.5 or angle >= 337.5:
        return "new_moon"
    if angle < 67.5:
        return "waxing_crescent"
    if angle < 112.5:
        return "first_quarter"
    if angle < 157.5:
        return "waxing_gibbous"
    if angle < 202.5:
        return "full_moon"
    if angle < 247.5:
        return "waning_gibbous"
    if angle < 292.5:
        return "last_quarter"
    return "waning_crescent"


def _moon_sign(longitude: float) -> str:
    index = int(longitude // 30) % 12
    return SIGNS[index]


def _calculate_lunar_day_start(moon_age_days: float, target_date: date, tz: str) -> Optional[str]:
    """
    Calculate approximate time when current lunar day started.

    Lunar day changes approximately every 24.8 hours.
    We calculate backwards from moon age to find when this day began.
    """
    # Никакого try/except: единственный реальный сбой здесь — неизвестная
    # таймзона, и это ошибка входа, которая обязана падать громко
    # (conventions.md §12), а не превращаться в null, неотличимый от
    # «время начала неизвестно».
    # Get fractional part of lunar day (e.g., 5.3 days -> 0.3)
    current_lunar_day = max(1, min(30, math.floor(moon_age_days) + 1))
    fraction_into_day = moon_age_days - (current_lunar_day - 1)

    # Average lunar day is ~24.8 hours
    # Calculate how many hours ago this day started
    hours_into_day = fraction_into_day * 24.8

    # Calculate start time by going back from midnight
    tzinfo = pytz.timezone(tz)
    midnight_local = tzinfo.localize(
        datetime(target_date.year, target_date.month, target_date.day, 0, 0)
    )

    # Lunar day start time
    day_start = midnight_local + timedelta(hours=hours_into_day)

    # If calculated time is in the future (>24h ahead), go back one day
    now_local = datetime.now(tzinfo)
    if day_start > now_local + timedelta(hours=12):
        day_start -= timedelta(days=1)

    # Format as HH:MM
    return day_start.strftime("%H:%M")


def _local_noon_utc(target_date: date, tz: str) -> datetime:
    tzinfo = pytz.timezone(tz)
    local_noon = tzinfo.localize(datetime(target_date.year, target_date.month, target_date.day, 12, 0))
    return local_noon.astimezone(pytz.UTC)


def compute_lunar(date_iso: str, tz: str) -> LunarResult:
    target_date = date.fromisoformat(date_iso)
    ephe_config.require_in_range(target_date, "lunar calculation")
    noon_utc = _local_noon_utc(target_date, tz)
    ut = noon_utc.hour + noon_utc.minute / 60 + noon_utc.second / 3600 + noon_utc.microsecond / 3_600_000_000

    jd_ut = swe.julday(noon_utc.year, noon_utc.month, noon_utc.day, ut)
    # Same fail-closed rule as the astrology wrapper: the returned flags
    # are the only witness that SWIEPH actually served the result.
    sun_lon = ephe_config.calc_ut_swieph(jd_ut, SUN)[0]
    moon_lon = ephe_config.calc_ut_swieph(jd_ut, MOON)[0]

    phase_angle = (moon_lon - sun_lon) % 360.0
    # WP-16: illuminated fraction from swe_pheno_ut, not the flat
    # (1-cos)/2 approximation — the latter ignores the Moon's actual
    # phase geometry and was off by up to ~4 pp (74.08% vs 77.85% on
    # 2026-08-03 10:00 UTC).
    illumination = swe.pheno_ut(jd_ut, MOON, ephe_config.FLAGS)[1]
    moon_age_days = (phase_angle / 360.0) * SYNODIC_MONTH
    lunar_day = max(1, min(30, math.floor(moon_age_days) + 1))
    lunar_day_start_time = _calculate_lunar_day_start(moon_age_days, target_date, tz)
    phase = _phase_key(phase_angle)
    moon_sign = _moon_sign(moon_lon)

    provenance = {
        "ephemeris_engine": ephe_config.ENGINE_MODE,
        "swisseph_version": ephe_config.SWE_VERSION,
        "ephemeris_files": [dict(item) for item in ephe_config.ephemeris_files()],
        "flags": ephe_config.FLAGS_TEXT,
        "illumination_method": "swe_pheno_ut",
        "jd_ut": jd_ut,
        "timezone": tz,
        "local_noon_utc": noon_utc.isoformat(),
    }

    return LunarResult(
        date=target_date.isoformat(),
        timezone=tz,
        jd_ut=jd_ut,
        sun_longitude=sun_lon,
        moon_longitude=moon_lon,
        phase_angle=phase_angle,
        illumination=illumination,
        moon_age_days=moon_age_days,
        lunar_day=lunar_day,
        lunar_day_start_time=lunar_day_start_time,
        moon_sign=moon_sign,
        phase_key=phase,
        provenance=provenance,
    )


class LunarEngine:
    """
    High-level API for lunar calculations.

    Used by astrology service for getting lunar day info.
    """

    def get_lunar_day(self, target_date: date, timezone: str) -> dict:
        """
        Get lunar day information for a specific date.

        Args:
            target_date: Date to calculate for
            timezone: Timezone string (e.g., "Europe/Moscow")

        Returns:
            Dict with keys: lunar_day, phase, moon_sign, illumination, provenance
        """
        result = compute_lunar(target_date.isoformat(), timezone)

        return {
            "lunar_day": result.lunar_day,
            "phase": result.phase_key,
            "moon_sign": result.moon_sign,
            "illumination": result.illumination,
            "moon_age_days": result.moon_age_days,
            "lunar_day_start_time": result.lunar_day_start_time,
            "provenance": result.provenance,
        }

    def get_lunar_info_for_period(
        self, start_date: date, end_date: date, timezone: str
    ) -> list[dict]:
        """
        Get lunar info for a date range.

        Args:
            start_date: Start of period
            end_date: End of period
            timezone: Timezone string

        Returns:
            List of dicts with lunar info for each day
        """
        results = []
        current = start_date

        while current <= end_date:
            daily_info = self.get_lunar_day(current, timezone)
            daily_info["date"] = current.isoformat()
            results.append(daily_info)
            current += timedelta(days=1)

        return results
