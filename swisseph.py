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
    # Return predictable but deterministic values: lon increases with jd and body
    speed_factor = 0.1 + (body * 0.02)
    longitude = (jd * speed_factor + body * 3) % 360
    latitude = 0.0
    distance = 1.0
    speed = 1.0
    return (longitude, latitude, distance, speed), flags


def houses_ex(jd_ut: float, lat: float, lon: float, system: bytes):
    cusps = [(i * 30.0 + (jd_ut % 30)) % 360 for i in range(12)]
    ascmc = []
    return cusps, ascmc

