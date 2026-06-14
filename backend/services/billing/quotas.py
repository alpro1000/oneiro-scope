"""Tier-based quota enforcement.

Tiers (matching the pricing matrix in docs/PLAN.md Phase 6):

- FREE: 1 natal chart (lifetime), 1 horoscope/day, unlimited lunar lookups,
  1 dream analysis (lifetime).
- PREMIUM: unlimited everything.
- PRO: unlimited everything, BUT pro users must supply BYOK keys
  (enforced separately when the LLM provider is constructed).

Quota state lives on the `User` model (free_natal_used, free_dream_used)
plus a small in-memory daily counter for horoscopes (would move to Redis
in production for multi-process safety).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Optional

from fastapi import HTTPException, status

from backend.models.subscription import Subscription
from backend.models.user import User

logger = logging.getLogger(__name__)


class Tier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"


class QuotaKind(str, Enum):
    NATAL_CHART = "natal_chart"
    HOROSCOPE = "horoscope"
    DREAM_ANALYSIS = "dream_analysis"
    EVENT_FORECAST = "event_forecast"
    LUNAR_LOOKUP = "lunar_lookup"


# Daily horoscope counter — process-local; for multi-process deployments
# swap to Redis (oneiro:quota:horoscope:<user_id>:<YYYY-MM-DD>).
_DAILY_LOCK = Lock()
_DAILY_HOROSCOPE: dict[tuple[str, str], int] = defaultdict(int)

# Free-tier numeric limits.
FREE_DAILY_HOROSCOPE_LIMIT = 1
FREE_DAILY_EVENT_FORECAST_LIMIT = 1


def current_tier(user: User, active_subs: Optional[list[Subscription]] = None) -> Tier:
    """Return the user's effective tier from their active subscriptions."""
    if active_subs is None:
        active_subs = [s for s in (user.subscriptions or []) if s.status == "active"]
    for sub in active_subs:
        if sub.tier == Tier.PRO.value:
            return Tier.PRO
    for sub in active_subs:
        if sub.tier == Tier.PREMIUM.value:
            return Tier.PREMIUM
    return Tier.FREE


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _consume_daily(user_id: str, kind: str) -> int:
    """Atomically increment + return the post-increment count for today."""
    day = _today_utc()
    key = (str(user_id), f"{kind}:{day}")
    with _DAILY_LOCK:
        _DAILY_HOROSCOPE[key] += 1
        return _DAILY_HOROSCOPE[key]


def reset_daily_counters() -> None:
    """Test helper. Wipes the in-memory daily counters."""
    with _DAILY_LOCK:
        _DAILY_HOROSCOPE.clear()


def _raise_402(detail: str, cta: str = "upgrade") -> None:
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"error": detail, "cta": cta, "tier_required": "premium"},
    )


def assert_quota(user: User, kind: QuotaKind) -> None:
    """Raise 402 if the user has exhausted their free-tier allowance.

    Premium and Pro tiers never hit a quota wall. Free tier rules:
    - NATAL_CHART: once per account (free_natal_used flag).
    - DREAM_ANALYSIS: once per account (free_dream_used flag).
    - HOROSCOPE: 1 per UTC day (in-memory or Redis counter).
    - EVENT_FORECAST: 1 per UTC day.
    - LUNAR_LOOKUP: unrestricted on every tier (free advertising surface).
    """
    tier = current_tier(user)
    if tier in (Tier.PREMIUM, Tier.PRO):
        return  # No limits.

    if kind is QuotaKind.LUNAR_LOOKUP:
        return  # Always free.

    if kind is QuotaKind.NATAL_CHART:
        if user.free_natal_used:
            _raise_402(
                "Free tier includes one natal chart. Upgrade to Premium for unlimited."
            )
        return

    if kind is QuotaKind.DREAM_ANALYSIS:
        if user.free_dream_used:
            _raise_402(
                "Free tier includes one dream analysis. Upgrade to Premium for unlimited."
            )
        return

    if kind is QuotaKind.HOROSCOPE:
        count = _consume_daily(user.id, "horoscope")
        if count > FREE_DAILY_HOROSCOPE_LIMIT:
            _raise_402(
                "Free tier allows one horoscope per day. Upgrade for unlimited."
            )
        return

    if kind is QuotaKind.EVENT_FORECAST:
        count = _consume_daily(user.id, "event_forecast")
        if count > FREE_DAILY_EVENT_FORECAST_LIMIT:
            _raise_402(
                "Free tier allows one event forecast per day. Upgrade for unlimited."
            )
        return


def mark_used(user: User, kind: QuotaKind) -> None:
    """Mark lifetime-flag quotas as consumed. Caller must commit the session.

    Used after a successful natal chart / dream analysis call on free tier.
    Daily quotas are auto-consumed inside `assert_quota`.
    """
    tier = current_tier(user)
    if tier in (Tier.PREMIUM, Tier.PRO):
        return
    if kind is QuotaKind.NATAL_CHART and not user.free_natal_used:
        user.free_natal_used = True
    elif kind is QuotaKind.DREAM_ANALYSIS and not user.free_dream_used:
        user.free_dream_used = True
