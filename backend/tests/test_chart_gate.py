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


# ── "the same chart" is a place tolerance, not string equality ──────────────
#
# The key is `utc|lat|lon`. The same birth in the same city resolves to
# slightly different coordinates depending on how the place was supplied, so
# exact matching billed a re-fetch as a second chart. Observed live on
# Запорожье: 47.8388/35.1396 typed vs 47.85167/35.11714 geocoded, 1.4 km apart.

from backend.services.billing.entitlements import same_chart  # noqa: E402

_UTC = "1977-07-01T19:30:00Z"


def test_same_chart_accepts_the_geocoder_vs_typed_coordinate_gap():
    typed = f"{_UTC}|47.8388|35.1396"
    geocoded = f"{_UTC}|47.85167|35.11714"
    assert same_chart(typed, geocoded)
    assert same_chart(geocoded, typed)  # symmetric


def test_same_chart_still_requires_the_identical_birth_instant():
    """A different moment is a different chart, however close the place."""
    assert not same_chart(
        f"{_UTC}|47.8388|35.1396", f"1977-07-01T19:31:00Z|47.8388|35.1396"
    )


def test_same_chart_rejects_a_genuinely_different_place():
    # Kyiv is ~2.5° north of Zaporizhzhia — far outside the tolerance.
    assert not same_chart(f"{_UTC}|47.8388|35.1396", f"{_UTC}|50.4501|30.5234")


def test_same_chart_handles_the_antimeridian():
    """±180 is one seam, not a 360° gap — a wrap-unaware diff would refuse."""
    assert same_chart(f"{_UTC}|-16.5|-179.97", f"{_UTC}|-16.5|179.97")


def test_same_chart_on_missing_or_unparseable_key():
    assert not same_chart(None, f"{_UTC}|47.8|35.1")
    assert not same_chart("", f"{_UTC}|47.8|35.1")
    # A legacy/odd stored key that is not utc|lat|lon: exact match only.
    assert same_chart("LEGACY-KEY", "LEGACY-KEY")
    assert not same_chart("LEGACY-KEY", f"{_UTC}|47.8|35.1")


def test_refusal_message_follows_the_locale():
    from backend.services.billing.entitlements import (
        EntitlementRequired,
        check_chart_entitlement,
    )

    user = _user(free_natal=True, key="KEY-A")
    for locale, needle in (("ru", "Бесплатная"), ("en", "already been issued")):
        try:
            check_chart_entitlement(user, "KEY-B", locale=locale)
        except EntitlementRequired as exc:
            assert needle in exc.detail["message"], (locale, exc.detail["message"])
        else:  # pragma: no cover - the gate must refuse here
            raise AssertionError("expected a refusal")


# ── legacy grant: the flag without the key ───────────────────────────────────
# `free_natal_used` predates `free_natal_chart_key` (the column arrived with
# migration 0002 as NULL). Every account that burned its grant under the old
# `quotas.mark_used` therefore holds a grant that matches NOTHING — and the
# owner hit the consequence live: their own 1977-07-01 Запорожье answered
# `entitlement_required` on every spelling of the city.


def test_legacy_flag_without_key_does_not_wall_off_every_chart():
    user = _user(free_natal=True, key=None)
    own = chart_identity(build_chart_core(**REF).core)
    check_chart_entitlement(user, own)  # must not raise


def test_legacy_grant_is_adopted_once_and_then_keyed_normally():
    """The grace is one issuance: the next chart becomes THE granted chart,
    after which the account behaves exactly like a normally-keyed one —
    its own chart free forever, any other refused."""
    user = _user(free_natal=True, key=None)
    own = chart_identity(build_chart_core(**REF).core)

    check_chart_entitlement(user, own)
    assert mark_chart_issued(user, own) is True  # adoption writes the key
    assert user.free_natal_chart_key == own

    other = chart_identity(
        build_chart_core(**{**REF, "birth_time": time(6, 0)}).core
    )
    with pytest.raises(EntitlementRequired):
        check_chart_entitlement(user, other)

    check_chart_entitlement(user, own)  # own chart: free, forever
    assert mark_chart_issued(user, own) is False  # nothing left to write


def test_a_readable_grant_is_never_overwritten_by_adoption():
    """Adoption exists for the unkeyed legacy state ONLY. An account whose
    grant is already keyed keeps its FIRST chart."""
    user = _user(free_natal=True, key="2000-01-01T12:00:00+00:00|51.4779|-0.0015")
    assert mark_chart_issued(user, "1999-01-01T00:00:00+00:00|0.0|0.0") is False
    assert user.free_natal_chart_key == "2000-01-01T12:00:00+00:00|51.4779|-0.0015"


# ── the refusal is an MCP error, not a look-alike result ─────────────────────


def test_tool_level_refusal_raises_tool_error_with_the_structured_payload(monkeypatch):
    """Owner-reported: `entitlement_required` arrived with `isError: false`,
    so a generic client displayed the refusal as if it were a successful
    computation. The tool did not perform the operation — the result must say
    so. The structured refusal rides in the error message as JSON so the
    model can still read the limit and the account link."""
    import json as _json

    from mcp.server.fastmcp.exceptions import ToolError

    from backend.mcp.tools import astrology as A

    core = build_chart_core(**REF).core

    class _Resp:
        chart_core = core

        def model_dump(self, mode):  # pragma: no cover — refusal path returns first
            return {}

    class _Svc:
        async def calculate_natal_chart(self, req, interpret):
            return _Resp()

    refusal = {
        "error": "entitlement_required",
        "reason": "free_natal_chart_used",
        "allowance": {"kind": "natal_chart", "free": 1, "period": "lifetime"},
    }

    async def _gate(key, locale="ru"):
        return refusal, {"gated": True}

    monkeypatch.setattr(A, "_service", _Svc())
    monkeypatch.setattr(A, "_gate_chart_issuance", _gate)

    with pytest.raises(ToolError) as exc:
        asyncio.run(A.calculate_natal_chart(
            birth_date="1977-07-01", birth_place="Запорожье",
            birth_time="22:30", latitude=47.8388, longitude=35.1396,
        ))
    payload = _json.loads(str(exc.value))
    assert payload["reason"] == "free_natal_chart_used"
    assert payload["allowance"]["free"] == 1


def test_a_refusal_names_the_identity_it_refused(monkeypatch):
    """An operator who has just filled STAFF_ACCOUNTS cannot otherwise tell
    "the bypass is off" from "I named the wrong identity" — the symptom is
    the same refusal, and the only feedback loop is editing a dashboard and
    re-running a chart. Observed live: a transcribed Auth0 user_id lost two
    characters, which would have failed silently forever.

    The value is the caller's OWN subject, returned to the caller.
    """
    from backend.mcp.tools import astrology as A

    class _Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def commit(self): pass

    user = _user(free_natal=True, key="OTHER-CHART")

    monkeypatch.setattr(A, "mcp_auth_context", lambda: (True, "auth0|deadbeef"))
    monkeypatch.setattr(A, "resolve_connector_user", lambda db, subject: _async(user))
    monkeypatch.setattr(
        "backend.core.database.get_sessionmaker", lambda: (lambda: _Session())
    )

    refusal, stamp = asyncio.run(A._gate_chart_issuance("A-DIFFERENT-CHART"))
    assert stamp == {"gated": True}
    assert refusal["reason"] == "free_natal_chart_used"
    assert refusal["authenticated_as"] == "auth0|deadbeef"


async def _async(value):
    return value
