"""Quota service tests (Phase 6.B)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.services.billing.quotas import (
    QuotaKind,
    Tier,
    assert_quota,
    current_tier,
    mark_used,
    reset_daily_counters,
)


def _user(*, free_natal=False, free_dream=False, subs=()):
    """Build a minimal User-shaped stub (we only access a few attributes)."""
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        free_natal_used=free_natal,
        free_dream_used=free_dream,
        subscriptions=list(subs),
    )


def _sub(tier="premium", status="active"):
    return SimpleNamespace(tier=tier, status=status)


@pytest.fixture(autouse=True)
def _reset_counters():
    reset_daily_counters()
    yield
    reset_daily_counters()


def test_current_tier_free_when_no_subs():
    assert current_tier(_user()) == Tier.FREE


def test_current_tier_premium():
    u = _user(subs=[_sub("premium")])
    assert current_tier(u) == Tier.PREMIUM


def test_current_tier_pro_dominates_premium():
    u = _user(subs=[_sub("premium"), _sub("pro")])
    assert current_tier(u) == Tier.PRO


def test_current_tier_ignores_inactive_subs():
    u = _user(subs=[_sub("premium", status="canceled")])
    assert current_tier(u) == Tier.FREE


def test_free_natal_chart_once():
    u = _user(free_natal=False)
    assert_quota(u, QuotaKind.NATAL_CHART)  # ok
    mark_used(u, QuotaKind.NATAL_CHART)
    assert u.free_natal_used is True
    with pytest.raises(HTTPException) as exc:
        assert_quota(u, QuotaKind.NATAL_CHART)
    assert exc.value.status_code == 402


def test_free_dream_analysis_once():
    u = _user(free_dream=False)
    assert_quota(u, QuotaKind.DREAM_ANALYSIS)
    mark_used(u, QuotaKind.DREAM_ANALYSIS)
    with pytest.raises(HTTPException) as exc:
        assert_quota(u, QuotaKind.DREAM_ANALYSIS)
    assert exc.value.status_code == 402


def test_free_horoscope_one_per_day():
    u = _user()
    assert_quota(u, QuotaKind.HOROSCOPE)  # first call: counter=1, allowed
    with pytest.raises(HTTPException) as exc:
        assert_quota(u, QuotaKind.HOROSCOPE)  # second: counter=2, blocked
    assert exc.value.status_code == 402


def test_free_event_forecast_one_per_day():
    u = _user()
    assert_quota(u, QuotaKind.EVENT_FORECAST)
    with pytest.raises(HTTPException) as exc:
        assert_quota(u, QuotaKind.EVENT_FORECAST)
    assert exc.value.status_code == 402


def test_lunar_lookup_never_blocked():
    u = _user()
    for _ in range(50):
        assert_quota(u, QuotaKind.LUNAR_LOOKUP)


def test_premium_user_unlimited():
    u = _user(free_natal=True, free_dream=True, subs=[_sub("premium")])
    # No matter what, no exceptions.
    for kind in QuotaKind:
        for _ in range(5):
            assert_quota(u, kind)


def test_pro_user_unlimited():
    u = _user(free_natal=True, subs=[_sub("pro")])
    for kind in QuotaKind:
        for _ in range(3):
            assert_quota(u, kind)


def test_mark_used_idempotent_on_premium():
    u = _user(subs=[_sub("premium")])
    mark_used(u, QuotaKind.NATAL_CHART)
    # Premium users don't get the free flag toggled (it's irrelevant).
    assert u.free_natal_used is False


def test_402_payload_has_cta():
    u = _user()
    mark_used(u, QuotaKind.NATAL_CHART)  # premium-no-op then free user
    # Trigger from free user:
    u2 = _user(free_natal=True)
    with pytest.raises(HTTPException) as exc:
        assert_quota(u2, QuotaKind.NATAL_CHART)
    assert exc.value.detail["tier_required"] == "premium"
