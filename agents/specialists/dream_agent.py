"""Dream analysis specialist agent.

Tools: dream analysis (Hall/Van de Castle + Jungian + REM/NREM + DreamBank
norms) plus pure-data lookups for symbols, archetypes, and H/VdC categories.
"""

from agents.base import BaseOneiroAgent

DREAM_TOOLS: list[str] = [
    "analyze_dream",
    "dream_series_stats",
    # Folded KB lookups: dream_symbols / dream_archetypes / hvdc_categories.
    "lookup",
]


class DreamAgent(BaseOneiroAgent):
    """Specialist for dream interpretation grounded in peer-reviewed methodology."""

    name = "dream"

    def default_tools(self) -> list[str]:
        return DREAM_TOOLS
