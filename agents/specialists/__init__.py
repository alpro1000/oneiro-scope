"""OneiroScope specialist agents (Phase B).

Each specialist is a `BaseOneiroAgent` with a narrow MCP-tool subset and a
domain-specific system prompt. The SuperOrchestrator (Phase C) picks the
right specialist(s) for each user intent and merges their answers.
"""

from agents.specialists.astrology_agent import AstrologyAgent
from agents.specialists.dream_agent import DreamAgent
from agents.specialists.lunar_agent import LunarAgent

__all__ = ["AstrologyAgent", "DreamAgent", "LunarAgent"]
