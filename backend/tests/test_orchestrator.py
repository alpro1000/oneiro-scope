"""SuperOrchestrator tests (Phase C).

Cover the intent router (rule-based, deterministic) and the dispatch
shape. The actual Claude API is not invoked — specialists are replaced
by stubs that record what was asked of them.
"""

from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator

import pytest

from agents.orchestrator import SuperOrchestrator, classify_intent


# ---------- intent router -------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Натальная карта для 15 мая 1990 Москва 14:30", ["astrology"]),
        ("Calculate my natal chart 1990-05-15", ["astrology"]),
        ("Дневной гороскоп на сегодня", ["astrology"]),
        ("Weekly horoscope please", ["astrology"]),
        ("Forecast event for 2026-06-01", ["astrology"]),
        ("Мне приснилось что я лечу над городом", ["dream"]),
        ("I dreamt I was falling", ["dream"]),
        ("Лунный день на сегодня", ["lunar"]),
        ("What lunar day is it tomorrow?", ["lunar"]),
        ("Полнолуние когда?", ["lunar"]),
        # Multi-domain
        ("Истолкуй мой сон в контексте лунного дня", ["dream", "lunar"]),
        ("Гороскоп и лунный день на завтра", ["astrology", "lunar"]),
        ("Натальная карта и сон про падение", ["astrology", "dream"]),
    ],
)
def test_classify_intent_routing(text, expected):
    assert classify_intent(text) == expected


def test_classify_intent_empty_falls_back_to_astrology():
    assert classify_intent("hello, what can you do?") == ["astrology"]


# ---------- dispatch shape ------------------------------------------------


class _StubAgent:
    """Drop-in for AstrologyAgent / DreamAgent / LunarAgent."""

    def __init__(self, label: str):
        self.label = label
        self.received: list[str] = []

    async def run(self, msg: str) -> AsyncIterator[str]:
        self.received.append(msg)
        # Two chunks so we can verify streaming concat.
        yield f"[{self.label}] start "
        yield f"answer for: {msg[:30]}"


@pytest.fixture
def orch(monkeypatch):
    """An orchestrator wired with stub specialists (no Claude API needed)."""
    o = SuperOrchestrator()
    # Pre-populate the instance cache so _get() returns our stubs.
    o._instances = {
        "astrology": _StubAgent("astro"),
        "dream": _StubAgent("dream"),
        "lunar": _StubAgent("lunar"),
    }
    return o


@pytest.mark.asyncio
async def test_single_domain_passthrough_streams_raw(orch):
    chunks = []
    async for c in orch.run("Натальная карта для меня"):
        chunks.append(c)
    text = "".join(chunks)
    # Single-domain output is NOT wrapped in headers.
    assert "##" not in text
    assert text.startswith("[astro]")
    assert orch._instances["astrology"].received == ["Натальная карта для меня"]
    # Other specialists must not be invoked.
    assert orch._instances["dream"].received == []
    assert orch._instances["lunar"].received == []


@pytest.mark.asyncio
async def test_multi_domain_runs_fan_out_and_merges_with_headers(orch):
    chunks = []
    async for c in orch.run("Истолкуй мой сон в контексте лунного дня"):
        chunks.append(c)
    text = "".join(chunks)
    # Both stubs were asked.
    assert orch._instances["dream"].received != []
    assert orch._instances["lunar"].received != []
    assert orch._instances["astrology"].received == []
    # Output contains both domain headers.
    assert "## Dream" in text
    assert "## Lunar" in text


class _BrokenAgent:
    """Specialist whose stream raises mid-flight — simulates LLM/MCP failure."""

    def __init__(self, exc: Exception):
        self.exc = exc

    async def run(self, msg: str) -> AsyncIterator[str]:
        # Mark this as a real async generator before raising.
        if False:  # pragma: no cover
            yield ""
        raise self.exc


@pytest.mark.asyncio
async def test_multi_domain_partial_results_when_one_specialist_crashes(orch):
    """A failing specialist must not take down sibling agents.

    Regression for the gather-without-return_exceptions bug spotted in PR
    #117 review. Surviving specialists keep streaming; the failed one
    surfaces as an inline error block tagged with its domain.
    """
    orch._instances["dream"] = _BrokenAgent(RuntimeError("LLM timeout"))
    chunks: list[str] = []
    async for c in orch.run("Истолкуй мой сон в контексте лунного дня"):
        chunks.append(c)
    text = "".join(chunks)

    # The working specialist's output is preserved.
    assert "## Lunar" in text
    assert "[lunar] start" in text

    # The failed one is surfaced, not silently dropped.
    assert "## Dream" in text
    assert "temporarily unavailable" in text
    assert "RuntimeError" in text


@pytest.mark.asyncio
async def test_multi_domain_preserves_router_order(orch):
    """`classify_intent` returns ['astrology','lunar'] for this prompt."""
    chunks = []
    async for c in orch.run("Гороскоп и лунный день на завтра"):
        chunks.append(c)
    text = "".join(chunks)
    a_pos = text.find("## Astrology")
    l_pos = text.find("## Lunar")
    assert a_pos != -1 and l_pos != -1
    assert a_pos < l_pos, "Headers should follow the router-emitted order"


def test_orchestrator_specialists_registry_complete():
    assert set(SuperOrchestrator.SPECIALISTS) == {"astrology", "dream", "lunar"}


def test_lazy_specialist_instantiation():
    """Don't spin up specialists we don't use — saves stdio MCP children."""
    o = SuperOrchestrator()
    assert o._instances == {}


# ---------- cost-tracker agent tag (Phase D) ------------------------------


def test_cost_tracker_tags_via_env(monkeypatch):
    """ONEIRO_AGENT_NAME env propagates into the cost-tracker key."""
    from datetime import date

    from backend.core import cost_tracker

    cost_tracker.reset_memory()
    monkeypatch.setenv("ONEIRO_AGENT_NAME", "astrology")
    cost_tracker.record(
        provider="groq",
        input_tokens=100,
        output_tokens=50,
        cost_per_1k_tokens=0.0,
        when=date.today(),
    )
    monkeypatch.setenv("ONEIRO_AGENT_NAME", "dream")
    cost_tracker.record(
        provider="groq",
        input_tokens=200,
        output_tokens=100,
        cost_per_1k_tokens=0.0,
        when=date.today(),
    )

    # Default report sums across all agent tags.
    overall = cost_tracker.report(date.today(), date.today(), provider="groq")
    assert overall[0].calls == 2
    assert overall[0].input_tokens == 300

    # Filter by single agent.
    astro_only = cost_tracker.report(
        date.today(), date.today(), provider="groq", agent="astrology"
    )
    assert astro_only[0].calls == 1
    assert astro_only[0].input_tokens == 100

    # group_by_agent yields the breakdown.
    grouped = cost_tracker.report(
        date.today(), date.today(), provider="groq", group_by_agent=True
    )
    assert set(grouped[0].by_agent) == {"astrology", "dream"}
    assert grouped[0].by_agent["astrology"]["input_tokens"] == 100
    assert grouped[0].by_agent["dream"]["input_tokens"] == 200

    cost_tracker.reset_memory()


def test_cost_tracker_explicit_agent_arg_wins_over_env(monkeypatch):
    from datetime import date
    from backend.core import cost_tracker

    cost_tracker.reset_memory()
    monkeypatch.setenv("ONEIRO_AGENT_NAME", "astrology")
    cost_tracker.record("groq", 1, 1, 0.0, when=date.today(), agent="lunar")
    rows = cost_tracker.report(
        date.today(), date.today(), provider="groq", agent="lunar"
    )
    assert rows and rows[0].calls == 1
    cost_tracker.reset_memory()


def test_base_agent_sets_agent_env_in_mcp_child(monkeypatch):
    """BaseOneiroAgent propagates its name into the spawned MCP server env."""
    from agents.specialists import AstrologyAgent

    a = AstrologyAgent()
    # The ClaudeAgentOptions object stores mcp_servers as a dict; the
    # 'oneiro' entry must carry ONEIRO_AGENT_NAME=<self.name>.
    servers = a.options.mcp_servers
    env = servers["oneiro"]["env"]
    assert env["ONEIRO_AGENT_NAME"] == "astrology"
