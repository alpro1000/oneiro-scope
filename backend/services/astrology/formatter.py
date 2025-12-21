"""Human-readable formatting for natal chart calculations.

This module converts raw calculation results from :class:`NatalChartCalculator`
into bilingual (RU/EN) markdown or JSON reports while preserving the scientific
accuracy of the underlying Swiss Ephemeris data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .interpreter import PLANET_DESCRIPTIONS, SIGN_DESCRIPTIONS
from .schemas import Aspect, AspectType, House, Planet, PlanetPosition, ZodiacSign


PLANET_SYMBOLS: dict[Planet, str] = {
    Planet.SUN: "☉",
    Planet.MOON: "☽",
    Planet.MERCURY: "☿",
    Planet.VENUS: "♀",
    Planet.MARS: "♂",
    Planet.JUPITER: "♃",
    Planet.SATURN: "♄",
    Planet.URANUS: "♅",
    Planet.NEPTUNE: "♆",
    Planet.PLUTO: "♇",
    Planet.NORTH_NODE: "☊",
    Planet.SOUTH_NODE: "☋",
    Planet.CHIRON: "⚷",
}


ASPECT_SYMBOLS: dict[AspectType, str] = {
    AspectType.CONJUNCTION: "☌",
    AspectType.SEXTILE: "⚹",
    AspectType.SQUARE: "□",
    AspectType.TRINE: "△",
    AspectType.OPPOSITION: "☍",
    AspectType.QUINCUNX: "⚻",
}


ELEMENT_TRANSLATIONS = {
    "fire": {"ru": "огонь", "en": "fire"},
    "earth": {"ru": "земля", "en": "earth"},
    "air": {"ru": "воздух", "en": "air"},
    "water": {"ru": "вода", "en": "water"},
}


QUALITY_TRANSLATIONS = {
    "cardinal": {"ru": "кардинальный", "en": "cardinal"},
    "fixed": {"ru": "фиксированный", "en": "fixed"},
    "mutable": {"ru": "мутабельный", "en": "mutable"},
}


SIGN_PREPOSITIONAL_RU = {
    ZodiacSign.ARIES: "Овне",
    ZodiacSign.TAURUS: "Тельце",
    ZodiacSign.GEMINI: "Близнецах",
    ZodiacSign.CANCER: "Раке",
    ZodiacSign.LEO: "Льве",
    ZodiacSign.VIRGO: "Деве",
    ZodiacSign.LIBRA: "Весах",
    ZodiacSign.SCORPIO: "Скорпионе",
    ZodiacSign.SAGITTARIUS: "Стрельце",
    ZodiacSign.CAPRICORN: "Козероге",
    ZodiacSign.AQUARIUS: "Водолее",
    ZodiacSign.PISCES: "Рыбах",
}


ASPECT_NAMES = {
    "ru": {
        AspectType.CONJUNCTION: "Соединение",
        AspectType.SEXTILE: "Секстиль",
        AspectType.SQUARE: "Квадрат",
        AspectType.TRINE: "Трин",
        AspectType.OPPOSITION: "Оппозиция",
        AspectType.QUINCUNX: "Квинконс",
    },
    "en": {
        AspectType.CONJUNCTION: "Conjunction",
        AspectType.SEXTILE: "Sextile",
        AspectType.SQUARE: "Square",
        AspectType.TRINE: "Trine",
        AspectType.OPPOSITION: "Opposition",
        AspectType.QUINCUNX: "Quincunx",
    },
}


ASPECT_DESCRIPTIONS = {
    "scientific": {
        "ru": "аспект с орбом {orb:.2f}° ({applying})",
        "en": "aspect with {orb:.2f}° orb ({applying})",
    },
    "poetic": {
        "ru": "тонкая связь с орбом {orb:.2f}° ({applying})",
        "en": "a subtle tie with {orb:.2f}° orb ({applying})",
    },
}


APPLYING_TRANSLATIONS = {
    "ru": {True: "нарастающий", False: "расходящийся"},
    "en": {True: "applying", False: "separating"},
}


PLANET_NAMES_EN = {
    Planet.SUN: "Sun",
    Planet.MOON: "Moon",
    Planet.MERCURY: "Mercury",
    Planet.VENUS: "Venus",
    Planet.MARS: "Mars",
    Planet.JUPITER: "Jupiter",
    Planet.SATURN: "Saturn",
    Planet.URANUS: "Uranus",
    Planet.NEPTUNE: "Neptune",
    Planet.PLUTO: "Pluto",
    Planet.NORTH_NODE: "North Node",
    Planet.SOUTH_NODE: "South Node",
    Planet.CHIRON: "Chiron",
}


SIGN_NAMES_EN = {
    ZodiacSign.ARIES: "Aries",
    ZodiacSign.TAURUS: "Taurus",
    ZodiacSign.GEMINI: "Gemini",
    ZodiacSign.CANCER: "Cancer",
    ZodiacSign.LEO: "Leo",
    ZodiacSign.VIRGO: "Virgo",
    ZodiacSign.LIBRA: "Libra",
    ZodiacSign.SCORPIO: "Scorpio",
    ZodiacSign.SAGITTARIUS: "Sagittarius",
    ZodiacSign.CAPRICORN: "Capricorn",
    ZodiacSign.AQUARIUS: "Aquarius",
    ZodiacSign.PISCES: "Pisces",
}


@dataclass
class FormattedPlanet:
    """Structured representation of a formatted planet entry."""

    title: str
    description: str
    raw: PlanetPosition


class ChartFormatter:
    """Render natal chart calculations into Markdown or JSON."""

    def __init__(self, language: str = "ru", style: str = "scientific", output_format: str = "markdown"):
        self.language = language if language in {"ru", "en"} else "ru"
        self.style = style if style in {"scientific", "poetic"} else "scientific"
        self.output_format = output_format if output_format in {"markdown", "json"} else "markdown"

    def generate(
        self,
        planets: Iterable[PlanetPosition],
        houses: Optional[Iterable[House]] = None,
        aspects: Optional[Iterable[Aspect]] = None,
    ):
        """Generate a formatted report for the natal chart."""

        planet_entries = [self._format_planet(planet) for planet in planets]
        aspect_entries = [self._format_aspect(aspect, planet_entries) for aspect in aspects or []]
        ascendant_entry = self._format_ascendant(houses)

        if self.output_format == "json":
            return {
                "title": "Natal Chart" if self.language == "en" else "Натальная карта",
                "planets": [self._planet_to_dict(entry) for entry in planet_entries],
                "ascendant": ascendant_entry,
                "aspects": aspect_entries,
            }

        return self._render_markdown(planet_entries, ascendant_entry, aspect_entries)

    def _render_markdown(self, planets: list[FormattedPlanet], ascendant: Optional[dict], aspects: list[dict]) -> str:
        title = "# Natal Chart" if self.language == "en" else "# Натальная карта"
        lines: list[str] = [title]

        if ascendant:
            lines.append(ascendant["title"])
            lines.append(ascendant["description"])
            lines.append("")

        for entry in planets:
            lines.append(entry.title)
            lines.append(entry.description)
            lines.append("")

        if aspects:
            lines.append("**Aspects:**" if self.language == "en" else "**Аспекты:**")
            for aspect in aspects:
                lines.append(f"- {aspect['text']}")

        return "\n".join(line.rstrip() for line in lines if line is not None)

    def _format_planet(self, planet: PlanetPosition) -> FormattedPlanet:
        sign_data = SIGN_DESCRIPTIONS.get(planet.sign)
        planet_data = PLANET_DESCRIPTIONS.get(planet.planet)
        sign_ru = sign_data.get("ru") if sign_data else planet.sign.value
        sign_en = SIGN_NAMES_EN.get(planet.sign, planet.sign.value.title())
        planet_ru = planet_data.get("ru") if planet_data else planet.planet.value
        planet_en = PLANET_NAMES_EN.get(planet.planet, planet.planet.value.title())

        preposition_ru = SIGN_PREPOSITIONAL_RU.get(planet.sign, sign_ru)
        symbol = PLANET_SYMBOLS.get(planet.planet, "")
        retrograde_marker = " (R)" if planet.retrograde else ""

        if self.language == "ru":
            title = f"{symbol} **{planet_ru} в {preposition_ru} ({sign_en})**{retrograde_marker}  "
        else:
            title = f"{symbol} **{planet_en} in {sign_en} ({sign_ru})**{retrograde_marker}  "

        description = self._planet_description(planet, sign_data, planet_data)

        return FormattedPlanet(title=title, description=description, raw=planet)

    def _planet_description(self, planet: PlanetPosition, sign_data: dict, planet_data: dict) -> str:
        element = ELEMENT_TRANSLATIONS.get(sign_data.get("element")) if sign_data else None
        quality = QUALITY_TRANSLATIONS.get(sign_data.get("quality")) if sign_data else None
        keywords = sign_data.get("keywords", []) + planet_data.get("keywords", []) if sign_data and planet_data else []

        if self.language == "ru":
            element_txt = f"Элемент: {element['ru'].capitalize()}" if element else ""
            quality_txt = f"Качество: {quality['ru'].capitalize()}" if quality else ""
            keywords_txt = "Ключевые слова: " + ", ".join(keywords) if keywords else ""
            base = " · ".join(filter(None, [element_txt, quality_txt, keywords_txt]))
            if self.style == "poetic":
                base = base + " — энергия раскрывается интуитивно." if base else "Энергия проявляется интуитивно."
            return base

        element_txt = f"Element: {element['en'].capitalize()}" if element else ""
        quality_txt = f"Mode: {quality['en'].capitalize()}" if quality else ""
        keywords_txt = "Keywords: " + ", ".join(keywords) if keywords else ""
        base = " · ".join(filter(None, [element_txt, quality_txt, keywords_txt]))
        if self.style == "poetic":
            base = base + " — energy flows in its own rhythm." if base else "Energy flows in its own rhythm."
        return base

    def _format_aspect(self, aspect: Aspect, planets: list[FormattedPlanet]) -> dict:
        planet_map = {entry.raw.planet: entry for entry in planets}
        p1 = planet_map.get(aspect.planet1)
        p2 = planet_map.get(aspect.planet2)

        p1_name = PLANET_NAMES_EN.get(aspect.planet1, aspect.planet1.value.title())
        p2_name = PLANET_NAMES_EN.get(aspect.planet2, aspect.planet2.value.title())
        p1_local = PLANET_DESCRIPTIONS.get(aspect.planet1, {}).get("ru", p1_name)
        p2_local = PLANET_DESCRIPTIONS.get(aspect.planet2, {}).get("ru", p2_name)

        p1_label = p1.title.split("**")[1].split("**")[0] if p1 else p1_name
        p2_label = p2.title.split("**")[1].split("**")[0] if p2 else p2_name

        aspect_symbol = ASPECT_SYMBOLS.get(aspect.aspect_type, "")
        aspect_name = ASPECT_NAMES[self.language][aspect.aspect_type]
        applying = APPLYING_TRANSLATIONS[self.language][aspect.applying]
        aspect_template = ASPECT_DESCRIPTIONS[self.style][self.language]
        detail = aspect_template.format(orb=aspect.orb, applying=applying)

        if self.language == "ru":
            text = f"{PLANET_SYMBOLS.get(aspect.planet1, '')} {p1_local} {aspect_symbol} {PLANET_SYMBOLS.get(aspect.planet2, '')} {p2_local} ({aspect_name}) — {detail}."
        else:
            text = f"{PLANET_SYMBOLS.get(aspect.planet1, '')} {p1_label} {aspect_symbol} {PLANET_SYMBOLS.get(aspect.planet2, '')} {p2_label} ({aspect_name}) — {detail}."

        return {
            "planet1": aspect.planet1.value,
            "planet2": aspect.planet2.value,
            "aspect": aspect.aspect_type.value,
            "orb": aspect.orb,
            "applying": aspect.applying,
            "text": text,
        }

    def _format_ascendant(self, houses: Optional[Iterable[House]]) -> Optional[dict]:
        if not houses:
            return None

        first_house = next((house for house in houses if house.number == 1), None)
        if not first_house:
            return None

        sign_ru = SIGN_DESCRIPTIONS.get(first_house.sign, {}).get("ru", first_house.sign.value)
        sign_en = SIGN_NAMES_EN.get(first_house.sign, first_house.sign.value.title())
        if self.language == "ru":
            title = f"↑ **Асцендент в {SIGN_PREPOSITIONAL_RU.get(first_house.sign, sign_ru)} (Asc {sign_en})**  "
            description = "Проявление личности вовне."  # concise placeholder, retains scientific data provenance
        else:
            title = f"↑ **Ascendant in {sign_en} ({sign_ru})**  "
            description = "Outward personality expression."

        return {
            "title": title,
            "description": description,
            "sign": first_house.sign.value,
            "degree": first_house.degree,
        }

    def _planet_to_dict(self, planet: FormattedPlanet) -> dict:
        return {
            "planet": planet.raw.planet.value,
            "sign": planet.raw.sign.value,
            "degree": planet.raw.degree,
            "sign_degree": planet.raw.sign_degree,
            "retrograde": planet.raw.retrograde,
            "house": planet.raw.house,
            "title": planet.title,
            "description": planet.description,
        }

