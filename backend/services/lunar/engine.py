"""Lunar calculations powered by Swiss Ephemeris."""

from __future__ import annotations

import glob
import hashlib
import math
import os
from dataclasses import dataclass
from datetime import date, datetime
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


def _local_noon_utc(target_date: date, tz: str) -> datetime:
    tzinfo = pytz.timezone(tz)
    local_noon = tzinfo.localize(datetime(target_date.year, target_date.month, target_date.day, 12, 0))
    return local_noon.astimezone(pytz.UTC)


def compute_lunar(date_iso: str, tz: str) -> LunarResult:
    target_date = date.fromisoformat(date_iso)
    noon_utc = _local_noon_utc(target_date, tz)
    ut = noon_utc.hour + noon_utc.minute / 60 + noon_utc.second / 3600 + noon_utc.microsecond / 3_600_000_000

    ephe_path = _resolve_ephe_path()
    engine_mode = "swisseph_moseph"
    ephemeris_files: list[EphemerisFile] = []
    if ephe_path and os.path.isdir(ephe_path):
        swe.set_ephe_path(ephe_path)
        engine_mode = "swisseph_swieph"
        ephemeris_files = list(_hash_ephemeris_files(ephe_path))

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    jd_ut = swe.julday(noon_utc.year, noon_utc.month, noon_utc.day, ut)
    sun_lon, _, _, _ = swe.calc_ut(jd_ut, SUN, flags)[0]
    moon_lon, _, _, _ = swe.calc_ut(jd_ut, MOON, flags)[0]

    phase_angle = (moon_lon - sun_lon) % 360.0
    illumination = (1 - math.cos(math.radians(phase_angle))) / 2
    moon_age_days = (phase_angle / 360.0) * SYNODIC_MONTH
    lunar_day = max(1, min(30, math.floor(moon_age_days) + 1))
    phase = _phase_key(phase_angle)
    moon_sign = _moon_sign(moon_lon)

    provenance = {
        "ephemeris_engine": engine_mode,
        "ephemeris_files": [file.__dict__ for file in ephemeris_files],
        "flags": "SWIEPH|SPEED",
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
        moon_sign=moon_sign,
        phase_key=phase,
        provenance=provenance,
    )

