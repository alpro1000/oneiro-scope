"""Tests for the remote-MCP connector surface (auth + discovery metadata).

Exercises the OAuth 2.1 resource-server behaviour without needing the `mcp`
package or a live authorization server: the ASGI middleware is driven directly
and JWKS fetching is stubbed.
"""

from __future__ import annotations

import json
import time

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


def test_discovery_is_off_until_an_issuer_exists(monkeypatch):
    """Advertising OAuth without an authorization server breaks connectors.

    Clients that see the document but no `authorization_servers` fall back to
    treating this origin as the AS and try Dynamic Client Registration, which
    fails — the user gets "couldn't register with the sign-in service".
    """
    assert remote.oauth_discovery_enabled() is False
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    assert remote.oauth_discovery_enabled() is True


def test_discovery_is_off_when_auth_is_configured_but_not_enforced(monkeypatch):
    """Advertising protection that isn't enforced sends clients through a login
    flow for an endpoint that would have answered without one."""
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", False, raising=False)
    assert remote.oauth_discovery_enabled() is False


@pytest.fixture
def app_client():
    """Real app, so the wiring of the discovery route is what's tested.

    The app pulls in the full backend dependency set; where those are absent
    the test is skipped rather than failed — CI installs them and runs it.
    """
    pytest.importorskip("fastapi", reason="fastapi not installed")
    try:
        from fastapi.testclient import TestClient

        from backend.app.main import app
    except Exception as exc:  # optional heavy dep absent locally
        pytest.skip(f"backend.app.main not importable: {exc}")
    return TestClient(app)


def test_discovery_endpoint_404s_on_a_public_server(app_client, monkeypatch):
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", False, raising=False)
    resp = app_client.get(remote.PROTECTED_RESOURCE_PATH)
    assert resp.status_code == 404


def test_discovery_endpoint_serves_metadata_once_configured(
    app_client, monkeypatch
):
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com")
    resp = app_client.get(remote.PROTECTED_RESOURCE_PATH)
    assert resp.status_code == 200
    assert resp.json()["authorization_servers"] == ["https://idp.example.com"]


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


# --- transport wiring (mount path + DNS-rebinding allow-list) -----------------

@pytest.mark.asyncio
async def test_dispatcher_sends_mcp_paths_to_the_transport():
    """`/mcp` and `/mcp/` both reach the transport, with mount semantics."""
    to_mcp: list[dict] = []
    to_api: list[str] = []

    async def mcp_app(scope, receive, send):
        to_mcp.append(scope)

    async def api(scope, receive, send):
        to_api.append(scope["path"])

    disp = remote.MCPPathDispatcher(api, mcp_app, "/mcp")
    for path in ("/mcp", "/mcp/", "/mcp/extra"):
        await disp({"type": "http", "path": path}, _noop_receive, _Recorder())

    assert [s["path"] for s in to_mcp] == ["/", "/", "/extra"]
    assert all(s["root_path"] == "/mcp" for s in to_mcp)
    assert to_api == []


@pytest.mark.asyncio
async def test_dispatcher_leaves_every_other_path_to_the_api():
    to_api: list[str] = []

    async def mcp_app(scope, receive, send):  # pragma: no cover
        raise AssertionError("API path reached the transport")

    async def api(scope, receive, send):
        to_api.append(scope.get("path", scope["type"]))

    disp = remote.MCPPathDispatcher(api, mcp_app, "/mcp")
    for path in ("/", "/api", "/mcpx", "/connect"):
        await disp({"type": "http", "path": path}, _noop_receive, _Recorder())
    # Lifespan belongs to the API app — it owns startup/shutdown.
    await disp({"type": "lifespan"}, _noop_receive, _Recorder())

    assert to_api == ["/", "/api", "/mcpx", "/connect", "lifespan"]


def test_ipv6_hosts_keep_their_brackets(monkeypatch):
    """Splitting an IPv6 literal on the first colon yields `[2001:*`."""
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://[2001:db8::1]:8443/mcp", raising=False
    )
    hosts = remote.allowed_transport_hosts()
    assert "[2001:db8::1]:8443" in hosts
    assert "[2001:db8::1]:*" in hosts
    assert not any(h.startswith("[2001:*") for h in hosts)


def test_allowed_transport_hosts_derived_from_public_url():
    hosts = remote.allowed_transport_hosts()
    assert "api.example.com" in hosts
    assert "api.example.com:*" in hosts


def test_allowed_transport_hosts_explicit_override(monkeypatch):
    monkeypatch.setattr(
        settings, "MCP_ALLOWED_HOSTS", "mcp.example.org, alt.example.org",
        raising=False,
    )
    hosts = remote.allowed_transport_hosts()
    assert "mcp.example.org" in hosts and "alt.example.org" in hosts


def test_transport_security_allows_the_public_host(monkeypatch):
    pytest.importorskip("mcp", reason="mcp package not installed")
    sec = remote._transport_security()
    assert sec.enable_dns_rebinding_protection is True
    # The deployed host must be allowed, or every request is 421.
    assert "api.example.com" in sec.allowed_hosts
    # Localhost stays usable for local clients.
    assert "localhost:*" in sec.allowed_hosts


def test_transport_security_opens_up_when_no_host_is_known(monkeypatch):
    """Better an unconfigured server that answers than one that 421s everything."""
    pytest.importorskip("mcp", reason="mcp package not installed")
    monkeypatch.setattr(settings, "MCP_PUBLIC_URL", None, raising=False)
    monkeypatch.setattr(settings, "MCP_ALLOWED_HOSTS", "", raising=False)
    assert remote._transport_security().enable_dns_rebinding_protection is False


def test_sse_stream_is_not_swallowed_by_the_app_middleware(monkeypatch):
    """The server→client SSE channel must deliver headers immediately.

    This needs a real socket: `TestClient`'s transport runs the app to
    completion before returning, so an endless stream can never "finish" and
    every result looks like a hang. Measured over HTTP, mounting the transport
    inside the app's middleware stack yields *zero* response bytes (GZip holds
    output back deciding whether to compress; BaseHTTPMiddleware re-frames the
    response), while dispatching above the stack answers at once. Guards the
    reason `MCPPathDispatcher` exists.
    """
    pytest.importorskip("mcp", reason="mcp package not installed")
    uvicorn = pytest.importorskip("uvicorn", reason="uvicorn not installed")
    httpx = pytest.importorskip("httpx", reason="httpx not installed")

    import threading

    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", False, raising=False)
    monkeypatch.setattr(settings, "MCP_ENABLED", True, raising=False)
    try:
        from backend.app import main as app_main
    except Exception as exc:
        pytest.skip(f"backend.app.main not importable: {exc}")

    # Keep the DB out of it — this test is about the ASGI stack.
    async def _noop():
        return None

    monkeypatch.setattr(app_main, "init_db", _noop, raising=False)
    monkeypatch.setattr(app_main, "close_db", _noop, raising=False)

    config = uvicorn.Config(
        app_main.app, host="127.0.0.1", port=0, log_level="error"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.1)
        if not server.started or not server.servers:
            pytest.skip("uvicorn did not start in this environment")
        port = server.servers[0].sockets[0].getsockname()[1]
        base = f"http://127.0.0.1:{port}"

        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            started = client.post(
                f"{base}/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "sse-test", "version": "0"},
                    },
                },
            )
            assert started.status_code == 200, started.text
            session = started.headers["mcp-session-id"]
            client.post(
                f"{base}/mcp",
                headers={**headers, "mcp-session-id": session},
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )

            # Headers must arrive without waiting for the stream to end.
            with httpx.Client(timeout=httpx.Timeout(5.0, read=2.0)) as streamer:
                with streamer.stream(
                    "GET",
                    f"{base}/mcp",
                    headers={
                        "accept": "text/event-stream",
                        "mcp-session-id": session,
                    },
                ) as stream:
                    assert stream.status_code == 200
                    assert "text/event-stream" in stream.headers["content-type"]
    finally:
        server.should_exit = True
        thread.join(timeout=10)


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
