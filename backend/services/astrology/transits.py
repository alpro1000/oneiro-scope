"""Transit calculations module."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from .ephemeris import SwissEphemeris
from .schemas import (
    Aspect,
    AspectType,
    Planet,
    PlanetPosition,
    TransitInfo,
)

logger = logging.getLogger(__name__)

# Transit orbs (tighter than natal)
TRANSIT_ORBS = {
    AspectType.CONJUNCTION: 3,
    AspectType.OPPOSITION: 3,
    AspectType.TRINE: 2,
    AspectType.SQUARE: 2,
    AspectType.SEXTILE: 2,
    AspectType.QUINCUNX: 1,
}

# Aspect angles
ASPECT_ANGLES = {
    AspectType.CONJUNCTION: 0,
    AspectType.SEXTILE: 60,
    AspectType.SQUARE: 90,
    AspectType.TRINE: 120,
    AspectType.QUINCUNX: 150,
    AspectType.OPPOSITION: 180,
}

# Transit descriptions for interpretation
TRANSIT_MEANINGS = {
    (Planet.JUPITER, AspectType.CONJUNCTION): "expansion and opportunity",
    (Planet.JUPITER, AspectType.TRINE): "flowing growth and good fortune",
    (Planet.JUPITER, AspectType.SEXTILE): "opportunities for growth",
    (Planet.JUPITER, AspectType.SQUARE): "tension around expansion",
    (Planet.JUPITER, AspectType.OPPOSITION): "balancing growth with restraint",

    (Planet.SATURN, AspectType.CONJUNCTION): "structure and responsibility",
    (Planet.SATURN, AspectType.TRINE): "disciplined progress",
    (Planet.SATURN, AspectType.SEXTILE): "productive effort",
    (Planet.SATURN, AspectType.SQUARE): "tests and challenges",
    (Planet.SATURN, AspectType.OPPOSITION): "balancing duty and desire",

    (Planet.MARS, AspectType.CONJUNCTION): "energy and action",
    (Planet.MARS, AspectType.TRINE): "motivated action",
    (Planet.MARS, AspectType.SEXTILE): "active opportunities",
    (Planet.MARS, AspectType.SQUARE): "friction and conflict",
    (Planet.MARS, AspectType.OPPOSITION): "confrontation with others",

    (Planet.VENUS, AspectType.CONJUNCTION): "love and harmony",
    (Planet.VENUS, AspectType.TRINE): "pleasant relationships",
    (Planet.VENUS, AspectType.SEXTILE): "social opportunities",
    (Planet.VENUS, AspectType.SQUARE): "relationship tension",
    (Planet.VENUS, AspectType.OPPOSITION): "balancing self and other",

    (Planet.MERCURY, AspectType.CONJUNCTION): "communication focus",
    (Planet.MERCURY, AspectType.TRINE): "clear thinking",
    (Planet.MERCURY, AspectType.SEXTILE): "good conversations",
    (Planet.MERCURY, AspectType.SQUARE): "mental tension",
    (Planet.MERCURY, AspectType.OPPOSITION): "different perspectives",

    (Planet.URANUS, AspectType.CONJUNCTION): "sudden change and awakening",
    (Planet.URANUS, AspectType.TRINE): "breakthrough insights",
    (Planet.URANUS, AspectType.SEXTILE): "innovative opportunities",
    (Planet.URANUS, AspectType.SQUARE): "disruption and tension",
    (Planet.URANUS, AspectType.OPPOSITION): "external shake-ups",

    (Planet.NEPTUNE, AspectType.CONJUNCTION): "inspiration or confusion",
    (Planet.NEPTUNE, AspectType.TRINE): "spiritual flow",
    (Planet.NEPTUNE, AspectType.SEXTILE): "creative inspiration",
    (Planet.NEPTUNE, AspectType.SQUARE): "illusion or deception",
    (Planet.NEPTUNE, AspectType.OPPOSITION): "reality check needed",

    (Planet.PLUTO, AspectType.CONJUNCTION): "transformation and power",
    (Planet.PLUTO, AspectType.TRINE): "empowered change",
    (Planet.PLUTO, AspectType.SEXTILE): "deep opportunities",
    (Planet.PLUTO, AspectType.SQUARE): "power struggles",
    (Planet.PLUTO, AspectType.OPPOSITION): "external transformation",
}


class TransitCalculator:
    """
    Calculator for planetary transits.

    Transits are the current positions of planets
    compared to natal chart positions.
    """

    def __init__(self, ephemeris: SwissEphemeris):
        self.ephemeris = ephemeris

    def calculate_transits(
        self,
        natal_planets: list[PlanetPosition],
        start_date: date,
        end_date: date,
    ) -> list[TransitInfo]:
        """
        Calculate significant transits between natal and transiting planets.

        Args:
            natal_planets: Natal chart planet positions
            start_date: Start of period
            end_date: End of period

        Returns:
            List of TransitInfo for significant aspects
        """
        transits = []

        # Transiting planets to check (outer planets have longer effects)
        transiting_planets = [
            Planet.MARS, Planet.JUPITER, Planet.SATURN,
            Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO,
        ]

        # Natal points to check
        natal_points = [
            Planet.SUN, Planet.MOON, Planet.MERCURY, Planet.VENUS, Planet.MARS,
            Planet.JUPITER, Planet.SATURN,
        ]

        # Check each day in period
        current_date = start_date
        while current_date <= end_date:
            dt = datetime.combine(current_date, datetime.min.time())

            for trans_planet in transiting_planets:
                trans_data = self.ephemeris.calculate_planet_position(trans_planet, dt)
                trans_lon = trans_data.longitude

                for natal_planet_enum in natal_points:
                    natal_pos = next(
                        (p for p in natal_planets if p.planet == natal_planet_enum),
                        None
                    )
                    if not natal_pos:
                        continue

                    # Check for aspect
                    aspect_info = self._find_transit_aspect(
                        trans_planet,
                        trans_lon,
                        natal_planet_enum,
                        natal_pos.degree,
                        current_date,
                    )

                    if aspect_info:
                        # Avoid duplicates
                        existing = next(
                            (t for t in transits
                             if t.transiting_planet == trans_planet
                             and t.natal_planet == natal_planet_enum
                             and t.aspect == aspect_info.aspect),
                            None
                        )
                        if not existing:
                            transits.append(aspect_info)

            current_date += timedelta(days=1)

        return transits

    def _find_transit_aspect(
        self,
        trans_planet: Planet,
        trans_longitude: float,
        natal_planet: Planet,
        natal_longitude: float,
        check_date: date,
    ) -> Optional[TransitInfo]:
        """
        Check if transiting planet makes aspect to natal position.

        Returns:
            TransitInfo if aspect found, None otherwise
        """
        # Calculate angular separation
        diff = abs(trans_longitude - natal_longitude)
        if diff > 180:
            diff = 360 - diff

        # Check each aspect type
        for aspect_type, exact_angle in ASPECT_ANGLES.items():
            orb = TRANSIT_ORBS[aspect_type]
            deviation = abs(diff - exact_angle)

            if deviation <= orb:
                # Get description
                description = TRANSIT_MEANINGS.get(
                    (trans_planet, aspect_type),
                    f"{trans_planet.value} {aspect_type.value} natal {natal_planet.value}"
                )

                return TransitInfo(
                    transiting_planet=trans_planet,
                    natal_planet=natal_planet,
                    aspect=aspect_type,
                    exact_date=check_date,
                    orb=deviation,
                    description=description,
                )

        return None

    def get_retrograde_planets(self, target_date: date) -> list[Planet]:
        """
        Get list of retrograde planets on a date.

        Args:
            target_date: Date to check

        Returns:
            List of retrograde planets
        """
        return self.ephemeris.get_retrograde_planets(target_date)

    def calculate_daily_transits(
        self,
        natal_planets: list[PlanetPosition],
        target_date: date,
    ) -> list[TransitInfo]:
        """
        Get all transits active on a specific date.

        Args:
            natal_planets: Natal chart positions
            target_date: Date to analyze

        Returns:
            List of active transits
        """
        return self.calculate_transits(natal_planets, target_date, target_date)

    def get_major_transit_dates(
        self,
        natal_planets: list[PlanetPosition],
        start_date: date,
        end_date: date,
        trans_planet: Planet,
    ) -> list[tuple[date, TransitInfo]]:
        """
        Find exact dates of major transits from a specific planet.

        Useful for finding when Jupiter or Saturn make exact aspects.

        Args:
            natal_planets: Natal positions
            start_date: Start of search period
            end_date: End of search period
            trans_planet: Planet to track

        Returns:
            List of (date, TransitInfo) for exact aspects
        """
        results = []
        natal_points = [Planet.SUN, Planet.MOON, Planet.MERCURY, Planet.VENUS, Planet.MARS]

        current_date = start_date
        prev_aspects = {}

        while current_date <= end_date:
            dt = datetime.combine(current_date, datetime.min.time())
            trans_data = self.ephemeris.calculate_planet_position(trans_planet, dt)
            trans_lon = trans_data.longitude

            for natal_planet_enum in natal_points:
                natal_pos = next(
                    (p for p in natal_planets if p.planet == natal_planet_enum),
                    None
                )
                if not natal_pos:
                    continue

                aspect_info = self._find_transit_aspect(
                    trans_planet,
                    trans_lon,
                    natal_planet_enum,
                    natal_pos.degree,
                    current_date,
                )

                key = (natal_planet_enum, aspect_info.aspect if aspect_info else None)

                if aspect_info:
                    prev_orb = prev_aspects.get(key)
                    if prev_orb is not None and aspect_info.orb > prev_orb:
                        # Orb is growing, previous date was closest
                        results.append((current_date - timedelta(days=1), aspect_info))

                    prev_aspects[key] = aspect_info.orb
                else:
                    prev_aspects[key] = None

            current_date += timedelta(days=1)

        return results
