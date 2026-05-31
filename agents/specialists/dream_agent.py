"""Dream analysis specialist agent.

Tools: dream analysis (Hall/Van de Castle + Jungian + REM/NREM + DreamBank
norms) plus pure-data lookups for symbols, archetypes, and H/VdC categories.
"""

from agents.base import BaseOneiroAgent

DREAM_TOOLS: list[str] = [
    "analyze_dream",
    "list_dream_symbols",
    "list_archetypes",
    "list_hvdc_categories",
]


class DreamAgent(BaseOneiroAgent):
    """Specialist for dream interpretation grounded in peer-reviewed methodology."""

    name = "dream"

    def default_tools(self) -> list[str]:
        return DREAM_TOOLS
