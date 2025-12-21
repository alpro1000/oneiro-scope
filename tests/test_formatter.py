from backend.services.astrology.formatter import ChartFormatter, PLANET_SYMBOLS
from backend.services.astrology.schemas import Aspect, AspectType, Planet, PlanetPosition, ZodiacSign


def build_planet_positions():
    signs = list(ZodiacSign)
    planets = list(Planet)
    positions = []
    for idx, planet in enumerate(planets):
        positions.append(
            PlanetPosition(
                planet=planet,
                sign=signs[idx % len(signs)],
                degree=float((idx * 15) % 360),
                sign_degree=float((idx * 15) % 30),
                retrograde=bool(idx % 2),
                house=(idx % 12) + 1,
            )
        )
    return positions


def test_markdown_contains_all_planets():
    formatter = ChartFormatter(language="ru", style="scientific", output_format="markdown")
    planets = build_planet_positions()
    report = formatter.generate(planets)

    for planet in Planet:
        symbol = PLANET_SYMBOLS.get(planet, "")
        formatted = formatter._format_planet(next(p for p in planets if p.planet == planet)).title
        planet_label = formatted.split(" **")[1].split("**")[0]
        assert planet_label in report or symbol in report


def test_translations_and_formats():
    formatter = ChartFormatter(language="en", style="poetic", output_format="markdown")
    planets = build_planet_positions()
    report = formatter.generate(planets)

    assert "Sun in" in report
    assert "(Овен" in report or "(Стрелец" in report  # Russian translation included


def test_aspects_render_with_orb():
    planets = build_planet_positions()
    sun = next(p for p in planets if p.planet == Planet.SUN)
    moon = next(p for p in planets if p.planet == Planet.MOON)
    aspect = Aspect(
        planet1=sun.planet,
        planet2=moon.planet,
        aspect_type=AspectType.TRINE,
        orb=1.25,
        applying=True,
    )

    formatter = ChartFormatter(language="ru", style="scientific", output_format="markdown")
    report = formatter.generate(planets, aspects=[aspect])

    assert "1.25" in report
    assert "Трин" in report
    assert "☉" in report and "☽" in report


def test_json_output_structure():
    formatter = ChartFormatter(language="en", output_format="json")
    planets = build_planet_positions()
    result = formatter.generate(planets)

    assert "planets" in result
    assert len(result["planets"]) == len(planets)
    assert result["title"] == "Natal Chart"
    assert any("title" in entry for entry in result["planets"])

