"""The gate on chart_core issuance: entitlement seam + MCP transport wiring.

Covers the security-critical logic — "one chart forever, keyed", tiers, the
structured refusal, and the MCP gate's branches — with User-shaped stubs and
injected fakes, the same DB-free discipline as `test_quotas.py`. The three
HTTP/MCP doors are thin callers of this seam; what could be wrong lives here.
"""

from __future__ import annotations

import asyncio
from datetime import date, time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.services.astrology.chart_core import build_chart_core, chart_identity
from backend.services.billing.entitlements import (
    AccountRequired,
    EntitlementRequired,
    check_chart_entitlement,
    mark_chart_issued,
)

REF = dict(birth_date=date(1977, 7, 1), birth_time=time(22, 30),
           lat=47.8388, lon=35.1396, place_label="Запорожье")


def _user(*, free_natal=False, key=None, subs=()):
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        free_natal_used=free_natal,
        free_natal_chart_key=key,
        subscriptions=list(subs),
    )


def _sub(tier="premium", status="active"):
    return SimpleNamespace(tier=tier, status=status)


# ── chart identity ──────────────────────────────────────────────────────────

def test_chart_identity_is_birth_instant_and_place():
    core = build_chart_core(**REF).core
    b = core["birth"]
    assert chart_identity(core) == f"{b['utc']}|{b['lat']}|{b['lon']}"


def test_chart_identity_is_stable_across_house_system_and_locale():
    # House system and locale are views, not the chart — same identity.
    a = build_chart_core(**REF, house_system="placidus").core
    b = build_chart_core(**REF, house_system="whole_sign").core
    assert chart_identity(a) == chart_identity(b)


def test_chart_identity_differs_when_the_birth_moment_differs():
    with_time = build_chart_core(**REF).core
    without = build_chart_core(**{**REF, "birth_time": None}).core
    # Noon-assumed vs real time is a different chart, different grant.
    assert chart_identity(with_time) != chart_identity(without)


# ── the seam: one chart forever, keyed ──────────────────────────────────────

def test_first_chart_is_free_then_marked():
    u = _user(free_natal=False)
    check_chart_entitlement(u, "KEY-A")  # allowed
    assert mark_chart_issued(u, "KEY-A") is True
    assert u.free_natal_used is True
    assert u.free_natal_chart_key == "KEY-A"


def test_refetching_your_own_chart_is_always_free():
    u = _user(free_natal=True, key="KEY-A")
    # No exception, any number of times — the account owns this chart.
    for _ in range(5):
        check_chart_entitlement(u, "KEY-A")
    # And re-issuing it does not consume a second grant.
    assert mark_chart_issued(u, "KEY-A") is False
    assert u.free_natal_chart_key == "KEY-A"


def test_a_different_second_chart_is_refused():
    u = _user(free_natal=True, key="KEY-A")
    with pytest.raises(EntitlementRequired) as exc:
        check_chart_entitlement(u, "KEY-B")
    assert exc.value.status_code == 402


def test_refusal_is_structured_and_not_sales_copy():
    u = _user(free_natal=True, key="KEY-A")
    with pytest.raises(EntitlementRequired) as exc:
        check_chart_entitlement(u, "KEY-B")
    d = exc.value.detail
    assert d["error"] == "entitlement_required"
    assert d["reason"] == "free_natal_chart_used"
    assert d["allowance"] == {"kind": "natal_chart", "free": 1, "period": "lifetime"}
    assert d["reset_at"] is None  # lifetime — does not reset
    assert d["tier_required"] == "premium"
    assert d["account_url"]
    # Factual, not promotional: no imperative sell.
    assert "upgrade now" not in d["message"].lower()
    assert "!" not in d["message"]


@pytest.mark.parametrize("tier", ["premium", "pro"])
def test_paid_tiers_are_never_gated(tier):
    u = _user(free_natal=True, key="KEY-A", subs=[_sub(tier)])
    for k in ("KEY-A", "KEY-B", "KEY-C"):
        check_chart_entitlement(u, k)  # no exception on any chart
    # And marking is a no-op for paid tiers (no free flag to spend).
    assert mark_chart_issued(u, "KEY-D") is False


def test_mark_is_idempotent_and_keeps_the_first_chart():
    u = _user(free_natal=False)
    assert mark_chart_issued(u, "KEY-A") is True
    # A second, different chart must not silently overwrite the grant.
    assert mark_chart_issued(u, "KEY-B") is False
    assert u.free_natal_chart_key == "KEY-A"


def test_account_required_is_a_structured_401():
    exc = AccountRequired("Sign in to get your free natal chart.")
    assert exc.status_code == 401
    assert exc.detail["error"] == "account_required"
    assert exc.detail["account_url"]
    assert exc.headers.get("WWW-Authenticate") == "Bearer"


# ── MCP transport gate ──────────────────────────────────────────────────────

class _FakeDB:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


def _fake_factory(db):
    class _CM:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *a):
            return False

    return lambda: _CM()


def _wire_mcp(monkeypatch, *, subject, user, db, on_http=True):
    """Point the MCP gate at a stub principal, user and session."""
    from backend.mcp.tools import astrology as A
    import backend.core.database as dbmod

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (on_http, subject))

    async def _resolve(_db, _subject):
        return user

    monkeypatch.setattr(A, "resolve_connector_user", _resolve)
    monkeypatch.setattr(dbmod, "get_sessionmaker", lambda: _fake_factory(db))
    return A


def test_mcp_gate_meters_and_commits_first_chart(monkeypatch):
    u = _user(free_natal=False)
    db = _FakeDB()
    A = _wire_mcp(monkeypatch, subject="sub-1", user=u, db=db)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    assert refusal is None
    assert stamp["gated"] is True and stamp["tier"] == "free"
    assert u.free_natal_used is True and u.free_natal_chart_key == "KEY-A"
    assert db.committed is True


def test_mcp_gate_refuses_a_second_chart_without_committing(monkeypatch):
    u = _user(free_natal=True, key="KEY-A")
    db = _FakeDB()
    A = _wire_mcp(monkeypatch, subject="sub-1", user=u, db=db)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-B"))
    assert refusal is not None and refusal["error"] == "entitlement_required"
    assert stamp == {"gated": True}
    assert db.committed is False


def test_mcp_gate_refetch_own_chart_is_free_and_no_commit(monkeypatch):
    u = _user(free_natal=True, key="KEY-A")
    db = _FakeDB()
    A = _wire_mcp(monkeypatch, subject="sub-1", user=u, db=db)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    assert refusal is None and stamp["gated"] is True
    assert db.committed is False  # already owned — nothing new to persist


def test_mcp_gate_off_transport_is_ungated(monkeypatch):
    # stdio client or a direct in-process call: no principal exists to meter,
    # regardless of MCP_REQUIRE_AUTH (which governs the HTTP transport).
    from backend.mcp.tools import astrology as A
    from backend.core import config

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (False, None))
    monkeypatch.setattr(config.settings, "MCP_REQUIRE_AUTH", True)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    assert refusal is None
    assert stamp["gated"] is False
    assert "no account" in stamp["reason"].lower()


def test_mcp_gate_open_http_connector_says_ungated(monkeypatch):
    from backend.mcp.tools import astrology as A
    from backend.core import config

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (True, None))
    monkeypatch.setattr(config.settings, "MCP_REQUIRE_AUTH", False)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    assert refusal is None
    assert stamp["gated"] is False
    assert "open" in stamp["reason"].lower()


def test_mcp_gate_on_transport_no_subject_under_auth_fails_closed(monkeypatch):
    from backend.mcp.tools import astrology as A
    from backend.core import config

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (True, None))
    monkeypatch.setattr(config.settings, "MCP_REQUIRE_AUTH", True)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    # A valid token was required to reach the tool; a missing subject is a
    # broken handoff, not an anonymous user. Refuse, never issue ungated.
    assert refusal is not None
    assert refusal["error"] == "entitlement_unverifiable"
    assert stamp == {"gated": True}


def test_mcp_gate_store_unavailable_under_auth_fails_closed(monkeypatch):
    from backend.mcp.tools import astrology as A
    from backend.core import config
    import backend.core.database as dbmod

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (True, "sub-1"))
    monkeypatch.setattr(config.settings, "MCP_REQUIRE_AUTH", True)

    def _boom():
        raise RuntimeError("DATABASE_URL is not configured")

    monkeypatch.setattr(dbmod, "get_sessionmaker", _boom)
    refusal, stamp = asyncio.run(A._gate_chart_issuance("KEY-A"))
    # Cannot check the account → refuse, don't hand out an unmetered chart.
    assert refusal is not None and refusal["error"] == "entitlement_unverifiable"
    assert stamp == {"gated": True}
