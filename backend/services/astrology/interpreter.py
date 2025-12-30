"""LLM-based astrological interpretation."""

import json
import logging
import os
import re
from typing import Optional

from .schemas import (
    Aspect,
    AspectType,
    EventType,
    HoroscopePeriod,
    House,
    Planet,
    PlanetPosition,
    TransitInfo,
    ZodiacSign,
)
from .ai.astro_reasoner import AstroReasoner

logger = logging.getLogger(__name__)

# Load lunar tables for horoscope generation
_LUNAR_TABLES = None


def _load_lunar_tables():
    """Load lunar day descriptions from JSON."""
    global _LUNAR_TABLES
    if _LUNAR_TABLES is not None:
        return _LUNAR_TABLES

    lunar_json_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "lunar_tables.json",
    )

    try:
        with open(lunar_json_path, "r", encoding="utf-8") as f:
            _LUNAR_TABLES = json.load(f)
        logger.info(f"Loaded lunar tables from {lunar_json_path}")
    except Exception as e:
        logger.warning(f"Failed to load lunar tables: {e}")
        _LUNAR_TABLES = {"ru": [], "en": []}

    return _LUNAR_TABLES


# Zodiac sign descriptions
SIGN_DESCRIPTIONS = {
    ZodiacSign.ARIES: {
        "element": "fire",
        "quality": "cardinal",
        "keywords": ["initiative", "courage", "impulsiveness", "leadership"],
        "ru": "Овен",
    },
    ZodiacSign.TAURUS: {
        "element": "earth",
        "quality": "fixed",
        "keywords": ["stability", "sensuality", "persistence", "material"],
        "ru": "Телец",
    },
    ZodiacSign.GEMINI: {
        "element": "air",
        "quality": "mutable",
        "keywords": ["communication", "curiosity", "adaptability", "duality"],
        "ru": "Близнецы",
    },
    ZodiacSign.CANCER: {
        "element": "water",
        "quality": "cardinal",
        "keywords": ["nurturing", "emotion", "protection", "home"],
        "ru": "Рак",
    },
    ZodiacSign.LEO: {
        "element": "fire",
        "quality": "fixed",
        "keywords": ["creativity", "pride", "generosity", "drama"],
        "ru": "Лев",
    },
    ZodiacSign.VIRGO: {
        "element": "earth",
        "quality": "mutable",
        "keywords": ["analysis", "service", "perfectionism", "health"],
        "ru": "Дева",
    },
    ZodiacSign.LIBRA: {
        "element": "air",
        "quality": "cardinal",
        "keywords": ["balance", "partnership", "diplomacy", "aesthetics"],
        "ru": "Весы",
    },
    ZodiacSign.SCORPIO: {
        "element": "water",
        "quality": "fixed",
        "keywords": ["intensity", "transformation", "power", "secrets"],
        "ru": "Скорпион",
    },
    ZodiacSign.SAGITTARIUS: {
        "element": "fire",
        "quality": "mutable",
        "keywords": ["expansion", "philosophy", "adventure", "optimism"],
        "ru": "Стрелец",
    },
    ZodiacSign.CAPRICORN: {
        "element": "earth",
        "quality": "cardinal",
        "keywords": ["ambition", "discipline", "structure", "achievement"],
        "ru": "Козерог",
    },
    ZodiacSign.AQUARIUS: {
        "element": "air",
        "quality": "fixed",
        "keywords": ["innovation", "independence", "humanitarianism", "eccentricity"],
        "ru": "Водолей",
    },
    ZodiacSign.PISCES: {
        "element": "water",
        "quality": "mutable",
        "keywords": ["intuition", "compassion", "imagination", "escapism"],
        "ru": "Рыбы",
    },
}

# Planet descriptions
PLANET_DESCRIPTIONS = {
    Planet.SUN: {"keywords": ["identity", "ego", "vitality", "purpose"], "ru": "Солнце"},
    Planet.MOON: {"keywords": ["emotions", "instincts", "habits", "mother"], "ru": "Луна"},
    Planet.MERCURY: {"keywords": ["communication", "thinking", "learning", "travel"], "ru": "Меркурий"},
    Planet.VENUS: {"keywords": ["love", "beauty", "values", "pleasure"], "ru": "Венера"},
    Planet.MARS: {"keywords": ["action", "desire", "aggression", "energy"], "ru": "Марс"},
    Planet.JUPITER: {"keywords": ["expansion", "luck", "wisdom", "growth"], "ru": "Юпитер"},
    Planet.SATURN: {"keywords": ["structure", "limits", "responsibility", "time"], "ru": "Сатурн"},
    Planet.URANUS: {"keywords": ["revolution", "innovation", "freedom", "sudden change"], "ru": "Уран"},
    Planet.NEPTUNE: {"keywords": ["dreams", "illusion", "spirituality", "confusion"], "ru": "Нептун"},
    Planet.PLUTO: {"keywords": ["transformation", "power", "death/rebirth", "secrets"], "ru": "Плутон"},
    Planet.NORTH_NODE: {"keywords": ["destiny", "growth direction", "karma"], "ru": "Северный узел"},
    Planet.SOUTH_NODE: {"keywords": ["past life", "comfort zone", "release"], "ru": "Южный узел"},
    Planet.CHIRON: {"keywords": ["wound", "healing", "teaching", "vulnerability"], "ru": "Хирон"},
}


class AstrologyInterpreter:
    """
    LLM-based interpreter for astrological data.

    Generates human-readable interpretations of:
    - Natal charts
    - Horoscopes (transits)
    - Event forecasts
    """

    def __init__(self, llm_client=None):
        """
        Initialize interpreter.

        Args:
            llm_client: LLM client for generating interpretations.
                       If None, uses AstroReasoner with template-based fallback.
        """
        self.llm_client = llm_client

        # Initialize AstroReasoner for advanced interpretation
        try:
            self.reasoner = AstroReasoner(
                max_tokens=2000,
                temperature=0.7,
            )
            logger.info("AstroReasoner initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AstroReasoner: {e}")
            self.reasoner = None

    async def interpret_natal_chart(
        self,
        planets: list[PlanetPosition],
        houses: Optional[list[House]],
        aspects: list[Aspect],
        locale: str = "ru",
        birth_date: Optional[str] = None,
        birth_time: Optional[str] = None,
        birth_place: Optional[str] = None,
        coords: Optional[dict] = None,
        timezone: Optional[str] = None,
    ) -> str:
        """
        Generate interpretation of natal chart.

        Args:
            planets: Planet positions
            houses: House cusps (may be None)
            aspects: Aspects between planets
            locale: Language for output
            birth_date: Birth date string (for enhanced prompts)
            birth_time: Birth time string (for enhanced prompts)
            birth_place: Birth place name (for enhanced prompts)
            coords: Coordinates dict (for enhanced prompts)
            timezone: Timezone string (for enhanced prompts)

        Returns:
            Text interpretation
        """
        # Try AstroReasoner first if available and all data provided
        if self.reasoner and birth_date and birth_place and coords and timezone:
            try:
                planets_dict = self._format_planets_for_reasoner(planets)
                houses_dict = self._format_houses_for_reasoner(houses) if houses else None
                aspects_dict = self._format_aspects_for_reasoner(aspects)

                interpretation = await self.reasoner.interpret_natal_chart(
                    planets=planets_dict,
                    houses=houses_dict,
                    aspects=aspects_dict,
                    birth_date=birth_date,
                    birth_time=birth_time,
                    birth_place=birth_place,
                    coords=coords,
                    timezone=timezone,
                    locale=locale,
                )
                return interpretation
            except Exception as e:
                logger.error(f"AstroReasoner failed, falling back to template: {e}")

        # Fallback to template
        return self._template_interpret_natal(planets, houses, aspects, locale)

    async def interpret_horoscope(
        self,
        transits: list[TransitInfo],
        retrograde_planets: list[Planet],
        lunar_phase: str,
        lunar_day: int,
        period: HoroscopePeriod,
        locale: str = "ru",
        sun_sign: Optional[ZodiacSign] = None,
        moon_sign: Optional[ZodiacSign] = None,
        ascendant: Optional[ZodiacSign] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> tuple[str, dict[str, str], list[str]]:
        """
        Generate horoscope interpretation.

        Returns:
            Tuple of (summary, sections_dict, recommendations_list)
        """
        # Try AstroReasoner first if available
        if self.reasoner and sun_sign and moon_sign:
            try:
                transits_dict = [
                    {
                        "transit_planet": PLANET_DESCRIPTIONS.get(t.transiting_planet, {}).get("ru", t.transiting_planet.value),
                        "natal_planet": PLANET_DESCRIPTIONS.get(t.natal_planet, {}).get("ru", t.natal_planet.value),
                        "aspect": t.aspect.value,
                        "orb": t.orb,
                    }
                    for t in transits
                ]

                retro_list = [PLANET_DESCRIPTIONS.get(p, {}).get("ru", p.value) for p in retrograde_planets]

                summary, sections, recommendations = await self.reasoner.interpret_horoscope(
                    sun_sign=SIGN_DESCRIPTIONS.get(sun_sign, {}).get("ru", sun_sign.value),
                    moon_sign=SIGN_DESCRIPTIONS.get(moon_sign, {}).get("ru", moon_sign.value),
                    ascendant=SIGN_DESCRIPTIONS.get(ascendant, {}).get("ru", ascendant.value) if ascendant else None,
                    transits=transits_dict,
                    retrograde_planets=retro_list,
                    lunar_phase=lunar_phase,
                    lunar_day=lunar_day,
                    period=period.value,
                    period_start=period_start or "",
                    period_end=period_end or "",
                    locale=locale,
                )

                # Extract recommendations from sections
                recommendations_list = sections.get("recommendations", [])
                if not recommendations_list:
                    recommendations_list = recommendations

                return summary, sections, recommendations_list
            except Exception as e:
                logger.error(f"AstroReasoner horoscope failed, falling back to template: {e}")

        # Fallback to template
        return self._template_interpret_horoscope(
            transits, retrograde_planets, lunar_phase, lunar_day, period, locale
        )

    async def generate_event_recommendations(
        self,
        event_type: EventType,
        transits: list[TransitInfo],
        positive_factors: list[str],
        risk_factors: list[str],
        locale: str = "ru",
    ) -> list[str]:
        """
        Generate recommendations for an event.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Base recommendations by event type
        event_tips = {
            EventType.TRAVEL: [
                "Проверьте документы заранее" if locale == "ru" else "Check documents in advance",
                "Имейте запасной план" if locale == "ru" else "Have a backup plan",
            ],
            EventType.WEDDING: [
                "Уделите внимание деталям" if locale == "ru" else "Pay attention to details",
                "Сохраняйте спокойствие" if locale == "ru" else "Stay calm",
            ],
            EventType.BUSINESS: [
                "Подготовьте все документы" if locale == "ru" else "Prepare all documents",
                "Будьте готовы к переговорам" if locale == "ru" else "Be ready to negotiate",
            ],
            EventType.INTERVIEW: [
                "Изучите компанию заранее" if locale == "ru" else "Research the company beforehand",
                "Подготовьте вопросы" if locale == "ru" else "Prepare questions",
            ],
            EventType.SURGERY: [
                "Следуйте рекомендациям врача" if locale == "ru" else "Follow doctor's recommendations",
                "Обеспечьте поддержку близких" if locale == "ru" else "Ensure support from loved ones",
            ],
        }

        recommendations.extend(event_tips.get(event_type, []))

        # Add transit-based recommendations
        for transit in transits:
            if transit.aspect in [AspectType.SQUARE, AspectType.OPPOSITION]:
                if locale == "ru":
                    recommendations.append(
                        f"Учитывайте влияние {PLANET_DESCRIPTIONS[transit.transiting_planet]['ru']}"
                    )
                else:
                    recommendations.append(
                        f"Consider the influence of {transit.transiting_planet.value}"
                    )

        # Add retrograde warnings
        if Planet.MERCURY in [t.transiting_planet for t in transits]:
            if locale == "ru":
                recommendations.append("Перепроверьте все коммуникации")
            else:
                recommendations.append("Double-check all communications")

        return recommendations[:5]  # Limit to 5 recommendations

    async def interpret_natal_structured(
        self,
        planets: list[PlanetPosition],
        houses: Optional[list[House]],
        aspects: list[Aspect],
        locale: str = "ru",
        birth_date: Optional[str] = None,
        birth_time: Optional[str] = None,
        birth_place: Optional[str] = None,
        coords: Optional[dict] = None,
        timezone: Optional[str] = None,
    ) -> dict:
        """
        Generate structured interpretation of natal chart.

        Returns:
            Dict with keys: personality, strengths, challenges, relationships, career, life_purpose
        """
        # Get full interpretation
        full_interpretation = await self.interpret_natal_chart(
            planets=planets,
            houses=houses,
            aspects=aspects,
            locale=locale,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=birth_place,
            coords=coords,
            timezone=timezone,
        )

        # Parse structured sections from interpretation
        sections = self._parse_structured_sections(full_interpretation, locale)

        return sections

    def _parse_structured_sections(self, interpretation: str, locale: str) -> dict:
        """Parse structured sections from interpretation text."""
        sections = {
            "personality": "",
            "strengths": "",
            "challenges": "",
            "relationships": "",
            "career": "",
            "life_purpose": "",
        }

        # Section markers (RU and EN)
        markers = {
            "personality": [
                "общая характеристика", "personality", "личность",
                "характер", "core", "identity"
            ],
            "strengths": [
                "сильные стороны", "strengths", "таланты",
                "talents", "abilities", "достоинства"
            ],
            "challenges": [
                "зоны роста", "challenges", "сложности",
                "трудности", "areas of growth", "проблемы"
            ],
            "relationships": [
                "отношения", "relationships", "любовь",
                "love", "партнерство", "partnership"
            ],
            "career": [
                "карьера", "career", "профессия",
                "работа", "work", "profession"
            ],
            "life_purpose": [
                "предназначение", "life purpose", "purpose",
                "миссия", "mission", "calling"
            ],
        }

        # Split by sections
        lines = interpretation.split("\n")
        current_section = None
        current_text = []

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()

            # Check if this line is a section header
            matched_section = None
            for section_key, keywords in markers.items():
                if any(keyword in line_lower for keyword in keywords):
                    # Check if it looks like a header (starts with #, **, or numbered)
                    if (line_clean.startswith("#") or
                        line_clean.startswith("**") or
                        line_clean.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")) or
                        line_clean.endswith(":")):
                        matched_section = section_key
                        break

            if matched_section:
                # Save previous section
                if current_section and current_text:
                    sections[current_section] = "\n".join(current_text).strip()
                current_section = matched_section
                current_text = []
            elif current_section:
                # Add line to current section
                current_text.append(line_clean)

        # Save last section
        if current_section and current_text:
            sections[current_section] = "\n".join(current_text).strip()

        # Fallback: if sections are empty, try to extract from full text
        if not any(sections.values()):
            # Just put everything in personality as fallback
            sections["personality"] = interpretation

        return sections

    def _format_planets_for_reasoner(self, planets: list[PlanetPosition]) -> list[dict]:
        """Format planets for AstroReasoner."""
        result = []
        for p in planets:
            sign_info = SIGN_DESCRIPTIONS.get(p.sign, {})
            planet_info = PLANET_DESCRIPTIONS.get(p.planet, {})

            result.append({
                "name": planet_info.get("ru", p.planet.value),
                "sign": sign_info.get("ru", p.sign.value),
                "sign_degree": p.sign_degree,
                "retrograde": p.retrograde,
                "house": p.house,
            })
        return result

    def _format_houses_for_reasoner(self, houses: list[House]) -> list[dict]:
        """Format houses for AstroReasoner."""
        result = []
        for h in houses:
            sign_info = SIGN_DESCRIPTIONS.get(h.sign, {})
            result.append({
                "number": h.number,
                "sign": sign_info.get("ru", h.sign.value),
                "degree": h.cusp_degree,
            })
        return result

    def _format_aspects_for_reasoner(self, aspects: list[Aspect]) -> list[dict]:
        """Format aspects for AstroReasoner."""
        result = []
        for a in aspects:
            p1_info = PLANET_DESCRIPTIONS.get(a.planet1, {})
            p2_info = PLANET_DESCRIPTIONS.get(a.planet2, {})

            result.append({
                "planet1": p1_info.get("ru", a.planet1.value),
                "planet2": p2_info.get("ru", a.planet2.value),
                "type": a.aspect_type.value,
                "orb": a.orb,
                "applying": a.applying,
            })
        return result

    def _template_interpret_natal(
        self,
        planets: list[PlanetPosition],
        houses: Optional[list[House]],
        aspects: list[Aspect],
        locale: str,
    ) -> str:
        """Template-based natal chart interpretation (fallback)."""
        lines = []

        # Sun sign
        sun = next((p for p in planets if p.planet == Planet.SUN), None)
        moon = next((p for p in planets if p.planet == Planet.MOON), None)

        if sun:
            sign_info = SIGN_DESCRIPTIONS[sun.sign]
            if locale == "ru":
                lines.append(f"**Солнце в {sign_info['ru']}е**")
                lines.append(f"Ваша основная энергия связана с качествами {sign_info['ru']}а: "
                           f"{', '.join(sign_info['keywords'][:3])}.")
            else:
                lines.append(f"**Sun in {sun.sign.value.title()}**")
                lines.append(f"Your core energy relates to {sun.sign.value} qualities: "
                           f"{', '.join(sign_info['keywords'][:3])}.")

        if moon:
            sign_info = SIGN_DESCRIPTIONS[moon.sign]
            if locale == "ru":
                lines.append(f"\n**Луна в {sign_info['ru']}е**")
                lines.append(f"Ваши эмоциональные потребности выражаются через призму {sign_info['ru']}а.")
            else:
                lines.append(f"\n**Moon in {moon.sign.value.title()}**")
                lines.append(f"Your emotional needs are expressed through {moon.sign.value} energy.")

        # Aspects
        if aspects:
            if locale == "ru":
                lines.append("\n**Ключевые аспекты:**")
            else:
                lines.append("\n**Key Aspects:**")

            for aspect in aspects[:5]:
                p1 = PLANET_DESCRIPTIONS[aspect.planet1]["ru" if locale == "ru" else "keywords"][0]
                p2 = PLANET_DESCRIPTIONS[aspect.planet2]["ru" if locale == "ru" else "keywords"][0]
                if locale == "ru":
                    lines.append(f"- {p1} {aspect.aspect_type.value} {p2}")
                else:
                    lines.append(f"- {aspect.planet1.value} {aspect.aspect_type.value} {aspect.planet2.value}")

        return "\n".join(lines)

    def _template_interpret_horoscope(
        self,
        transits: list[TransitInfo],
        retrograde_planets: list[Planet],
        lunar_phase: str,
        lunar_day: int,
        period: HoroscopePeriod,
        locale: str,
    ) -> tuple[str, dict[str, str], list[str]]:
        """Template-based horoscope interpretation (fallback)."""
        tables = _load_lunar_tables()

        # Map phase keys to Russian/English
        phase_names_ru = {
            "new_moon": "Новолуние",
            "waxing_crescent": "Растущий серп",
            "first_quarter": "Первая четверть",
            "waxing_gibbous": "Растущая Луна",
            "full_moon": "Полнолуние",
            "waning_gibbous": "Убывающая Луна",
            "last_quarter": "Последняя четверть",
            "waning_crescent": "Убывающий серп",
        }
        phase_names_en = {
            "new_moon": "New Moon",
            "waxing_crescent": "Waxing Crescent",
            "first_quarter": "First Quarter",
            "waxing_gibbous": "Waxing Gibbous",
            "full_moon": "Full Moon",
            "waning_gibbous": "Waning Gibbous",
            "last_quarter": "Last Quarter",
            "waning_crescent": "Waning Crescent",
        }

        # Summary
        if locale == "ru":
            phase_display = phase_names_ru.get(lunar_phase, lunar_phase)
            summary = f"{lunar_day} лунный день. {phase_display}. "
            if retrograde_planets:
                retro_names = [PLANET_DESCRIPTIONS[p]["ru"] for p in retrograde_planets]
                summary += f"Ретроградные планеты: {', '.join(retro_names)}."
        else:
            phase_display = phase_names_en.get(lunar_phase, lunar_phase)
            summary = f"Lunar day {lunar_day}. {phase_display}. "
            if retrograde_planets:
                retro_names = [p.value for p in retrograde_planets]
                summary += f"Retrograde planets: {', '.join(retro_names)}."

        # Get lunar day info from tables
        lunar_info = None
        if 1 <= lunar_day <= 30:
            lang_tables = tables.get(locale, tables.get("ru", []))
            if lunar_day < len(lang_tables):
                lunar_info = lang_tables[lunar_day]

        # Sections based on lunar phase and day
        sections = {}
        recommendations = []

        # Generate sections from lunar data
        if locale == "ru":
            if lunar_info and isinstance(lunar_info, dict):
                lunar_type = lunar_info.get("type", "")
                lunar_notes = lunar_info.get("notes", "")
                sections["energy"] = f"Энергия дня: {lunar_type}. {lunar_notes}"
            else:
                sections["energy"] = f"{lunar_day} лунный день несёт особую энергетику."

            # Love section based on phase
            if "full_moon" in lunar_phase or "waxing" in lunar_phase:
                sections["love"] = "Благоприятное время для открытого общения и проявления чувств."
            elif "waning" in lunar_phase:
                sections["love"] = "Время для углубления отношений и работы над взаимопониманием."
            else:
                sections["love"] = "Период перехода в отношениях. Хороший момент для рефлексии."

            # Career section based on retrograde planets
            if retrograde_planets:
                sections["career"] = "Ретроградные планеты советуют пересмотреть планы, завершить старые дела."
            else:
                sections["career"] = "Благоприятное время для новых начинаний и активных действий."

            # Health section
            if lunar_day <= 15:  # Растущая Луна
                sections["health"] = "Организм набирает силу. Подходит для начала оздоровительных программ."
            else:  # Убывающая Луна
                sections["health"] = "Время очищения и детоксикации. Уделите внимание отдыху."

            # Recommendations
            recommendations = [
                "Учитывайте фазу Луны при планировании важных дел",
                f"На {lunar_day} лунный день обратите внимание на интуитивные подсказки",
            ]

            if retrograde_planets:
                recommendations.append("В период ретроградности избегайте поспешных решений")

        else:  # English
            if lunar_info and isinstance(lunar_info, dict):
                lunar_type = lunar_info.get("type", "")
                lunar_notes = lunar_info.get("notes", "")
                sections["energy"] = f"Day energy: {lunar_type}. {lunar_notes}"
            else:
                sections["energy"] = f"Lunar day {lunar_day} carries special energy."

            # Love section based on phase
            if "full_moon" in lunar_phase or "waxing" in lunar_phase:
                sections["love"] = "Favorable time for open communication and expressing feelings."
            elif "waning" in lunar_phase:
                sections["love"] = "Time for deepening relationships and working on mutual understanding."
            else:
                sections["love"] = "Transitional period in relationships. Good moment for reflection."

            # Career section
            if retrograde_planets:
                sections["career"] = "Retrograde planets advise reviewing plans and completing old tasks."
            else:
                sections["career"] = "Favorable time for new beginnings and active initiatives."

            # Health section
            if lunar_day <= 15:  # Waxing Moon
                sections["health"] = "Body is gaining strength. Good for starting wellness programs."
            else:  # Waning Moon
                sections["health"] = "Time for cleansing and detoxification. Focus on rest."

            # Recommendations
            recommendations = [
                "Consider Moon phase when planning important matters",
                f"On lunar day {lunar_day}, pay attention to intuitive insights",
            ]

            if retrograde_planets:
                recommendations.append("During retrograde periods, avoid hasty decisions")

        return summary, sections, recommendations

    async def _llm_interpret_natal(
        self,
        planets: list[PlanetPosition],
        houses: Optional[list[House]],
        aspects: list[Aspect],
        locale: str,
    ) -> str:
        """LLM-based natal chart interpretation."""
        # Format planet data for prompt
        planet_data = []
        for p in planets:
            sign_info = SIGN_DESCRIPTIONS[p.sign]
            planet_data.append({
                "planet": PLANET_DESCRIPTIONS[p.planet]["ru"] if locale == "ru" else p.planet.value,
                "sign": sign_info["ru"] if locale == "ru" else p.sign.value,
                "degree": round(p.sign_degree, 1),
                "retrograde": p.retrograde,
                "house": p.house,
            })

        aspect_data = [
            {
                "planet1": PLANET_DESCRIPTIONS[a.planet1]["ru"] if locale == "ru" else a.planet1.value,
                "planet2": PLANET_DESCRIPTIONS[a.planet2]["ru"] if locale == "ru" else a.planet2.value,
                "aspect": a.aspect_type.value,
                "orb": round(a.orb, 1),
            }
            for a in aspects[:10]
        ]

        prompt = f"""Проанализируй натальную карту и дай интерпретацию на {'русском' if locale == 'ru' else 'английском'} языке.

Планеты: {planet_data}

Аспекты: {aspect_data}

Дай интерпретацию по разделам:
1. Общая характеристика личности
2. Эмоциональная сфера
3. Коммуникация и мышление
4. Отношения
5. Карьера
6. Сильные стороны
7. Зоны роста

Используй научный астрологический подход. Избегай категоричных утверждений."""

        try:
            response = await self.llm_client.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            return self._template_interpret_natal(planets, houses, aspects, locale)

    async def _llm_interpret_horoscope(
        self,
        transits: list[TransitInfo],
        retrograde_planets: list[Planet],
        lunar_phase: str,
        lunar_day: int,
        period: HoroscopePeriod,
        locale: str,
    ) -> tuple[str, dict[str, str], list[str]]:
        """LLM-based horoscope interpretation."""
        # Implementation would call LLM client
        # For now, fallback to template
        return self._template_interpret_horoscope(
            transits, retrograde_planets, lunar_phase, lunar_day, period, locale
        )
