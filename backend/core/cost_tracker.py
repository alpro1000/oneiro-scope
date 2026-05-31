"""LLM cost tracker.

Records per-provider call counts and estimated $ spend, persisting to Redis
when available and falling back to a thread-safe in-memory store otherwise.
Designed to never raise — instrumentation must not break the request path.

Keys (Redis):
    oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:calls       (INT, INCR)
    oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:input_tok   (INT, INCRBY)
    oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:output_tok  (INT, INCRBY)
    oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:usd_micro   (INT, INCRBY in micro-USD)

The `<agent>` segment defaults to `default` (or the value of the
`ONEIRO_AGENT_NAME` env var, which the SuperOrchestrator sets when
spawning specialist MCP children). Older callers that omit the agent
parameter continue to write under `default`, so `report()` without an
agent filter still sums everything.

In-memory fallback uses the same key structure under `_MEM`.
"""

from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_MEM: dict[str, int] = defaultdict(int)

# Resolved lazily so tests / sync paths don't need an event loop just to import.
_redis_client = None
_redis_attempted = False


def _maybe_redis():
    """Return a sync Redis client or None. Cached after first call."""
    global _redis_client, _redis_attempted
    if _redis_attempted:
        return _redis_client
    _redis_attempted = True
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(url, socket_timeout=0.5, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("cost_tracker: Redis connected at %s", url)
    except Exception as exc:  # pragma: no cover - infra dependent
        logger.warning("cost_tracker: Redis unavailable (%s), using memory", exc)
        _redis_client = None
    return _redis_client


def _resolve_agent(agent: Optional[str]) -> str:
    """Pick the agent tag: explicit > env > 'default'."""
    return agent or os.getenv("ONEIRO_AGENT_NAME") or "default"


def _key(provider: str, suffix: str, day: date_cls, agent: str) -> str:
    return f"oneiro:cost:{provider}:{agent}:{day.isoformat()}:{suffix}"


def record(
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cost_per_1k_tokens: float,
    when: Optional[date_cls] = None,
    agent: Optional[str] = None,
) -> None:
    """Record a single LLM call. Never raises.

    Args:
        provider: Provider name ("groq", "gemini", "openai", "anthropic", "together").
        input_tokens: Prompt tokens consumed.
        output_tokens: Completion tokens generated.
        cost_per_1k_tokens: Price per 1k tokens for this model (from `LLMModel.cost_per_1k_tokens`).
        when: Date bucket (UTC). Default: today.
        agent: Specialist tag ("astrology" / "dream" / "lunar" / "oneiro").
            Defaults to env var `ONEIRO_AGENT_NAME`, then "default".
    """
    try:
        day = when or date_cls.today()
        tag = _resolve_agent(agent)
        total_tokens = int(input_tokens) + int(output_tokens)
        usd_micro = int(round(total_tokens / 1000 * cost_per_1k_tokens * 1_000_000))

        client = _maybe_redis()
        if client is not None:
            pipe = client.pipeline()
            pipe.incr(_key(provider, "calls", day, tag))
            pipe.incrby(_key(provider, "input_tok", day, tag), int(input_tokens))
            pipe.incrby(_key(provider, "output_tok", day, tag), int(output_tokens))
            pipe.incrby(_key(provider, "usd_micro", day, tag), usd_micro)
            # 60-day TTL on each — keeps the per-day buckets bounded.
            for suffix in ("calls", "input_tok", "output_tok", "usd_micro"):
                pipe.expire(_key(provider, suffix, day, tag), 60 * 86400)
            pipe.execute()
            return

        with _LOCK:
            _MEM[_key(provider, "calls", day, tag)] += 1
            _MEM[_key(provider, "input_tok", day, tag)] += int(input_tokens)
            _MEM[_key(provider, "output_tok", day, tag)] += int(output_tokens)
            _MEM[_key(provider, "usd_micro", day, tag)] += usd_micro
    except Exception as exc:  # pragma: no cover
        logger.warning("cost_tracker.record failed: %s", exc)


@dataclass
class ProviderUsage:
    provider: str
    calls: int
    input_tokens: int
    output_tokens: int
    usd: float
    # Per-agent breakdown; None unless `report(group_by_agent=True)`.
    by_agent: Optional[dict[str, dict]] = None


# Known agent tags. The orchestrator sets ONEIRO_AGENT_NAME from this set;
# we iterate it (plus "default" for legacy callers) when aggregating.
_AGENT_TAGS = ("default", "oneiro", "astrology", "dream", "lunar")


def report(
    start: date_cls,
    end: date_cls,
    provider: Optional[str] = None,
    agent: Optional[str] = None,
    group_by_agent: bool = False,
) -> list[ProviderUsage]:
    """Aggregate usage for [start, end] inclusive.

    Args:
        start: First day (UTC) to include.
        end: Last day (UTC), inclusive.
        provider: Filter to a single provider, or None for all.
        agent: Filter to a single agent tag, or None to sum across all.
        group_by_agent: When true, include a per-agent breakdown in
            `ProviderUsage.by_agent`.
    """
    if end < start:
        raise ValueError("end < start")
    providers = [provider] if provider else ["groq", "gemini", "together", "openai", "anthropic"]
    agents = [agent] if agent else list(_AGENT_TAGS)
    out: list[ProviderUsage] = []

    client = _maybe_redis()

    for prov in providers:
        calls = inp = outp = micros = 0
        per_agent: dict[str, dict] = {}
        for tag in agents:
            a_calls = a_inp = a_outp = a_micros = 0
            d = start
            while d <= end:
                for suffix in ("calls", "input_tok", "output_tok", "usd_micro"):
                    k = _key(prov, suffix, d, tag)
                    v = client.get(k) if client is not None else _MEM.get(k, 0)
                    v = int(v or 0)
                    if suffix == "calls":
                        a_calls += v
                    elif suffix == "input_tok":
                        a_inp += v
                    elif suffix == "output_tok":
                        a_outp += v
                    else:
                        a_micros += v
                d += timedelta(days=1)
            calls += a_calls
            inp += a_inp
            outp += a_outp
            micros += a_micros
            if group_by_agent and (a_calls or a_inp or a_outp):
                per_agent[tag] = {
                    "calls": a_calls,
                    "input_tokens": a_inp,
                    "output_tokens": a_outp,
                    "usd": a_micros / 1_000_000,
                }
        if calls or inp or outp:
            out.append(
                ProviderUsage(
                    provider=prov,
                    calls=calls,
                    input_tokens=inp,
                    output_tokens=outp,
                    usd=micros / 1_000_000,
                    by_agent=per_agent if group_by_agent else None,
                )
            )
    return out


def reset_memory() -> None:
    """Test helper — wipes the in-memory store."""
    with _LOCK:
        _MEM.clear()
