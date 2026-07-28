"""WP-2/WP-3 acceptance: houses in calculate_natal_chart + real applying/separating.

Reference chart (owner-supplied): 1977-07-01 22:30, Zaporizhzhia
(47.8388N 35.1396E, tz resolved from coordinates → Europe/Zaporozhye,
= 19:30 UT). Expected Placidus placements: Mars/Venus 3rd, Jupiter 4th,
Sun/Mercury 5th, Saturn 6th, Pluto 7th, Uranus 8th, Neptune 10th,
Moon 12th.

The tests go through AstrologyService.calculate_natal_chart — the exact
path the MCP tool wraps — because that is where houses used to come back
unassigned: assign_planets_to_houses existed but nothing called it.
"""

import asyncio
from datetime import date, time

import pytest

from backend.services.astrology import AstrologyService, NatalChartRequest
from backend.services.astrology.schemas import Planet

EXPECTED_HOUSES = {
    Planet.MARS: 3,
    Planet.VENUS: 3,
    Planet.JUPITER: 4,
    Planet.SUN: 5,
    Planet.MERCURY: 5,
    Planet.SATURN: 6,
    Planet.PLUTO: 7,
    Planet.URANUS: 8,
    Planet.NEPTUNE: 10,
    Planet.MOON: 12,
}


def _calculate(birth_time):
    req = NatalChartRequest(
        birth_date=date(1977, 7, 1),
        birth_time=birth_time,
        birth_place="Zaporizhzhia",
        latitude=47.8388,
        longitude=35.1396,
        locale="ru",
    )
    return asyncio.run(
        AstrologyService().calculate_natal_chart(req, interpret=False)
    )


@pytest.fixture(scope="module")
def chart():
    return _calculate(time(22, 30))


def test_houses_present_with_cusps(chart):
    assert chart.houses is not None and len(chart.houses) == 12
    for house in chart.houses:
        assert house.cusp_degree is not None
    assert chart.ascendant is not None and chart.midheaven is not None


def test_reference_placements_match_owner_chart(chart):
    by_planet = {p.planet: p for p in chart.planets}
    mismatches = {
        planet.value: (by_planet[planet].house, expected)
        for planet, expected in EXPECTED_HOUSES.items()
        if by_planet[planet].house != expected
    }
    assert not mismatches, f"(actual, expected): {mismatches}"


def test_planet_house_relation_is_bidirectional(chart):
    houses_by_number = {h.number: h for h in chart.houses}
    for planet in chart.planets:
        assert planet.house is not None, f"{planet.planet} has no house"
        assert planet.planet in houses_by_number[planet.house].planets
    for house in chart.houses:
        for planet_name in house.planets:
            planet = next(p for p in chart.planets if p.planet == planet_name)
            assert planet.house == house.number


def test_borderline_flags_mark_cusp_proximity(chart):
    by_planet = {p.planet: p for p in chart.planets}
    # Pluto sits ~0.33° from the 8th cusp: the canonical borderline case.
    pluto = by_planet[Planet.PLUTO]
    assert pluto.house_borderline is True
    assert pluto.distance_to_cusp_deg is not None
    assert pluto.distance_to_cusp_deg < 0.5
    # Sun is deep inside the 5th (≥8° from either cusp).
    sun = by_planet[Planet.SUN]
    assert sun.house_borderline is False
    assert sun.distance_to_cusp_deg > 5.0
    # The flag must be exactly (distance < 1°) for every placed planet.
    for planet in chart.planets:
        assert planet.house_borderline == (planet.distance_to_cusp_deg < 1.0)


def test_aspects_carry_orb_and_speed_fields(chart):
    assert chart.aspects, "reference chart must have aspects"
    for aspect in chart.aspects:
        assert aspect.orb_deg is not None
        assert aspect.orb_deg == pytest.approx(aspect.orb)
        assert aspect.speed_diff_deg_per_day is not None


def test_applying_is_not_constant(chart):
    """The July audit's live natal had 20/20 aspects applying:true — the
    heuristic defaulted to True. Real speeds must produce both values."""
    values = {a.applying for a in chart.aspects}
    assert values == {True, False}


def test_applying_math_on_known_pairs(chart):
    def find(p1, p2):
        return next(
            a for a in chart.aspects
            if {a.planet1, a.planet2} == {p1, p2}
        )

    # Moon 289.2° (+14.92°/d) trine Venus 54.9° (+1.04°/d): deviation 5.7°
    # and shrinking — applying.
    moon_venus = find(Planet.MOON, Planet.VENUS)
    assert moon_venus.aspect_type.value == "trine"
    assert moon_venus.applying is True

    # Sun 99.8° (+0.95°/d) opposite Moon 289.2° (+14.92°/d): Moon is 9.4°
    # past exact opposition and pulling away — separating.
    sun_moon = find(Planet.SUN, Planet.MOON)
    assert sun_moon.aspect_type.value == "opposition"
    assert sun_moon.applying is False


def test_without_birth_time_houses_stay_honestly_null():
    chart = _calculate(None)
    assert chart.houses is None
    for planet in chart.planets:
        assert planet.house is None
        assert planet.house_borderline is None
        assert planet.distance_to_cusp_deg is None


def test_planets_carry_speed(chart):
    by_planet = {p.planet: p for p in chart.planets}
    assert by_planet[Planet.MOON].speed_deg_per_day == pytest.approx(14.92, abs=0.1)
    # Uranus was retrograde on 1977-07-01 — speed must be negative and the
    # retrograde flag must agree with it.
    uranus = by_planet[Planet.URANUS]
    assert uranus.speed_deg_per_day < 0
    assert uranus.retrograde is True
