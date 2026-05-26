"""OneiroScope ADK agent.

Wraps the Claude Agent SDK around the OneiroScope MCP server. The MCP
server is launched as a child process (stdio) and exposed to the model
as the canonical tool surface.

Usage:
    import asyncio
    from agents.oneiro_agent import OneiroAgent

    async def main():
        agent = OneiroAgent()
        async for chunk in agent.run("Натальная карта для 15 мая 1990, Москва, 14:30"):
            print(chunk, end="", flush=True)

    asyncio.run(main())

Or via the CLI:
    python -m agents.cli "natal 1990-05-15 14:30 Moscow"

Requires:
    pip install claude-agent-sdk
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import AsyncIterator, Optional

try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
    )
    from claude_agent_sdk.types import McpServerConfig
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "claude-agent-sdk is not installed. Run: pip install claude-agent-sdk"
    ) from exc


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "oneiro_system.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _build_mcp_config() -> dict[str, McpServerConfig]:
    """Spawn the OneiroScope MCP server as a stdio child process."""
    server_cfg: McpServerConfig = {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "backend.mcp.server"],
        "env": {
            **os.environ,
            "PYTHONPATH": str(_REPO_ROOT),
        },
    }
    return {"oneiro": server_cfg}


class OneiroAgent:
    """High-level orchestrator. One instance ≈ one conversation session."""

    def __init__(
        self,
        *,
        model: str = "claude-opus-4-7",
        max_turns: int = 12,
        permission_mode: str = "acceptEdits",
        cwd: Optional[Path] = None,
    ) -> None:
        self.options = ClaudeAgentOptions(
            model=model,
            system_prompt=_load_system_prompt(),
            mcp_servers=_build_mcp_config(),
            allowed_tools=[
                # Restrict the agent to OneiroScope MCP tools — no shell, no fs.
                "mcp__oneiro__calculate_natal_chart",
                "mcp__oneiro__generate_horoscope",
                "mcp__oneiro__forecast_event",
                "mcp__oneiro__list_event_types",
                "mcp__oneiro__list_horoscope_periods",
                "mcp__oneiro__analyze_dream",
                "mcp__oneiro__list_dream_symbols",
                "mcp__oneiro__list_archetypes",
                "mcp__oneiro__list_hvdc_categories",
                "mcp__oneiro__get_lunar_day",
                "mcp__oneiro__get_lunar_period",
                "mcp__oneiro__search_city",
                "mcp__oneiro__validate_birth_data",
            ],
            permission_mode=permission_mode,
            max_turns=max_turns,
            cwd=str(cwd or _REPO_ROOT),
        )

    async def run(self, user_message: str) -> AsyncIterator[str]:
        """Stream text chunks from the agent for a single user turn."""
        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(user_message)
            async for message in client.receive_response():
                # Yield only assistant text deltas. Tool calls/results pass
                # silently — they're visible to the model, not the user.
                content = getattr(message, "content", None)
                if not content:
                    continue
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        yield text
