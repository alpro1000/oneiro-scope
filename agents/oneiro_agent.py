"""OneiroScope generalist ADK agent.

Backward-compatible single-agent entry point: spawns the MCP server and
exposes all 13 OneiroScope tools to one model in one session. Useful for
ad-hoc use via `python -m agents.cli` and for older skills that haven't
moved to the SuperOrchestrator (Phase C).

For domain-specialized contexts and parallel multi-domain workflows,
use the specialist agents in `agents.specialists` (Phase B) or the
orchestrator (Phase C, planned).
"""

from __future__ import annotations

from pathlib import Path

from agents.base import BaseOneiroAgent

# Catalog of every tool the OneiroScope MCP server exposes. Kept here so
# the generalist mirrors the full surface; specialists import their own
# narrower subsets.
ALL_ONEIRO_TOOLS: list[str] = [
    # Astrology
    "calculate_natal_chart",
    "forecast_event",
    # Dreams
    "analyze_dream",
    # Lunar
    "get_lunar_day",
    "get_lunar_period",
    # Geo helpers
    "search_city",
    "validate_birth_data",
    # Folded knowledge-base lookups (WP-10): event types, horoscope
    # periods, dream symbols/archetypes/HVdC categories, archetype tables.
    "lookup",
]


_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "oneiro_system.md"


class OneiroAgent(BaseOneiroAgent):
    """Generalist agent with access to all OneiroScope MCP tools."""

    name = "oneiro"

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("name", "oneiro")
        kwargs.setdefault("system_prompt_path", _SYSTEM_PROMPT_PATH)
        kwargs.setdefault("allowed_tools", ALL_ONEIRO_TOOLS)
        super().__init__(**kwargs)

    def default_tools(self) -> list[str]:
        return ALL_ONEIRO_TOOLS
