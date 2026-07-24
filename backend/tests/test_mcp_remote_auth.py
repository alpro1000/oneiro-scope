"""Tests for the remote-MCP connector surface (auth + discovery metadata).

Exercises the OAuth 2.1 resource-server behaviour without needing the `mcp`
package or a live authorization server: the ASGI middleware is driven directly
and JWKS fetching is stubbed.
"""

from __future__ import annotations

import json

import pytest

from backend.core.config import settings
from backend.mcp import remote


@pytest.fixture(autouse=True)
def _reset_mcp_settings(monkeypatch):
    """Every test starts from an auth-required, production-like baseline."""
    monkeypatch.setattr(settings, "MCP_PATH", "/mcp", raising=False)
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://api.example.com/mcp", raising=False
    )
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", None, raising=False)
    monkeypatch.setattr(settings, "MCP_AUTH_JWKS_URL", None, raising=False)
    monkeypatch.setattr(settings, "MCP_AUTH_AUDIENCE", None, raising=False)
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "", raising=False)
    monkeypatch.setattr(settings, "MCP_DEV_TOKEN", None, raising=False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development", raising=False)
    remote._JWKS_CACHE.clear()


# --- discovery metadata -------------------------------------------------------

def test_resource_url_and_audience_default_to_public_url():
    assert remote.resource_url() == "https://api.example.com/mcp"
    assert remote.audience() == "https://api.example.com/mcp"


def test_jwks_url_derived_from_issuer(monkeypatch):
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com/")
    assert remote.jwks_url() == "https://idp.example.com/.well-known/jwks.json"
    assert remote.auth_configured() is True


def test_protected_resource_metadata_shape(monkeypatch):
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com/")
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "mcp:read mcp:write")
    meta = remote.protected_resource_metadata()
    assert meta["resource"] == "https://api.example.com/mcp"
    assert meta["authorization_servers"] == ["https://idp.example.com"]
    assert meta["scopes_supported"] == ["mcp:read", "mcp:write"]
    assert meta["bearer_methods_supported"] == ["header"]


def test_www_authenticate_points_at_metadata():
    header = remote.www_authenticate_header()
    assert 'resource_metadata="https://api.example.com' in header
    assert remote.PROTECTED_RESOURCE_PATH in header
    assert header.startswith("Bearer ")


# --- dev token ----------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_token_accepted_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "MCP_DEV_TOKEN", "local-secret")
    claims = await remote.verify_bearer("local-secret")
    assert claims["sub"] == "dev"


@pytest.mark.asyncio
async def test_dev_token_refused_in_production(monkeypatch):
    monkeypatch.setattr(settings, "MCP_DEV_TOKEN", "local-secret")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(remote.AuthError) as err:
        await remote.verify_bearer("local-secret")
    assert err.value.status == 401
    assert "production" in str(err.value)


@pytest.mark.asyncio
async def test_no_authorization_server_configured_is_rejected():
    with pytest.raises(remote.AuthError) as err:
        await remote.verify_bearer("some-token")
    assert "authorization server" in str(err.value)


# --- JWT verification (stubbed JWKS) ------------------------------------------

def _stub_jwks(monkeypatch, keys):
    async def _fake_fetch(url):
        return keys

    monkeypatch.setattr(remote, "_fetch_jwks", _fake_fetch)


@pytest.mark.asyncio
async def test_unknown_kid_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    _stub_jwks(monkeypatch, [{"kid": "known"}])

    from jose import jwt as jose_jwt

    token = jose_jwt.encode(
        {"sub": "u1", "aud": remote.audience()},
        "secret",
        algorithm="HS256",
        headers={"kid": "missing"},
    )
    with pytest.raises(remote.AuthError) as err:
        await remote.verify_bearer(token)
    assert "signing key" in str(err.value)


@pytest.mark.asyncio
async def test_valid_token_with_required_scope(monkeypatch):
    """A symmetric key stands in for JWKS — the code path is key-agnostic."""
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "mcp:read")
    key = {"kid": "k1", "kty": "oct", "k": "c2VjcmV0LWtleS12YWx1ZQ"}
    _stub_jwks(monkeypatch, [key])

    from jose import jwt as jose_jwt

    token = jose_jwt.encode(
        {
            "sub": "u1",
            "aud": remote.audience(),
            "iss": "https://idp.example.com",
            "scope": "mcp:read mcp:write",
        },
        key,
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    claims = await remote.verify_bearer(token)
    assert claims["sub"] == "u1"


@pytest.mark.asyncio
async def test_missing_scope_is_403(monkeypatch):
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "mcp:admin")
    key = {"kid": "k1", "kty": "oct", "k": "c2VjcmV0LWtleS12YWx1ZQ"}
    _stub_jwks(monkeypatch, [key])

    from jose import jwt as jose_jwt

    token = jose_jwt.encode(
        {
            "sub": "u1",
            "aud": remote.audience(),
            "iss": "https://idp.example.com",
            "scope": "mcp:read",
        },
        key,
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    with pytest.raises(remote.AuthError) as err:
        await remote.verify_bearer(token)
    assert err.value.status == 403
    assert err.value.code == "insufficient_scope"


# --- ASGI middleware ----------------------------------------------------------

class _Recorder:
    """Collects the ASGI messages a middleware sends."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int | None:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return None

    @property
    def headers(self) -> dict[str, str]:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return {
                    k.decode().lower(): v.decode() for k, v in m["headers"]
                }
        return {}

    @property
    def json_body(self) -> dict:
        for m in self.messages:
            if m["type"] == "http.response.body":
                return json.loads(m["body"])
        return {}


async def _noop_receive() -> dict:  # pragma: no cover - never awaited on reject
    return {"type": "http.request"}


def _scope(method: str = "POST", headers: list | None = None) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": "/mcp",
        "headers": headers or [],
    }


@pytest.mark.asyncio
async def test_middleware_rejects_missing_token():
    downstream_called = False

    async def downstream(scope, receive, send):  # pragma: no cover
        nonlocal downstream_called
        downstream_called = True

    mw = remote.BearerAuthMiddleware(downstream)
    rec = _Recorder()
    await mw(_scope(), _noop_receive, rec)

    assert rec.status == 401
    assert "www-authenticate" in rec.headers
    assert rec.json_body["error"] == "invalid_request"
    assert downstream_called is False


@pytest.mark.asyncio
async def test_middleware_passes_valid_token_and_sets_subject(monkeypatch):
    monkeypatch.setattr(settings, "MCP_DEV_TOKEN", "local-secret")
    seen: dict = {}

    async def downstream(scope, receive, send):
        seen.update(scope.get("state", {}))

    mw = remote.BearerAuthMiddleware(downstream)
    rec = _Recorder()
    await mw(
        _scope(headers=[(b"authorization", b"Bearer local-secret")]),
        _noop_receive,
        rec,
    )

    assert rec.status is None, "valid request must not be answered by the guard"
    assert seen["mcp_subject"] == "dev"


@pytest.mark.asyncio
async def test_middleware_lets_preflight_through():
    reached = False

    async def downstream(scope, receive, send):
        nonlocal reached
        reached = True

    mw = remote.BearerAuthMiddleware(downstream)
    await mw(_scope(method="OPTIONS"), _noop_receive, _Recorder())
    assert reached is True


@pytest.mark.asyncio
async def test_middleware_open_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", False)
    reached = False

    async def downstream(scope, receive, send):
        nonlocal reached
        reached = True

    mw = remote.BearerAuthMiddleware(downstream)
    await mw(_scope(), _noop_receive, _Recorder())
    assert reached is True
