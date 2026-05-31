"""OneiroScope agent CLI.

By default the SuperOrchestrator routes the prompt to one or more
domain specialists (astrology / dream / lunar). Pass `--generalist` to
fall back to the single-agent OneiroAgent with all 13 tools.

Examples:
    python -m agents.cli "Натальная карта для 15 мая 1990, Москва, 14:30"
    python -m agents.cli "Дневной гороскоп на сегодня"
    python -m agents.cli "Мне приснилось что я лечу над городом..."
    python -m agents.cli "Истолкуй мой сон в контексте лунного дня"   # multi-domain
    python -m agents.cli --generalist --model claude-sonnet-4-6 "..."

Requires `ANTHROPIC_API_KEY` for the Claude Agent SDK. Individual MCP
tools may also use Groq/Gemini/OpenAI/Anthropic via their own env vars;
without keys they fall back to deterministic templates.
"""

from __future__ import annotations

import argparse
import asyncio
import sys


async def _drive(prompt: str, model: str, generalist: bool) -> int:
    if generalist:
        from agents.oneiro_agent import OneiroAgent

        agent = OneiroAgent(model=model)
    else:
        from agents.orchestrator import SuperOrchestrator

        agent = SuperOrchestrator(model=model)

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
    parser.add_argument(
        "--generalist",
        action="store_true",
        help="Skip routing; use the single OneiroAgent with all 13 tools.",
    )
    args = parser.parse_args()

    return asyncio.run(_drive(args.prompt, args.model, args.generalist))


if __name__ == "__main__":
    sys.exit(main())
