"""SuperOrchestrator (Phase C).

Routes the user message to one or more domain specialists, runs them in
parallel for multi-domain requests, and merges their responses.

Routing is keyword-based (cheap, deterministic, no extra LLM call). If
nothing matches, we fall back to astrology as the default domain — that
matches the project's primary intent.

The orchestrator does NOT pass natal-chart context between specialists
yet — that requires `natal_chart_id` persistence (tracked in §5 known
issues). For now each specialist is invoked independently and the
results are merged with domain headers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Iterable

from agents.specialists import AstrologyAgent, DreamAgent, LunarAgent

logger = logging.getLogger(__name__)


# Keyword rules. Lowercased substrings — Cyrillic roots cover inflections
# ("сон/снил/приснил…" all match "сон" / "снил"). English uses bare words.
_ASTROLOGY_KEYWORDS: tuple[str, ...] = (
    # Russian — roots picked to avoid collisions ("гороск" not "горо",
    # which would also match "город").
    "натал", "гороск", "транзит", "ретроград", "зодиак", "планет",
    "венер", "марс", "юпитер", "сатурн", "асцендент",
    "событие", "событий", "форкаст",
    # English
    "horoscope", "natal", "transit", "retrograde", "zodiac", "planet",
    "ascendant", "midheaven", "forecast", "event favorab",
)
_DREAM_KEYWORDS: tuple[str, ...] = (
    "снил", "сон ", " сны", "сновид", "приснил", "кошмар", "архетип",
    "dream", "dreamt", "dreamed", "nightmare", "archetype",
)
_LUNAR_KEYWORDS: tuple[str, ...] = (
    "лунн", "лунный день", "фаза луны", "новолун", "полнолун",
    "lunar", "moon ", "moon-", "moon phase", "moonph",
)

_DEFAULT_DOMAIN = "astrology"


def classify_intent(text: str) -> list[str]:
    """Return the ordered list of specialist domains relevant to `text`.

    Multiple may match (e.g. "истолкуй мой сон в контексте лунного дня"
    → ["dream", "lunar"]). Empty match falls back to the default domain.
    """
    t = text.lower()
    domains: list[str] = []
    if any(k in t for k in _ASTROLOGY_KEYWORDS):
        domains.append("astrology")
    if any(k in t for k in _DREAM_KEYWORDS):
        domains.append("dream")
    if any(k in t for k in _LUNAR_KEYWORDS):
        domains.append("lunar")
    if not domains:
        domains.append(_DEFAULT_DOMAIN)
    return domains


class SuperOrchestrator:
    """Dispatches user turns to specialist agents and merges their output."""

    SPECIALISTS = {
        "astrology": AstrologyAgent,
        "dream": DreamAgent,
        "lunar": LunarAgent,
    }

    def __init__(self, *, model: str = "claude-opus-4-7", max_turns: int = 12) -> None:
        self._model = model
        self._max_turns = max_turns
        # Lazy: instantiate a specialist only when it's first dispatched to.
        self._instances: dict[str, object] = {}

    def _get(self, name: str):
        if name not in self._instances:
            cls = self.SPECIALISTS[name]
            self._instances[name] = cls(model=self._model, max_turns=self._max_turns)
        return self._instances[name]

    def classify(self, text: str) -> list[str]:
        """Public hook so callers can preview routing without invoking agents."""
        return classify_intent(text)

    async def run(self, user_message: str) -> AsyncIterator[str]:
        """Route, fan out, merge. Streams text chunks back to the caller."""
        domains = self.classify(user_message)
        logger.info("[orchestrator] intent=%s agents=%s", user_message[:60], domains)

        # Single-domain: passthrough, preserve streaming.
        if len(domains) == 1:
            async for chunk in self._get(domains[0]).run(user_message):
                yield chunk
            return

        # Multi-domain: run in parallel; only emit per-agent text once each
        # finishes so the merged output is readable. Each specialist returns
        # (name, text) so we can pair exceptions with their domain below.
        async def _collect(name: str) -> tuple[str, str]:
            buf: list[str] = []
            async for chunk in self._get(name).run(user_message):
                buf.append(chunk)
            return name, "".join(buf)

        # return_exceptions=True so one specialist's failure doesn't kill
        # the whole multi-domain request — we surface partial results and
        # log the failures.
        coros = [_collect(n) for n in domains]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for name, result in zip(domains, results):
            if isinstance(result, BaseException):
                logger.error(
                    "[orchestrator] specialist %s failed: %s", name, result
                )
                yield (
                    f"\n## {name.title()}\n\n"
                    f"_(specialist temporarily unavailable: {type(result).__name__})_\n"
                )
                continue
            _name, text = result
            yield f"\n## {_name.title()}\n\n{text}\n"
