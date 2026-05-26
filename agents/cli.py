"""OneiroScope agent CLI.

Examples:
    python -m agents.cli "Натальная карта для 15 мая 1990, Москва, 14:30"
    python -m agents.cli "Дневной гороскоп на сегодня"
    python -m agents.cli "Мне приснилось что я лечу над городом..."
    python -m agents.cli --model claude-sonnet-4-6 "Лунный день на 2026-06-01"

Requires `ANTHROPIC_API_KEY` in the environment (the Agent SDK uses it to
talk to the Claude model; the OneiroScope MCP tools themselves may also
use Groq/Gemini/OpenAI/Anthropic, configured via their own env vars).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agents.oneiro_agent import OneiroAgent


async def _drive(prompt: str, model: str) -> int:
    agent = OneiroAgent(model=model)
    async for chunk in agent.run(prompt):
        sys.stdout.write(chunk)
        sys.stdout.flush()
    sys.stdout.write("\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OneiroScope agent CLI")
    parser.add_argument("prompt", help="What to ask the OneiroScope agent.")
    parser.add_argument(
        "--model",
        default="claude-opus-4-7",
        help="Claude model id (default: claude-opus-4-7).",
    )
    args = parser.parse_args()

    return asyncio.run(_drive(args.prompt, args.model))


if __name__ == "__main__":
    sys.exit(main())
