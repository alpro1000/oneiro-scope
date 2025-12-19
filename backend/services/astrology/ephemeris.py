"""Swiss Ephemeris wrapper for astronomical calculations."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from .schemas import Planet, ZodiacSign

logger = logging.getLogger(__name__)

# Swiss Ephemeris planet constants (when library is available)
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
    Wrapper for Swiss Ephemeris calculations.

    Swiss Ephemeris provides high-precision astronomical calculations.
    Accuracy: < 1 arc second for modern dates.

    Note: Requires pyswisseph package and ephemeris data files.
    Falls back to simplified calculations if unavailable.
    """

    def __init__(self, ephemeris_path: Optional[str] = None):
        """
        Initialize Swiss Ephemeris.

        Args:
            ephemeris_path: Path to ephemeris data files.
                           If None, uses default path or falls back to Moshier.
        """
        self._swe = None
        self._initialized = False
        self._ephemeris_path = ephemeris_path
        self._flags = None
        self._engine_mode = "moseph"

        try:
            import swisseph as swe
            self._swe = swe
            if ephemeris_path:
                swe.set_ephe_path(ephemeris_path)
                self._engine_mode = "swieph"
                speed_flags = getattr(swe, "FLG_SWIEPH", 0)
            else:
                speed_flags = getattr(swe, "FLG_MOSEPH", getattr(swe, "FLG_SWIEPH", 0))
            self._flags = speed_flags | getattr(swe, "FLG_SPEED", 0)
            self._initialized = True
            logger.info("Swiss Ephemeris initialized successfully")
        except ImportError:
            logger.warning(
                "pyswisseph not installed. Using fallback calculations. "
                "Install with: pip install pyswisseph"
            )

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
        if self._swe and planet in PLANET_CODES:
            return self._calculate_with_swe(planet, dt)
        else:
            return self._calculate_fallback(planet, dt)

    def _calculate_with_swe(self, planet: Planet, dt: datetime) -> PlanetData:
        """Calculate using Swiss Ephemeris."""
        # Convert to Julian Day
        try:
            jd = self._swe.julday(
                dt.year, dt.month, dt.day,
                dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            )
        except TypeError:
            jd = self._swe.julday(dt.year, dt.month, dt.day)
        except Exception:
            jd = self._swe.julday(dt.year, dt.month, dt.day)

        if jd < 2_000_000:
            # Fall back to simplified Julian date if the stub returns an ordinal
            jd = (dt.replace(tzinfo=datetime.timezone.utc).timestamp() / 86400.0) + 2440587.5

        # Get planet position
        planet_code = PLANET_CODES.get(planet)
        if planet_code is None:
            return self._calculate_fallback(planet, dt)

        # SEFLG_SPEED includes speed in result
        flags = self._flags or (
            getattr(self._swe, "FLG_SWIEPH", 0) | getattr(self._swe, "FLG_SPEED", 0)
        )

        try:
            calc_ut = getattr(self._swe, "calc_ut", None)
            if calc_ut is None:
                raise AttributeError("calc_ut not available")
            result, ret_flags = calc_ut(jd, planet_code, flags)
        except Exception:
            fallback_flags = (
                getattr(self._swe, "FLG_MOSEPH", getattr(self._swe, "FLG_SWIEPH", 0))
                | getattr(self._swe, "FLG_SPEED", 0)
            )
            fallback_calc = getattr(self._swe, "calc_ut", None)
            if fallback_calc is None:
                return self._calculate_fallback(planet, dt)
            result, ret_flags = fallback_calc(jd, planet_code, fallback_flags)

        return PlanetData(
            longitude=result[0],  # Ecliptic longitude
            latitude=result[1],   # Ecliptic latitude
            distance=result[2],   # Distance in AU
            speed=result[3],      # Speed in degrees/day
        )

    def _calculate_fallback(self, planet: Planet, dt: datetime) -> PlanetData:
        """
        Fallback calculation when Swiss Ephemeris is unavailable.
        Uses simplified Keplerian elements.
        """
        # Simplified mean longitude calculation
        # This is approximate and should only be used as fallback
        import math

        # Days since J2000.0 (2000-01-01 12:00 UTC)
        j2000 = datetime(2000, 1, 1, 12, 0, 0)
        days = (dt - j2000).total_seconds() / 86400.0

        # Approximate mean longitudes (very simplified)
        mean_motions = {
            Planet.SUN: 0.9856474,     # degrees per day
            Planet.MOON: 13.1763965,
            Planet.MERCURY: 4.0923344,
            Planet.VENUS: 1.6021302,
            Planet.MARS: 0.5240208,
            Planet.JUPITER: 0.0830853,
            Planet.SATURN: 0.0334979,
            Planet.URANUS: 0.0117725,
            Planet.NEPTUNE: 0.0060195,
            Planet.PLUTO: 0.0039795,
        }

        base_longitudes = {
            Planet.SUN: 280.46,
            Planet.MOON: 218.32,
            Planet.MERCURY: 252.25,
            Planet.VENUS: 181.98,
            Planet.MARS: 355.45,
            Planet.JUPITER: 34.40,
            Planet.SATURN: 50.08,
            Planet.URANUS: 314.06,
            Planet.NEPTUNE: 304.35,
            Planet.PLUTO: 238.96,
        }

        motion = mean_motions.get(planet, 0.01)
        base_lon = base_longitudes.get(planet, 0.0)

        longitude = (base_lon + motion * days) % 360

        return PlanetData(
            longitude=longitude,
            latitude=0.0,  # Simplified - assume ecliptic
            distance=1.0,  # Placeholder
            speed=motion,  # Mean motion as speed approximation
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
