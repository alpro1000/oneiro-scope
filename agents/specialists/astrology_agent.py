"""Astrology specialist agent.

Tools: natal-chart calculation, horoscope generation, event forecasting,
plus geocoding/validation helpers (since natal charts always need geo).
"""

from agents.base import BaseOneiroAgent

ASTROLOGY_TOOLS: list[str] = [
    # Core astrology
    "calculate_natal_chart",
    "forecast_event",
    # Geo helpers — natal charts can't proceed without a resolved location.
    "search_city",
    "validate_birth_data",
    # Folded KB lookups (event types, horoscope periods, archetype tables).
    "lookup",
]


class AstrologyAgent(BaseOneiroAgent):
    """Specialist for natal charts, horoscopes, and event forecasts."""

    name = "astrology"

    def default_tools(self) -> list[str]:
        return ASTROLOGY_TOOLS
