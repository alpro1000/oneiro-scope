"""Tests for the account page.

The database layer is faked rather than exercised: the models use the
PostgreSQL `UUID` column type, so they do not create on SQLite, and the repo
has no Postgres fixture. What is under test here is the portal's own
behaviour — session cookie handling, delegation to the API handlers, and what
each failure mode renders — so the API calls are stubbed and asserted on.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("jinja2", reason="jinja2 not installed")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.portal import account as acc  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(acc.router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_real_database(monkeypatch):
    """A session object that is never actually used by the stubbed handlers."""

    @asynccontextmanager
    async def _fake_session():
        yield SimpleNamespace(name="fake-db")

    monkeypatch.setattr(acc, "_session", _fake_session)


def _user(**kw):
    return SimpleNamespace(
        email=kw.get("email", "someone@example.com"),
        name=kw.get("name"),
        llm_keys=kw.get("llm_keys", []),
    )


def _signed_in(monkeypatch, user=None):
    async def _resolve(request, db):
        return user if user is not None else _user()

    monkeypatch.setattr(acc, "_user_from_cookie", _resolve)


# --- signed out ---------------------------------------------------------------

def test_no_cookie_shows_the_sign_in_form(client):
    resp = client.get("/account")
    assert resp.status_code == 200
    assert 'action="/account/signin"' in resp.text
    assert "{{" not in resp.text


def test_sign_in_page_does_not_touch_the_database(client, monkeypatch):
    """A deployment with no DB configured must still render this page."""

    @asynccontextmanager
    async def _explode():
        raise AssertionError("signed-out page opened a database session")
        yield  # pragma: no cover

    monkeypatch.setattr(acc, "_session", _explode)
    assert client.get("/account").status_code == 200


def test_stale_cookie_clears_itself_and_shows_sign_in(client, monkeypatch):
    async def _no_user(request, db):
        return None

    monkeypatch.setattr(acc, "_user_from_cookie", _no_user)
    resp = client.get(
        "/account", cookies={acc.SESSION_COOKIE: "expired"},
    )
    assert resp.status_code == 200
    assert 'action="/account/signin"' in resp.text
    # The browser is told to drop it, so the next visit isn't a round trip.
    assert acc.SESSION_COOKIE in resp.headers.get("set-cookie", "")


# --- signing in ---------------------------------------------------------------

def _stub_login(monkeypatch, token="jwt-token", raises=None):
    calls = {}

    async def _login(req, db):
        calls["email"] = req.email
        calls["password"] = req.password
        if raises:
            raise raises
        return SimpleNamespace(access_token=token)

    async def _register(req, db):
        calls["registered"] = req.email
        calls["language"] = req.language
        if raises:
            raise raises
        return SimpleNamespace(access_token=token)

    import backend.api.v1.auth as auth_api

    monkeypatch.setattr(auth_api, "login", _login)
    monkeypatch.setattr(auth_api, "register", _register)
    return calls


def test_successful_sign_in_sets_an_httponly_session_cookie(client, monkeypatch):
    calls = _stub_login(monkeypatch, token="the-jwt")
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "hunter2000"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/account"
    assert calls["email"] == "a@b.com"

    cookie = resp.headers["set-cookie"]
    assert "the-jwt" in cookie
    assert "HttpOnly" in cookie
    # SameSite=Lax is what stands in for a CSRF token on these forms.
    assert "SameSite=lax" in cookie or "samesite=lax" in cookie.lower()


def test_session_cookie_is_secure_outside_development(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
    _stub_login(monkeypatch)
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "hunter2000"},
        follow_redirects=False,
    )
    assert "Secure" in resp.headers["set-cookie"]


def test_bad_credentials_render_the_form_again_without_a_cookie(
    client, monkeypatch
):
    _stub_login(monkeypatch, raises=HTTPException(status_code=401))
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "wrong-one"},
        follow_redirects=False,
    )
    assert resp.status_code == 401
    assert "set-cookie" not in resp.headers
    assert 'action="/account/signin"' in resp.text


def test_duplicate_email_says_sign_in_instead(client, monkeypatch):
    _stub_login(monkeypatch, raises=HTTPException(status_code=409))
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "hunter2000",
              "action": "register"},
    )
    assert resp.status_code == 409
    assert acc.TEXT["en"]["err_exists"] in resp.text or \
        acc.TEXT["ru"]["err_exists"] in resp.text


def test_short_password_is_refused_before_reaching_the_api(client, monkeypatch):
    calls = _stub_login(monkeypatch)
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "short", "action": "register"},
    )
    assert resp.status_code == 400
    assert "registered" not in calls


def test_registration_carries_the_page_language(client, monkeypatch):
    calls = _stub_login(monkeypatch)
    client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "hunter2000",
              "action": "register"},
        headers={"accept-language": "ru"},
        follow_redirects=False,
    )
    assert calls["language"] == "ru"


def test_database_outage_is_a_503_that_says_the_connector_still_works(
    client, monkeypatch
):
    @asynccontextmanager
    async def _broken():
        raise RuntimeError("no database")
        yield  # pragma: no cover

    monkeypatch.setattr(acc, "_session", _broken)
    resp = client.post(
        "/account/signin",
        data={"email": "a@b.com", "password": "hunter2000"},
    )
    assert resp.status_code == 503
    assert "connector" in resp.text.lower() or "коннектор" in resp.text


# --- dashboard ----------------------------------------------------------------

def _stub_subscription(monkeypatch, **fields):
    payload = {"tier": "free", "status": None, "current_period_end": None,
               "cancel_at_period_end": False, **fields}

    async def _sub(user, db):
        return SimpleNamespace(model_dump=lambda: payload)

    import backend.api.v1.billing as billing_api

    monkeypatch.setattr(billing_api, "my_subscription", _sub)


def test_dashboard_shows_plan_keys_and_connector_url(client, monkeypatch):
    _signed_in(monkeypatch, _user(
        email="me@example.com",
        llm_keys=[SimpleNamespace(provider="groq", hint="gsk…9f2")],
    ))
    _stub_subscription(monkeypatch, tier="premium", status="active")
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://api.example.com/mcp", raising=False
    )

    resp = client.get("/account", cookies={acc.SESSION_COOKIE: "valid"})
    assert resp.status_code == 200
    assert "me@example.com" in resp.text
    assert "PREMIUM" in resp.text
    assert "groq" in resp.text
    assert "https://api.example.com/mcp" in resp.text
    assert "{{" not in resp.text


def test_dashboard_survives_a_billing_outage(client, monkeypatch):
    """A broken subscription lookup must not take the whole page down."""
    _signed_in(monkeypatch)

    async def _boom(user, db):
        raise RuntimeError("lemon is down")

    import backend.api.v1.billing as billing_api

    monkeypatch.setattr(billing_api, "my_subscription", _boom)
    resp = client.get("/account", cookies={acc.SESSION_COOKIE: "valid"})
    assert resp.status_code == 200
    assert "FREE" in resp.text


def test_dashboard_never_prints_the_session_token(client, monkeypatch):
    _signed_in(monkeypatch)
    _stub_subscription(monkeypatch)
    token = "super-secret-jwt-value"
    resp = client.get("/account", cookies={acc.SESSION_COOKIE: token})
    assert token not in resp.text


def test_account_page_carries_the_disclaimer(client, monkeypatch):
    _signed_in(monkeypatch)
    _stub_subscription(monkeypatch)
    resp = client.get(
        "/account", cookies={acc.SESSION_COOKIE: "valid"},
        headers={"accept-language": "ru"},
    )
    assert "рефлексивно-развлекательный" in resp.text


# --- data export and deletion -------------------------------------------------

def test_export_returns_a_json_download(client, monkeypatch):
    _signed_in(monkeypatch)

    async def _export(user, db):
        return {"user": {"email": "me@example.com"}, "dream_count": 3}

    import backend.api.v1.users as users_api

    monkeypatch.setattr(users_api, "gdpr_export", _export)
    resp = client.get("/account/export", cookies={acc.SESSION_COOKIE: "valid"})
    assert resp.status_code == 200
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.json()["dream_count"] == 3


def test_export_without_a_session_redirects(client, monkeypatch):
    async def _none(request, db):
        return None

    monkeypatch.setattr(acc, "_user_from_cookie", _none)
    resp = client.get(
        "/account/export", cookies={acc.SESSION_COOKIE: "stale"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_deletion_requires_the_confirmation_tick(client, monkeypatch):
    _signed_in(monkeypatch)
    called = {"n": 0}

    async def _delete(user, db):
        called["n"] += 1
        return {"status": "deleted", "erased": []}

    import backend.api.v1.users as users_api

    monkeypatch.setattr(users_api, "delete_account", _delete)

    unticked = client.post(
        "/account/delete", data={}, cookies={acc.SESSION_COOKIE: "valid"}
    )
    assert unticked.status_code == 400
    assert called["n"] == 0, "erasure is irreversible — it must not run unticked"


def test_confirmed_deletion_erases_and_signs_out(client, monkeypatch):
    """Confirmation runs the erasure and ends the session.

    The handler used to call `request_account_deletion`, which only set a
    `pending_deletion_at` flag no code ever read; the page then quoted a purge
    date that would never arrive. It now calls the erasing `delete_account`,
    so there is no date to show and none is asserted.
    """
    _signed_in(monkeypatch)
    called = {"n": 0}

    async def _delete(user, db):
        called["n"] += 1
        return {"status": "deleted", "erased": ["account"]}

    import backend.api.v1.users as users_api

    monkeypatch.setattr(users_api, "delete_account", _delete)

    resp = client.post(
        "/account/delete", data={"confirm": "yes"},
        cookies={acc.SESSION_COOKIE: "valid"},
    )
    assert resp.status_code == 200
    assert called["n"] == 1
    # No purge date is promised any more — the erasure already happened.
    assert "purge" not in resp.text.lower()
    # Session cookie is dropped along with the account.
    assert 'oneiro_session=""' in resp.headers.get("set-cookie", "") or \
        "Max-Age=0" in resp.headers.get("set-cookie", "")


def test_signout_clears_the_cookie(client):
    resp = client.post("/account/signout", follow_redirects=False)
    assert resp.status_code == 303
    assert acc.SESSION_COOKIE in resp.headers["set-cookie"]
