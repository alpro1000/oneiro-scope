"""Natal chart calculation module."""

import logging
from datetime import datetime
from typing import Optional

from .ephemeris import SwissEphemeris
from .schemas import (
    Aspect,
    AspectType,
    House,
    Planet,
    PlanetPosition,
    ZodiacSign,
)

logger = logging.getLogger(__name__)

# Aspect orbs (maximum allowed deviation in degrees)
ASPECT_ORBS = {
    AspectType.CONJUNCTION: 10,
    AspectType.OPPOSITION: 10,
    AspectType.TRINE: 8,
    AspectType.SQUARE: 8,
    AspectType.SEXTILE: 6,
    AspectType.QUINCUNX: 3,
}

# Aspect exact angles
ASPECT_ANGLES = {
    AspectType.CONJUNCTION: 0,
    AspectType.SEXTILE: 60,
    AspectType.SQUARE: 90,
    AspectType.TRINE: 120,
    AspectType.QUINCUNX: 150,
    AspectType.OPPOSITION: 180,
}


class NatalChartCalculator:
    """
    Calculator for natal chart elements.

    Calculates:
    - Planet positions in signs and houses
    - House cusps (Placidus system by default)
    - Aspects between planets
    """

    def __init__(self, ephemeris: SwissEphemeris):
        self.ephemeris = ephemeris

    def calculate_planets(
        self,
        birth_dt: datetime,
        latitude: float,
        longitude: float,
        timezone: str,
    ) -> list[PlanetPosition]:
        """
        Calculate positions of all planets at birth time.

        Args:
            birth_dt: Birth datetime (local time)
            latitude: Birth place latitude
            longitude: Birth place longitude
            timezone: Birth place timezone

        Returns:
            List of PlanetPosition for all planets
        """
        # Convert to UTC for calculations
        import pytz
        try:
            local_tz = pytz.timezone(timezone)
            if birth_dt.tzinfo is None:
                birth_dt = local_tz.localize(birth_dt)
            utc_dt = birth_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception:
            # Fallback to treating as UTC
            utc_dt = birth_dt

        planets = []

        for planet in Planet:
            if planet == Planet.SOUTH_NODE:
                # South Node is opposite North Node
                continue

            data = self.ephemeris.calculate_planet_position(
                planet, utc_dt, latitude, longitude
            )

            sign, sign_degree = self.ephemeris.get_zodiac_sign(data.longitude)

            planets.append(
                PlanetPosition(
                    planet=planet,
                    sign=sign,
                    degree=data.longitude,
                    sign_degree=sign_degree,
                    retrograde=self.ephemeris.is_retrograde(data.speed),
                    house=None,  # Will be filled after house calculation
                )
            )

        # Add South Node (opposite of North Node)
        north_node = next((p for p in planets if p.planet == Planet.NORTH_NODE), None)
        if north_node:
            south_node_degree = (north_node.degree + 180) % 360
            south_sign, south_sign_degree = self.ephemeris.get_zodiac_sign(
                south_node_degree
            )
            planets.append(
                PlanetPosition(
                    planet=Planet.SOUTH_NODE,
                    sign=south_sign,
                    degree=south_node_degree,
                    sign_degree=south_sign_degree,
                    retrograde=True,  # Nodes are always retrograde
                    house=None,
                )
            )

        return planets

    def calculate_houses(
        self,
        birth_dt: datetime,
        latitude: float,
        longitude: float,
        timezone: str,
        system: str = "P",  # Placidus
    ) -> Optional[list[House]]:
        """
        Calculate house cusps.

        Args:
            birth_dt: Birth datetime (local time)
            latitude: Birth place latitude
            longitude: Birth place longitude
            timezone: Birth place timezone
            system: House system ('P'=Placidus, 'K'=Koch, 'W'=Whole Sign, etc.)

        Returns:
            List of 12 Houses or None if calculation fails
        """
        try:
            import pytz
            local_tz = pytz.timezone(timezone)
            if birth_dt.tzinfo is None:
                birth_dt = local_tz.localize(birth_dt)
            utc_dt = birth_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception:
            utc_dt = birth_dt

        if self.ephemeris._swe is None:
            # Fallback: use Whole Sign houses
            return self._calculate_whole_sign_houses(utc_dt)

        try:
            swe = self.ephemeris._swe

            # Convert to Julian Day
            jd = swe.julday(
                utc_dt.year, utc_dt.month, utc_dt.day,
                utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
            )

            # Calculate houses
            cusps, ascmc = swe.houses(jd, latitude, longitude, system.encode())

            houses = []
            for i in range(12):
                cusp_degree = cusps[i]
                sign, degree_in_sign = self.ephemeris.get_zodiac_sign(cusp_degree)

                houses.append(
                    House(
                        number=i + 1,
                        sign=sign,
                        degree=degree_in_sign,
                        planets=[],
                    )
                )

            return houses

        except Exception as e:
            logger.warning(f"House calculation failed: {e}")
            return self._calculate_whole_sign_houses(utc_dt)

    def _calculate_whole_sign_houses(self, utc_dt: datetime) -> list[House]:
        """
        Calculate Whole Sign houses (simplified fallback).
        Uses Sun sign as 1st house.
        """
        sun_data = self.ephemeris.calculate_planet_position(Planet.SUN, utc_dt)
        sun_sign, _ = self.ephemeris.get_zodiac_sign(sun_data.longitude)

        # Get index of sun sign
        signs = list(ZodiacSign)
        start_index = signs.index(sun_sign)

        houses = []
        for i in range(12):
            sign_index = (start_index + i) % 12
            houses.append(
                House(
                    number=i + 1,
                    sign=signs[sign_index],
                    degree=0.0,
                    planets=[],
                )
            )

        return houses

    def calculate_aspects(
        self,
        planets: list[PlanetPosition],
    ) -> list[Aspect]:
        """
        Calculate aspects between planets.

        Args:
            planets: List of planet positions

        Returns:
            List of aspects between planets
        """
        aspects = []

        # Only major planets for aspects
        major_planets = [
            Planet.SUN, Planet.MOON, Planet.MERCURY, Planet.VENUS,
            Planet.MARS, Planet.JUPITER, Planet.SATURN,
            Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO,
        ]

        planet_map = {p.planet: p for p in planets if p.planet in major_planets}

        checked_pairs = set()

        for planet1_enum in major_planets:
            for planet2_enum in major_planets:
                if planet1_enum == planet2_enum:
                    continue

                # Avoid duplicate pairs
                pair = tuple(sorted([planet1_enum.value, planet2_enum.value]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                planet1 = planet_map.get(planet1_enum)
                planet2 = planet_map.get(planet2_enum)

                if not planet1 or not planet2:
                    continue

                aspect = self._find_aspect(planet1, planet2)
                if aspect:
                    aspects.append(aspect)

        return aspects

    def _find_aspect(
        self,
        planet1: PlanetPosition,
        planet2: PlanetPosition,
    ) -> Optional[Aspect]:
        """
        Find aspect between two planets if within orb.

        Returns:
            Aspect if found, None otherwise
        """
        # Calculate angular separation
        diff = abs(planet1.degree - planet2.degree)
        if diff > 180:
            diff = 360 - diff

        # Check each aspect type
        for aspect_type, exact_angle in ASPECT_ANGLES.items():
            orb = ASPECT_ORBS[aspect_type]
            deviation = abs(diff - exact_angle)

            if deviation <= orb:
                # Determine if applying or separating
                # (simplified: based on faster planet approaching slower)
                applying = self._is_applying(planet1, planet2, aspect_type)

                return Aspect(
                    planet1=planet1.planet,
                    planet2=planet2.planet,
                    aspect_type=aspect_type,
                    orb=deviation,
                    applying=applying,
                )

        return None

    def _is_applying(
        self,
        planet1: PlanetPosition,
        planet2: PlanetPosition,
        aspect_type: AspectType,
    ) -> bool:
        """
        Determine if aspect is applying (forming) or separating.
        Simplified heuristic based on position.
        """
        # Moon and inner planets generally move faster
        fast_planets = [Planet.MOON, Planet.SUN, Planet.MERCURY, Planet.VENUS, Planet.MARS]

        if planet1.planet in fast_planets and planet2.planet not in fast_planets:
            # Planet1 is faster, check if moving toward exact aspect
            return True
        elif planet2.planet in fast_planets and planet1.planet not in fast_planets:
            return False

        # Default to applying for simplicity
        return True

    def assign_planets_to_houses(
        self,
        planets: list[PlanetPosition],
        houses: list[House],
    ) -> list[PlanetPosition]:
        """
        Assign planets to their houses based on position.

        Args:
            planets: List of planet positions
            houses: List of houses with cusps

        Returns:
            Updated planet positions with house assignments
        """
        # Get house cusp degrees
        cusp_degrees = [
            h.degree + (list(ZodiacSign).index(h.sign) * 30)
            for h in houses
        ]

        for planet in planets:
            # Find which house the planet falls in
            for i in range(12):
                next_i = (i + 1) % 12
                start = cusp_degrees[i]
                end = cusp_degrees[next_i]

                if end < start:  # Crosses 0 degrees
                    if planet.degree >= start or planet.degree < end:
                        planet.house = i + 1
                        houses[i].planets.append(planet.planet)
                        break
                else:
                    if start <= planet.degree < end:
                        planet.house = i + 1
                        houses[i].planets.append(planet.planet)
                        break

        return planets
