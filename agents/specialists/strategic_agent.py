"""Strategic Life Cycle Analyst — top-level synthesis agent.

This agent is the **Strategic Analyst** layer: it takes a decision
question from the user, calls the deterministic chart tools
(transits, solar return, astrocartography), then produces an evidence-
matrix response that separates astronomy from astrology from life
context. Astrology is one layer, not the source of truth.

It has access to a broader tool set than the domain specialists
because synthesis questions cross domains (year-ahead + relocation +
career timing).
"""

from agents.base import BaseOneiroAgent

STRATEGIC_TOOLS: list[str] = [
    # Core natal & validation
    "calculate_natal_chart",
    "validate_birth_data",
    "search_city",
    # Deterministic astronomy (confidence 1.0)
    "compute_transits",
    "solar_return_chart",
    "astrocartography_scan",
    "get_lunar_day",
    "get_lunar_period",
    # Hard archetype tables (confidence 0.9 — cited tradition, NOT LLM)
    "mc_in_sign",
    "sun_in_sign",
    "house_meaning",
    "aspect_meaning",
    "planet_dignity",
    "zodiac_sign",
    "list_archetype_topics",
    # Symbolic / LLM-narrative (confidence 0.7 — last resort)
    "generate_horoscope",
    "forecast_event",
    "list_event_types",
    "list_horoscope_periods",
]


class StrategicAnalystAgent(BaseOneiroAgent):
    """Decision-support synthesis agent with the Strategic Analyst posture."""

    name = "strategic"

    def default_tools(self) -> list[str]:
        return STRATEGIC_TOOLS
