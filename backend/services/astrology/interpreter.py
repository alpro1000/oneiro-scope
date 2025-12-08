"""LLM-based astrological interpretation."""

import logging
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

logger = logging.getLogger(__name__)


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
                       If None, uses template-based fallback.
        """
        self.llm_client = llm_client

    async def interpret_natal_chart(
        self,
        planets: list[PlanetPosition],
        houses: Optional[list[House]],
        aspects: list[Aspect],
        locale: str = "ru",
    ) -> str:
        """
        Generate interpretation of natal chart.

        Args:
            planets: Planet positions
            houses: House cusps (may be None)
            aspects: Aspects between planets
            locale: Language for output

        Returns:
            Text interpretation
        """
        if self.llm_client:
            return await self._llm_interpret_natal(planets, houses, aspects, locale)

        return self._template_interpret_natal(planets, houses, aspects, locale)

    async def interpret_horoscope(
        self,
        transits: list[TransitInfo],
        retrograde_planets: list[Planet],
        lunar_phase: str,
        lunar_day: int,
        period: HoroscopePeriod,
        locale: str = "ru",
    ) -> tuple[str, dict[str, str], list[str]]:
        """
        Generate horoscope interpretation.

        Returns:
            Tuple of (summary, sections_dict, recommendations_list)
        """
        if self.llm_client:
            return await self._llm_interpret_horoscope(
                transits, retrograde_planets, lunar_phase, lunar_day, period, locale
            )

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
        # Summary
        if locale == "ru":
            summary = f"Лунный день: {lunar_day}. Фаза: {lunar_phase}. "
            if retrograde_planets:
                retro_names = [PLANET_DESCRIPTIONS[p]["ru"] for p in retrograde_planets]
                summary += f"Ретроградные планеты: {', '.join(retro_names)}."
        else:
            summary = f"Lunar day: {lunar_day}. Phase: {lunar_phase}. "
            if retrograde_planets:
                retro_names = [p.value for p in retrograde_planets]
                summary += f"Retrograde planets: {', '.join(retro_names)}."

        # Sections
        sections = {}
        if locale == "ru":
            sections["love"] = "Благоприятный период для гармонизации отношений."
            sections["career"] = "Сосредоточьтесь на текущих задачах."
            sections["health"] = "Уделите внимание режиму дня."
        else:
            sections["love"] = "Favorable period for harmonizing relationships."
            sections["career"] = "Focus on current tasks."
            sections["health"] = "Pay attention to your daily routine."

        # Recommendations
        if locale == "ru":
            recommendations = [
                "Планируйте важные дела с учетом лунного цикла",
                "Прислушивайтесь к интуиции",
                "Сохраняйте баланс между работой и отдыхом",
            ]
        else:
            recommendations = [
                "Plan important matters according to the lunar cycle",
                "Listen to your intuition",
                "Maintain balance between work and rest",
            ]

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
