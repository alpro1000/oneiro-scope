"""Lunar calculations powered by Swiss Ephemeris."""

from __future__ import annotations

import glob
import hashlib
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

import pytz
import swisseph as swe

EPHE_PATTERNS = (
    "sepl*.se*",
    "sem*.se*",
    "seas*.se*",
    "semo*.se*",
)

SYNODIC_MONTH = 29.53058867
SUN = getattr(swe, "SUN", 0)
MOON = getattr(swe, "MOON", 1)
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
class EphemerisFile:
    path: str
    sha256: str


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


def _resolve_ephe_path(explicit: Optional[str] = None) -> Optional[str]:
    return (
        explicit
        or os.getenv("SWISSEPH_EPHE_PATH")
        or os.getenv("SWISSEPH_PATH")
        or os.getenv("SE_EPHE_PATH")
    )


def _hash_ephemeris_files(path: str) -> Iterable[EphemerisFile]:
    for pattern in EPHE_PATTERNS:
        for filename in glob.glob(os.path.join(path, pattern)):
            with open(filename, "rb") as handle:
                sha = hashlib.sha256(handle.read()).hexdigest()
            yield EphemerisFile(path=filename, sha256=sha)


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
    try:
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
    except Exception:
        return None


def _local_noon_utc(target_date: date, tz: str) -> datetime:
    tzinfo = pytz.timezone(tz)
    local_noon = tzinfo.localize(datetime(target_date.year, target_date.month, target_date.day, 12, 0))
    return local_noon.astimezone(pytz.UTC)


def _fallback_julday(year: int, month: int, day: int, ut: float) -> float:
    dt = datetime(year, month, day, tzinfo=pytz.UTC) + timedelta(hours=ut)
    return dt.timestamp() / 86400.0 + 2440587.5


def _fallback_longitude(days_since_j2000: float, base_longitude: float, mean_motion: float) -> float:
    return (base_longitude + mean_motion * days_since_j2000) % 360.0


def compute_lunar(date_iso: str, tz: str) -> LunarResult:
    target_date = date.fromisoformat(date_iso)
    noon_utc = _local_noon_utc(target_date, tz)
    ut = noon_utc.hour + noon_utc.minute / 60 + noon_utc.second / 3600 + noon_utc.microsecond / 3_600_000_000

    ephe_path = _resolve_ephe_path()
    engine_mode = "swisseph_moseph"
    ephemeris_files: list[EphemerisFile] = []
    flags = getattr(swe, "FLG_SPEED", 0)
    if ephe_path and os.path.isdir(ephe_path):
        swe.set_ephe_path(ephe_path)
        engine_mode = "swisseph_swieph"
        ephemeris_files = list(_hash_ephemeris_files(ephe_path))
        flags |= getattr(swe, "FLG_SWIEPH", 0)
        flags_text = "SWIEPH|SPEED"
    else:
        flags |= getattr(swe, "FLG_MOSEPH", getattr(swe, "FLG_SWIEPH", 0))
        flags_text = "MOSEPH|SPEED"
    try:
        jd_ut = swe.julday(noon_utc.year, noon_utc.month, noon_utc.day, ut)
    except TypeError:
        jd_ut = swe.julday(noon_utc.year, noon_utc.month, noon_utc.day)
    except Exception:
        jd_ut = _fallback_julday(noon_utc.year, noon_utc.month, noon_utc.day, ut)

    if jd_ut < 2_000_000:
        jd_ut = _fallback_julday(noon_utc.year, noon_utc.month, noon_utc.day, ut)

    calc_ut = getattr(swe, "calc_ut", None)
    if calc_ut:
        try:
            sun_lon, _, _, _ = calc_ut(jd_ut, SUN, flags)[0]
            moon_lon, _, _, _ = calc_ut(jd_ut, MOON, flags)[0]
        except Exception:
            calc_ut = None

    if not calc_ut:
        days_since_j2000 = jd_ut - 2451545.0
        sun_lon = _fallback_longitude(days_since_j2000, 280.46, 0.9856474)
        moon_lon = _fallback_longitude(days_since_j2000, 218.32, 13.1763965)

    phase_angle = (moon_lon - sun_lon) % 360.0
    illumination = (1 - math.cos(math.radians(phase_angle))) / 2
    moon_age_days = (phase_angle / 360.0) * SYNODIC_MONTH
    lunar_day = max(1, min(30, math.floor(moon_age_days) + 1))
    lunar_day_start_time = _calculate_lunar_day_start(moon_age_days, target_date, tz)
    phase = _phase_key(phase_angle)
    moon_sign = _moon_sign(moon_lon)

    provenance = {
        "ephemeris_engine": engine_mode,
        "ephemeris_files": [file.__dict__ for file in ephemeris_files],
        "flags": flags_text,
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

