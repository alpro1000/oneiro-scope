"""AI Reasoner for astrological interpretation using multiple LLM providers."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.core.llm_provider import UniversalLLMProvider, LLMProvider
from .prompt_templates import (
    SYSTEM_PROMPT,
    NATAL_CHART_PROMPT,
    HOROSCOPE_PROMPT,
    DAILY_HOROSCOPE_PROMPT,
    WEEKLY_HOROSCOPE_PROMPT,
    MONTHLY_HOROSCOPE_PROMPT,
    YEARLY_HOROSCOPE_PROMPT,
    EVENT_FORECAST_PROMPT,
    format_planets_for_prompt,
    format_aspects_for_prompt,
    format_transits_for_prompt,
)

logger = logging.getLogger(__name__)


class AstroReasoner:
    """
    AI-powered astrological interpretation engine.

    Uses Claude API for generating interpretations based on
    astronomical data and astrological knowledge base.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        preferred_provider: Optional[LLMProvider] = None,
        knowledge_base_path: Optional[Path] = None,
    ):
        """
        Initialize AstroReasoner.

        Args:
            max_tokens: Maximum tokens for response (increased to 4000 for detailed interpretations)
            temperature: Temperature for generation (0.0-1.0)
            preferred_provider: Preferred LLM provider (or None for cheapest)
            knowledge_base_path: Path to knowledge base JSON files
        """
        self.max_tokens = max_tokens

        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)

        # Initialize Universal LLM Provider
        self.llm = UniversalLLMProvider(
            max_tokens=max_tokens,
            temperature=temperature,
            preferred_provider=preferred_provider,
        )

        available = self.llm.get_available_providers()
        if available:
            logger.info(f"AstroReasoner initialized with providers: {', '.join(available)}")
        else:
            logger.warning("No LLM providers available - using fallback mode")

    def _load_knowledge_base(self, path: Optional[Path]) -> dict:
        """Load knowledge base from JSON files."""
        kb = {"planets": {}, "houses": {}, "aspects": {}}

        if path is None:
            path = Path(__file__).parent.parent / "knowledge_base"

        try:
            planets_file = path / "planets.json"
            if planets_file.exists():
                with open(planets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    kb["planets"] = data.get("planets", {})

            houses_file = path / "houses.json"
            if houses_file.exists():
                with open(houses_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    kb["houses"] = data.get("houses", {})

            aspects_file = path / "aspects.json"
            if aspects_file.exists():
                with open(aspects_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    kb["aspects"] = data.get("aspects", {})

            logger.info(
                f"Knowledge base loaded: {len(kb['planets'])} planets, "
                f"{len(kb['houses'])} houses, {len(kb['aspects'])} aspects"
            )
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")

        return kb

    async def interpret_natal_chart(
        self,
        planets: list[dict],
        houses: Optional[list[dict]],
        aspects: list[dict],
        birth_date: str,
        birth_time: Optional[str],
        birth_place: str,
        coords: dict,
        timezone: str,
        locale: str = "ru",
    ) -> str:
        """
        Generate natal chart interpretation.

        Args:
            planets: List of planet positions
            houses: List of house cusps (or None)
            aspects: List of aspects
            birth_date: Birth date string
            birth_time: Birth time string (or None)
            birth_place: Birth place name
            coords: Coordinates dict
            timezone: Timezone string
            locale: Output language

        Returns:
            Interpretation text
        """
        # Format data for prompt
        planets_str = format_planets_for_prompt(planets, locale)
        aspects_str = format_aspects_for_prompt(aspects, locale)

        houses_str = "Дома не рассчитаны (время рождения неизвестно)"
        if houses:
            houses_lines = [
                f"- Дом {h['number']}: {h['sign']} {h['degree']:.1f}°"
                for h in houses
            ]
            houses_str = "\n".join(houses_lines)

        prompt = NATAL_CHART_PROMPT.format(
            birth_date=birth_date,
            birth_time=birth_time or "неизвестно",
            birth_place=birth_place,
            coords=f"{coords['lat']}, {coords['lon']}",
            timezone=timezone,
            planets_json=planets_str,
            houses_json=houses_str,
            aspects_json=aspects_str,
            locale=locale,
        )

        return await self._generate(prompt)

    async def interpret_horoscope(
        self,
        sun_sign: str,
        moon_sign: str,
        ascendant: Optional[str],
        transits: list[dict],
        retrograde_planets: list[str],
        lunar_phase: str,
        lunar_day: int,
        period: str,
        period_start: str,
        period_end: str,
        locale: str = "ru",
    ) -> tuple[str, dict, list[str]]:
        """
        Generate horoscope interpretation.

        Returns:
            Tuple of (summary, sections_dict, recommendations_list)
        """
        transits_str = format_transits_for_prompt(transits, locale)
        retro_str = ", ".join(retrograde_planets) if retrograde_planets else "нет"

        # Select appropriate prompt based on period
        prompt_template = HOROSCOPE_PROMPT  # default
        if period.lower() == "daily":
            prompt_template = DAILY_HOROSCOPE_PROMPT
        elif period.lower() == "weekly":
            prompt_template = WEEKLY_HOROSCOPE_PROMPT
        elif period.lower() == "monthly":
            prompt_template = MONTHLY_HOROSCOPE_PROMPT
        elif period.lower() == "yearly":
            prompt_template = YEARLY_HOROSCOPE_PROMPT

        prompt = prompt_template.format(
            sun_sign=sun_sign,
            moon_sign=moon_sign,
            ascendant=ascendant or "неизвестен",
            transits_json=transits_str,
            retrograde_planets=retro_str,
            lunar_phase=lunar_phase,
            lunar_day=lunar_day,
            period=period,
            period_start=period_start,
            period_end=period_end,
            locale=locale,
        )

        response = await self._generate(prompt)

        # Parse sections from response
        sections = self._parse_horoscope_sections(response, locale)

        return response, sections, sections.get("recommendations", [])

    async def interpret_event_forecast(
        self,
        event_type: str,
        event_date: str,
        event_location: Optional[str],
        sun_sign: str,
        moon_sign: str,
        transits: list[dict],
        retrograde_planets: list[str],
        lunar_phase: str,
        lunar_day: int,
        locale: str = "ru",
    ) -> dict:
        """
        Generate event forecast interpretation.

        Returns:
            Dict with favorability score and interpretation
        """
        transits_str = format_transits_for_prompt(transits, locale)
        retro_str = ", ".join(retrograde_planets) if retrograde_planets else "нет"

        prompt = EVENT_FORECAST_PROMPT.format(
            event_type=event_type,
            event_date=event_date,
            event_location=event_location or "не указано",
            sun_sign=sun_sign,
            moon_sign=moon_sign,
            transits_json=transits_str,
            retrograde_planets=retro_str,
            lunar_phase=lunar_phase,
            lunar_day=lunar_day,
            locale=locale,
        )

        response = await self._generate(prompt)

        # Parse forecast from response
        return self._parse_event_forecast(response, locale)

    async def _generate(self, prompt: str) -> str:
        """Generate response using available LLM provider."""
        result, provider = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        if provider:
            logger.info(f"Generated interpretation using {provider}")
        else:
            logger.warning("Using fallback interpretation (no LLM available)")

        return result

    def _parse_horoscope_sections(self, response: str, locale: str) -> dict:
        """Parse horoscope sections from response."""
        sections = {
            "general": "",
            "personal": "",
            "social": "",
            "warnings": "",
            "recommendations": [],
        }

        # Simple section parsing (can be improved with regex)
        current_section = "general"
        lines = response.split("\n")

        for line in lines:
            line_lower = line.lower()
            if "общая" in line_lower or "general" in line_lower:
                current_section = "general"
            elif "личн" in line_lower or "personal" in line_lower:
                current_section = "personal"
            elif "социал" in line_lower or "social" in line_lower:
                current_section = "social"
            elif "предупреж" in line_lower or "warning" in line_lower:
                current_section = "warnings"
            elif "рекоменд" in line_lower or "recommend" in line_lower:
                current_section = "recommendations"
            else:
                if current_section == "recommendations":
                    if line.strip().startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
                        sections["recommendations"].append(line.strip().lstrip("-•*0123456789. "))
                else:
                    sections[current_section] += line + "\n"

        return sections

    def _parse_event_forecast(self, response: str, locale: str) -> dict:
        """Parse event forecast from response."""
        result = {
            "favorability_score": 50,
            "level": "Нейтрально" if locale == "ru" else "Neutral",
            "positive_factors": [],
            "risk_factors": [],
            "recommendations": [],
            "alternative_dates": [],
            "interpretation": response,
        }

        # Try to extract score
        import re
        score_match = re.search(r"(\d{1,3})\s*%", response)
        if score_match:
            result["favorability_score"] = int(score_match.group(1))

        # Determine level based on score
        score = result["favorability_score"]
        if locale == "ru":
            if score >= 80:
                result["level"] = "Отлично"
            elif score >= 60:
                result["level"] = "Хорошо"
            elif score >= 40:
                result["level"] = "Нейтрально"
            elif score >= 20:
                result["level"] = "Сложно"
            else:
                result["level"] = "Затруднительно"
        else:
            if score >= 80:
                result["level"] = "Excellent"
            elif score >= 60:
                result["level"] = "Good"
            elif score >= 40:
                result["level"] = "Neutral"
            elif score >= 20:
                result["level"] = "Challenging"
            else:
                result["level"] = "Difficult"

        return result

    def get_planet_meaning(self, planet: str, locale: str = "ru") -> dict:
        """Get planet meaning from knowledge base."""
        planet_key = planet.lower().replace(" ", "_")
        planet_data = self.knowledge_base["planets"].get(planet_key, {})
        return planet_data.get("interpretation", {}).get(locale, {})

    def get_aspect_meaning(self, aspect: str, locale: str = "ru") -> dict:
        """Get aspect meaning from knowledge base."""
        aspect_key = aspect.lower().replace("-", "_")
        aspect_data = self.knowledge_base["aspects"].get(aspect_key, {})
        return aspect_data.get("interpretation", {}).get(locale, {})

    def get_house_meaning(self, house: int, locale: str = "ru") -> dict:
        """Get house meaning from knowledge base."""
        house_data = self.knowledge_base["houses"].get(str(house), {})
        return house_data.get("interpretation", {}).get(locale, {})
