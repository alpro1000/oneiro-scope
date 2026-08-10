"""Staff bypass: the owner must be able to use the product they ship.

The free tier grants one natal chart for life, and it applied to the owner
exactly as it applies to a customer — so after the first chart every attempt
to exercise the paid path answered `entitlement_required`. A gate you cannot
get past is a gate you cannot test.

The bypass is deliberately narrow, and these tests are mostly about the ways
it must NOT widen: it is server configuration matched against an
authenticated identity, it is off unless a deployment names someone, and it
lives in `current_tier` so it cannot be added to one gate and forgotten at the
next.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.billing import quotas
from backend.services.billing.entitlements import (
    EntitlementRequired,
    check_chart_entitlement,
)
from backend.services.billing.quotas import Tier, current_tier, is_staff

OWNER = "alpro1000@gmail.com"


def account(**kw):
    """A user-shaped object. Quota code only needs it to quack."""
    base = dict(
        email=None, oauth_subject=None, subscriptions=[],
        free_natal_used=True, free_natal_chart_key="1990-05-15|14:30|55.7558|37.6173",
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def staff_configured(monkeypatch):
    monkeypatch.setattr(quotas, "staff_identities", lambda: frozenset({OWNER}))


# --- off by default -----------------------------------------------------------


def test_nothing_is_bypassed_when_no_staff_is_configured(monkeypatch):
    """The default must be that this feature does not exist."""
    monkeypatch.setattr(quotas, "staff_identities", frozenset)
    assert not is_staff(account(email=OWNER))
    assert current_tier(account(email=OWNER)) is Tier.FREE


def test_the_config_parser_ignores_blanks_and_case(monkeypatch):
    """Read from the live settings object — the function imports it lazily."""
    from backend.core import config

    monkeypatch.setattr(config.settings, "STAFF_ACCOUNTS", f" {OWNER.upper()} , , ")
    assert quotas.staff_identities() == frozenset({OWNER})

    monkeypatch.setattr(config.settings, "STAFF_ACCOUNTS", "")
    assert quotas.staff_identities() == frozenset()


# --- what it does -------------------------------------------------------------


def test_a_configured_owner_reaches_the_paid_tier(staff_configured):
    assert is_staff(account(email=OWNER))
    assert current_tier(account(email=OWNER)) is Tier.PRO


def test_the_owner_can_be_named_by_oauth_subject_too(staff_configured):
    """The MCP path authenticates by OAuth subject, not by email — a bypass
    that only understood email would work on the site and not in the chat."""
    monkeypatch_free = account(oauth_subject=OWNER)
    assert is_staff(monkeypatch_free)
    assert current_tier(monkeypatch_free) is Tier.PRO


def test_the_gate_that_blocked_the_owner_now_lets_them_through(staff_configured):
    """The exact reported failure: a second, different chart on a used free
    account."""
    someone_elses_chart = "1977-07-01|22:30|47.85167|35.11714"

    with pytest.raises(EntitlementRequired):
        check_chart_entitlement(account(email="customer@example.com"), someone_elses_chart)

    # Same account state, but named in STAFF_ACCOUNTS → no raise.
    check_chart_entitlement(account(email=OWNER), someone_elses_chart)


# --- and the ways it must not widen -------------------------------------------


def test_a_customer_is_still_gated(staff_configured):
    with pytest.raises(EntitlementRequired) as exc:
        check_chart_entitlement(account(email="customer@example.com"), "2000-01-01|12:00|0|0")
    assert exc.value.detail["reason"] == "free_natal_chart_used"


def test_a_lookalike_address_does_not_match(staff_configured):
    """Substring or domain matching would turn one name into a family of them."""
    for near in (
        "alpro1000@gmail.com.attacker.example",
        "notalpro1000@gmail.com",
        "alpro1000@gmail.co",
        "alpro1000",
    ):
        assert not is_staff(account(email=near)), near


def test_an_empty_identity_never_matches(staff_configured):
    """An account with no email and no subject must not fall into the list."""
    assert not is_staff(account())
    assert not is_staff(account(email="", oauth_subject=""))


def test_the_bypass_lives_in_one_place():
    """`current_tier` is the single seam every gate already consults.

    Asserted rather than assumed: the reason this is safe to have at all is
    that it cannot be present at one gate and absent at another.
    """
    import inspect

    from backend.services.billing import entitlements

    source = inspect.getsource(entitlements)
    assert "is_staff" not in source, (
        "the staff check leaked into a specific gate — it belongs in "
        "current_tier, so every gate inherits it"
    )
    assert "current_tier(" in source


def test_the_free_grant_is_not_consumed_by_staff(staff_configured):
    """`mark_chart_issued` is free-tier-only; staff read as PRO, so their
    testing must not burn a flag on their own account."""
    from backend.services.billing.entitlements import mark_chart_issued

    owner = account(email=OWNER, free_natal_used=False, free_natal_chart_key=None)
    assert mark_chart_issued(owner, "2000-01-01|12:00|0|0") is False
    assert owner.free_natal_used is False
