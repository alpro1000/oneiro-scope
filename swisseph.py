"""Lightweight stub of pyswisseph for offline testing.

This is not a replacement for the real Swiss Ephemeris and should only be
used in environments where the binary package cannot be installed. It
implements a tiny subset of the API used by the deterministic layer.
"""

from __future__ import annotations

import math
from datetime import datetime

SUN = 0
MOON = 1

FLG_SWIEPH = 2
FLG_SPEED = 256


def set_ephe_path(path: str) -> None:
    return None


def julday(year: int, month: int, day: int, ut: float) -> float:
    dt = datetime(year, month, day)  # naive
    base = datetime(1970, 1, 1)
    days = (dt - base).total_seconds() / 86400.0
    return 2440587.5 + days + ut / 24.0


def calc_ut(jd: float, body: int, flags: int):
    """Return a deterministic but more realistic mean longitude.

    The previous stub advanced the Sun and Moon by ~0.1° per day, which kept
    the lunar phase almost static across an entire month. That broke the
    "lunar day" calculation in offline mode (every date mapped to the same
    lunar day). Here we approximate the mean longitudes using simple linear
    speeds relative to J2000, which is sufficient for changing phase angles
    and lunar days in tests/dev.
    """

    days_since_j2000 = jd - 2451545.0

    if body == SUN:
        # Mean solar longitude ~0.9856° per day
        longitude = (280.460 + 0.9856474 * days_since_j2000) % 360
    elif body == MOON:
        # Mean lunar longitude ~13.1764° per day
        longitude = (218.316 + 13.176396 * days_since_j2000) % 360
    else:
        # Fallback: keep deterministic progression for any other body
        longitude = (jd * 0.1 + body * 3) % 360

    latitude = 0.0
    distance = 1.0
    speed = 1.0
    return (longitude, latitude, distance, speed), flags


def houses_ex(jd_ut: float, lat: float, lon: float, system: bytes):
    cusps = [(i * 30.0 + (jd_ut % 30)) % 360 for i in range(12)]
    ascmc = []
    return cusps, ascmc

