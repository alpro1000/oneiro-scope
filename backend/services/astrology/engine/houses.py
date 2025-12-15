"""House calculations with strict birth time handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ephemeris_engine import EphemerisEngine


@dataclass
class HouseCusp:
    number: int
    degree: float


class HouseCalculator:
    def __init__(self, engine: EphemerisEngine):
        self.engine = engine

    def calculate(self, jd_ut: Optional[float], lat: float, lon: float, house_system: str = "P") -> Optional[list[HouseCusp]]:
        if jd_ut is None:
            return None
        cusps, _ = self.engine.houses(jd_ut, lat, lon, house_system)
        return [HouseCusp(number=i + 1, degree=float(cusps[i])) for i in range(12)]
