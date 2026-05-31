"""Lunar calendar specialist agent.

Tools: deterministic lunar-day lookups for a single date or a range.
No LLM-bound tools — this specialist is mostly a thin reporting layer
over Swiss Ephemeris output.
"""

from agents.base import BaseOneiroAgent

LUNAR_TOOLS: list[str] = [
    "get_lunar_day",
    "get_lunar_period",
]


class LunarAgent(BaseOneiroAgent):
    """Specialist for lunar-calendar queries."""

    name = "lunar"

    def default_tools(self) -> list[str]:
        return LUNAR_TOOLS
