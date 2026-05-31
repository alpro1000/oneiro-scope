"""Base OneiroScope agent.

A specialist agent is a `BaseOneiroAgent` configured with:
- a name (used for cost-tracker tags / logs),
- a system prompt file under `agents/prompts/`,
- a subset of MCP tools it's allowed to call,
- (optional) the model id.

Every specialist spawns the same OneiroScope MCP server as a stdio child —
isolation is at the prompt + allowed_tools level, not the MCP server level.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import AsyncIterator, Iterable, Optional

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    from claude_agent_sdk.types import McpServerConfig
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "claude-agent-sdk is not installed. Run: pip install claude-agent-sdk"
    ) from exc


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _build_mcp_config(agent_name: str) -> dict[str, "McpServerConfig"]:
    """Spawn the OneiroScope MCP server as a stdio child process.

    `agent_name` is propagated via `ONEIRO_AGENT_NAME` so that
    `backend/core/cost_tracker.py` can tag LLM calls per specialist.
    """
    server_cfg: McpServerConfig = {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "backend.mcp.server"],
        "env": {
            **os.environ,
            "PYTHONPATH": str(_REPO_ROOT),
            "ONEIRO_AGENT_NAME": agent_name,
        },
    }
    return {"oneiro": server_cfg}


def _qualify(tool_names: Iterable[str]) -> list[str]:
    """Prepend the MCP server prefix to bare tool names."""
    return [
        n if n.startswith("mcp__") else f"mcp__oneiro__{n}"
        for n in tool_names
    ]


class BaseOneiroAgent:
    """Specialist agent base. One instance ≈ one conversation session."""

    name: str = "base"

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        system_prompt_path: Optional[Path] = None,
        allowed_tools: Optional[Iterable[str]] = None,
        model: str = "claude-opus-4-7",
        max_turns: int = 12,
        permission_mode: str = "acceptEdits",
        cwd: Optional[Path] = None,
    ) -> None:
        if name is not None:
            self.name = name

        if system_prompt_path is None:
            system_prompt_path = _PROMPTS_DIR / f"{self.name}_system.md"
        if allowed_tools is None:
            allowed_tools = self.default_tools()

        self.options = ClaudeAgentOptions(
            model=model,
            system_prompt=Path(system_prompt_path).read_text(encoding="utf-8"),
            mcp_servers=_build_mcp_config(self.name),
            allowed_tools=_qualify(allowed_tools),
            permission_mode=permission_mode,
            max_turns=max_turns,
            cwd=str(cwd or _REPO_ROOT),
        )

    def default_tools(self) -> list[str]:
        """Override in subclasses to declare the tool subset."""
        raise NotImplementedError("Subclass must declare default_tools()")

    async def run(self, user_message: str) -> AsyncIterator[str]:
        """Stream assistant text deltas for a single user turn."""
        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(user_message)
            async for message in client.receive_response():
                content = getattr(message, "content", None)
                if not content:
                    continue
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        yield text
