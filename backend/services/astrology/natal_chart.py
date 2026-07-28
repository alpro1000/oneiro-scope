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



def _to_utc_or_raise(birth_dt: datetime, timezone: str) -> datetime:
    """Convert a naive local birth datetime to naive UTC, or refuse.

    This used to be `except Exception: utc_dt = birth_dt` — on an unparseable
    zone the *local* time was treated as UTC, silently shifting the chart by the
    whole offset. Three hours for Ukraine is ~45 deg of Midheaven: not a
    degraded chart, a different one. Since the zone reaches here either from
    GeoNames/TimezoneFinder (always a valid IANA name) or from a
    schema-validated caller override, a failure now means a real bug — and a
    chart computed from the wrong instant is worse than no chart at all.
    """
    import pytz

    try:
        local_tz = pytz.timezone(timezone)
    except Exception as exc:
        raise ValueError(
            f"Unknown timezone {timezone!r} — refusing to compute a chart, "
            f"because treating local time as UTC would shift it by the whole "
            f"offset (~15 deg of Midheaven per hour)."
        ) from exc

    if birth_dt.tzinfo is None:
        birth_dt = local_tz.localize(birth_dt)
    return birth_dt.astimezone(pytz.UTC).replace(tzinfo=None)

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
        utc_dt = _to_utc_or_raise(birth_dt, timezone)

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
                    speed_deg_per_day=data.speed,
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
                    # The south node is the antipode: same angular rate.
                    speed_deg_per_day=north_node.speed_deg_per_day,
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
    ) -> list[House]:
        """
        Calculate house cusps.

        The provenance promises Placidus — so a failure here raises instead
        of silently swapping the house system (conventions.md §12). Swiss
        Ephemeris itself handles circumpolar latitudes internally; an
        exception from swe.houses means broken input or setup, not a
        situation a different methodology should paper over.

        Args:
            birth_dt: Birth datetime (local time)
            latitude: Birth place latitude
            longitude: Birth place longitude
            timezone: Birth place timezone
            system: House system ('P'=Placidus, 'K'=Koch, 'W'=Whole Sign, etc.)

        Returns:
            List of 12 Houses with absolute cusp longitudes
        """
        utc_dt = _to_utc_or_raise(birth_dt, timezone)
        swe = self.ephemeris._swe

        jd = swe.julday(
            utc_dt.year, utc_dt.month, utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        )

        try:
            cusps, ascmc = swe.houses(jd, latitude, longitude, system.encode())
        except Exception as exc:
            raise RuntimeError(
                f"House calculation ({system}) failed for jd={jd}, "
                f"lat={latitude}, lon={longitude}: {exc}"
            ) from exc

        houses = []
        for i in range(12):
            cusp_degree = cusps[i]
            sign, degree_in_sign = self.ephemeris.get_zodiac_sign(cusp_degree)

            houses.append(
                House(
                    number=i + 1,
                    sign=sign,
                    degree=degree_in_sign,
                    cusp_degree=cusp_degree % 360.0,
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

        Applying/separating comes from both bodies' actual speeds: the
        aspect is applying when the deviation from the exact angle is
        shrinking. A retrograde body flips the geometry by itself — no
        planet-class heuristics.

        Returns:
            Aspect if found, None otherwise
        """
        # Signed separation in (-180, 180]; delta = |s| is the angular distance.
        s = (planet1.degree - planet2.degree + 180.0) % 360.0 - 180.0
        delta = abs(s)

        speed1 = planet1.speed_deg_per_day or 0.0
        speed2 = planet2.speed_deg_per_day or 0.0
        speed_diff = speed1 - speed2
        # d(delta)/dt: |s| grows at (speed1-speed2) when s>0, shrinks when s<0.
        d_delta_dt = speed_diff if s >= 0 else -speed_diff

        for aspect_type, exact_angle in ASPECT_ANGLES.items():
            orb = ASPECT_ORBS[aspect_type]
            deviation = delta - exact_angle

            if abs(deviation) <= orb:
                # |deviation| is shrinking ⇔ the aspect is closing on exact.
                applying = deviation * d_delta_dt < 0

                return Aspect(
                    planet1=planet1.planet,
                    planet2=planet2.planet,
                    aspect_type=aspect_type,
                    orb=abs(deviation),
                    orb_deg=abs(deviation),
                    applying=applying,
                    speed_diff_deg_per_day=speed_diff,
                )

        return None

    def assign_planets_to_houses(
        self,
        planets: list[PlanetPosition],
        houses: list[House],
    ) -> list[PlanetPosition]:
        """
        Assign planets to their houses based on position.

        Fills both directions of the relation — planet.house and
        houses[i].planets — plus the cusp-proximity flags: a planet within
        1° of either bounding cusp gets house_borderline=True, because a
        few minutes of birth-time error would move it into the next house.

        Args:
            planets: List of planet positions
            houses: List of houses with cusps

        Returns:
            Updated planet positions with house assignments
        """
        cusp_degrees = [
            h.cusp_degree
            if h.cusp_degree is not None
            else h.degree + (list(ZodiacSign).index(h.sign) * 30)
            for h in houses
        ]

        for planet in planets:
            for i in range(12):
                next_i = (i + 1) % 12
                start = cusp_degrees[i]
                end = cusp_degrees[next_i]

                in_house = (
                    (planet.degree >= start or planet.degree < end)
                    if end < start  # house spans 0° Aries
                    else (start <= planet.degree < end)
                )
                if in_house:
                    planet.house = i + 1
                    houses[i].planets.append(planet.planet)
                    to_prev = (planet.degree - start) % 360.0
                    to_next = (end - planet.degree) % 360.0
                    distance = min(to_prev, to_next)
                    planet.distance_to_cusp_deg = round(distance, 3)
                    planet.house_borderline = distance < 1.0
                    break

        return planets
