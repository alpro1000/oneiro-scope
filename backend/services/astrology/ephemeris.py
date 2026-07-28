"""Swiss Ephemeris wrapper for astronomical calculations (SWIEPH only)."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

import swisseph as swe

from backend.core import ephemeris as ephe_config

from .schemas import Planet, ZodiacSign

logger = logging.getLogger(__name__)

# Swiss Ephemeris planet constants
# SE_SUN = 0, SE_MOON = 1, SE_MERCURY = 2, etc.
PLANET_CODES = {
    Planet.SUN: 0,
    Planet.MOON: 1,
    Planet.MERCURY: 2,
    Planet.VENUS: 3,
    Planet.MARS: 4,
    Planet.JUPITER: 5,
    Planet.SATURN: 6,
    Planet.URANUS: 7,
    Planet.NEPTUNE: 8,
    Planet.PLUTO: 9,
    Planet.NORTH_NODE: 11,  # True node
    Planet.CHIRON: 15,
}

ZODIAC_SIGNS = [
    ZodiacSign.ARIES,
    ZodiacSign.TAURUS,
    ZodiacSign.GEMINI,
    ZodiacSign.CANCER,
    ZodiacSign.LEO,
    ZodiacSign.VIRGO,
    ZodiacSign.LIBRA,
    ZodiacSign.SCORPIO,
    ZodiacSign.SAGITTARIUS,
    ZodiacSign.CAPRICORN,
    ZodiacSign.AQUARIUS,
    ZodiacSign.PISCES,
]


@dataclass
class PlanetData:
    """Raw planet calculation data."""
    longitude: float  # 0-360 degrees
    latitude: float
    distance: float  # AU
    speed: float  # degrees per day (negative = retrograde)


@dataclass
class Location:
    """Geographic location with timezone."""
    latitude: float
    longitude: float
    timezone: str
    name: str


class SwissEphemeris:
    """
    Wrapper for Swiss Ephemeris calculations, SWIEPH mode only.

    The ephemeris path and flags come from backend.core.ephemeris, which
    verifies the .se1 files at import — by the time this class exists the
    engine is configured or the process is already dead. Calculation
    errors propagate: no Keplerian approximation, no Moshier retry
    (conventions.md §12).
    """

    def __init__(self):
        self._swe = swe
        self._flags = ephe_config.FLAGS
        self._engine_mode = "swieph"

    def calculate_planet_position(
        self,
        planet: Planet,
        dt: datetime,
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> PlanetData:
        """
        Calculate planet position at given datetime.

        Args:
            planet: Planet to calculate
            dt: Datetime (UTC)
            latitude: Observer latitude (for topocentric)
            longitude: Observer longitude (for topocentric)

        Returns:
            PlanetData with longitude, latitude, distance, speed
        """
        planet_code = PLANET_CODES.get(planet)
        if planet_code is None:
            raise ValueError(f"No Swiss Ephemeris body code for {planet}")

        jd = swe.julday(
            dt.year, dt.month, dt.day,
            dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
        )
        result, ret_flags = swe.calc_ut(jd, planet_code, self._flags)
        if not ret_flags & swe.FLG_SWIEPH:
            # The C library substitutes another source when a body's file
            # is unreadable — that substitution must never pass as SWIEPH.
            raise RuntimeError(
                f"Swiss Ephemeris did not use SWIEPH for {planet} "
                f"(returned flags {ret_flags}) — check backend/data/ephemeris"
            )

        return PlanetData(
            longitude=result[0],  # Ecliptic longitude
            latitude=result[1],   # Ecliptic latitude
            distance=result[2],   # Distance in AU
            speed=result[3],      # Speed in degrees/day
        )

    def get_zodiac_sign(self, longitude: float) -> tuple[ZodiacSign, float]:
        """
        Get zodiac sign and degree within sign from ecliptic longitude.

        Args:
            longitude: Ecliptic longitude (0-360)

        Returns:
            Tuple of (ZodiacSign, degree within sign 0-30)
        """
        sign_index = int(longitude / 30) % 12
        degree_in_sign = longitude % 30

        return ZODIAC_SIGNS[sign_index], degree_in_sign

    def is_retrograde(self, speed: float) -> bool:
        """Check if planet is retrograde based on speed."""
        return speed < 0

    def get_lunar_info(self, target_date: date) -> tuple[str, int]:
        """
        Get lunar phase and lunar day for a date.

        Args:
            target_date: Date to check

        Returns:
            Tuple of (phase_name, lunar_day 1-30)
        """
        dt = datetime.combine(target_date, datetime.min.time())

        sun_data = self.calculate_planet_position(Planet.SUN, dt)
        moon_data = self.calculate_planet_position(Planet.MOON, dt)

        # Calculate phase angle (Moon - Sun longitude)
        phase_angle = (moon_data.longitude - sun_data.longitude) % 360

        # Determine lunar day (1-30)
        lunar_day = int(phase_angle / 12.0) + 1
        lunar_day = max(1, min(30, lunar_day))

        # Determine phase name
        if phase_angle < 11.25:
            phase = "new_moon"
        elif phase_angle < 78.75:
            phase = "waxing_crescent"
        elif phase_angle < 101.25:
            phase = "first_quarter"
        elif phase_angle < 168.75:
            phase = "waxing_gibbous"
        elif phase_angle < 191.25:
            phase = "full_moon"
        elif phase_angle < 258.75:
            phase = "waning_gibbous"
        elif phase_angle < 281.25:
            phase = "last_quarter"
        else:
            phase = "waning_crescent"

        return phase, lunar_day

    def get_retrograde_planets(self, target_date: date) -> list[Planet]:
        """Get list of retrograde planets on a date."""
        dt = datetime.combine(target_date, datetime.min.time())
        retrograde = []

        for planet in [
            Planet.MERCURY,
            Planet.VENUS,
            Planet.MARS,
            Planet.JUPITER,
            Planet.SATURN,
            Planet.URANUS,
            Planet.NEPTUNE,
            Planet.PLUTO,
        ]:
            data = self.calculate_planet_position(planet, dt)
            if self.is_retrograde(data.speed):
                retrograde.append(planet)

        return retrograde
