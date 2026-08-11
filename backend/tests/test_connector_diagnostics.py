"""Tests for the connector self-check endpoint.

The point of `/connect/diagnostics` is that it is trustworthy when someone
cannot read a log — so each test pins a real misconfiguration to the check
that must catch it, and one test pins the thing it must never do: print a
secret.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.portal import diagnostics as diag  # noqa: E402


@pytest.fixture
def client():
    """Through the real app: the endpoint reports on the app's own wiring."""
    try:
        from backend.app.main import app
    except Exception as exc:  # optional heavy dep absent
        pytest.skip(f"backend.app.main not importable: {exc}")
    return TestClient(app)


@pytest.fixture(autouse=True)
def _baseline(monkeypatch):
    monkeypatch.setattr(settings, "MCP_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "MCP_PATH", "/mcp", raising=False)
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://testserver/mcp", raising=False
    )
    monkeypatch.setattr(settings, "MCP_ALLOWED_HOSTS", "", raising=False)
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", False, raising=False)
    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", None, raising=False)
    monkeypatch.setattr(settings, "MCP_AUTH_JWKS_URL", None, raising=False)
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "", raising=False)


def _check(body, check_id):
    for c in body["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"no check {check_id!r} in {[c['id'] for c in body['checks']]}")


def test_public_server_reports_mode_public_and_flags_open_auth(client):
    body = client.get("/connect/diagnostics").json()
    assert body["mode"] == "public"
    auth = _check(body, "auth_enforced")
    assert auth["ok"] is False
    assert "anyone with the URL" in auth["detail"]
    assert "MCP_AUTH_ISSUER" in auth["fix"]
    # An open server is not "ready" — that is the whole point of the flag.
    assert body["ready"] is False


def test_missing_public_url_is_called_out(client, monkeypatch):
    monkeypatch.setattr(settings, "MCP_PUBLIC_URL", None, raising=False)
    body = client.get("/connect/diagnostics").json()
    url_check = _check(body, "public_url")
    assert url_check["ok"] is False
    assert "MCP_PUBLIC_URL" in url_check["fix"]


def test_foreign_host_is_reported_as_the_421_cause(client, monkeypatch):
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://real.example.com/mcp", raising=False
    )
    body = client.get("/connect/diagnostics").json()
    host = _check(body, "host_allowed")
    assert host["ok"] is False
    assert "421" in host["detail"]
    assert "MCP_ALLOWED_HOSTS" in host["fix"]


def test_matching_host_passes(client, monkeypatch):
    monkeypatch.setattr(
        settings, "MCP_ALLOWED_HOSTS", "testserver", raising=False
    )
    body = client.get("/connect/diagnostics").json()
    assert _check(body, "host_allowed")["ok"] is True


def test_auth_required_without_an_issuer_is_the_404_explanation(
    client, monkeypatch
):
    """The exact state the owner's Render service was in."""
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    body = client.get("/connect/diagnostics").json()
    configured = _check(body, "auth_configured")
    assert configured["ok"] is False
    assert "MCP_AUTH_ISSUER" in configured["fix"]
    # …and the discovery document is correctly withheld in that state.
    assert _check(body, "discovery_published")["ok"] is False


def test_fully_configured_reports_oauth_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(
        settings, "MCP_AUTH_ISSUER", "https://tenant.eu.auth0.com/", raising=False
    )

    async def _ok():
        return True, "3 signing key(s)"

    async def _dcr():
        return True, "registration_endpoint: https://tenant.eu.auth0.com/oidc/register"

    monkeypatch.setattr(diag, "_jwks_reachable", _ok)
    monkeypatch.setattr(diag, "_dcr_advertised", _dcr)
    body = client.get("/connect/diagnostics").json()
    assert body["mode"] == "oauth"
    assert _check(body, "auth_configured")["ok"] is True
    assert _check(body, "discovery_published")["ok"] is True
    assert _check(body, "jwks_reachable")["ok"] is True
    assert _check(body, "dcr_advertised")["ok"] is True


def test_unreachable_jwks_is_surfaced_with_a_fix(client, monkeypatch):
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(
        settings, "MCP_AUTH_ISSUER", "https://tenant.eu.auth0.com/", raising=False
    )

    async def _fail():
        return False, "unreachable: ConnectError"

    async def _dcr():
        return True, "registration_endpoint: https://tenant.eu.auth0.com/oidc/register"

    monkeypatch.setattr(diag, "_jwks_reachable", _fail)
    monkeypatch.setattr(diag, "_dcr_advertised", _dcr)
    body = client.get("/connect/diagnostics").json()
    jwks = _check(body, "jwks_reachable")
    assert jwks["ok"] is False
    assert "trailing" in jwks["fix"] or "slash" in jwks["fix"]
    assert body["ready"] is False


def test_never_leaks_a_secret(client, monkeypatch):
    """This endpoint is public; a config dump must stay secret-free."""
    monkeypatch.setattr(settings, "MCP_DEV_TOKEN", "dev-token-value", raising=False)
    monkeypatch.setattr(settings, "SECRET_KEY", "app-secret-value", raising=False)
    text = client.get("/connect/diagnostics").text
    assert "dev-token-value" not in text
    assert "app-secret-value" not in text


def test_host_matcher_handles_wildcard_ports():
    assert diag._host_allowed("api.example.com:8443", ["api.example.com:*"])
    assert diag._host_allowed("api.example.com", ["api.example.com"])
    assert not diag._host_allowed("evil.example.net", ["api.example.com:*"])
    # No allow-list means the transport's protection is off — nothing to fail.
    assert diag._host_allowed("anything", [])


def test_missing_dcr_is_named_as_the_connection_killer(client, monkeypatch):
    """The reported symptom was "Failed to start MCP authorization" on the
    user's screen — with nothing wrong in this deployment's own config.
    Claude registers itself as an OAuth client before it can send anyone to
    log in; an issuer that advertises no registration_endpoint kills the
    flow at that step. Auth0 ships with the flag OFF, so this row must name
    it rather than leave the owner staring at a green everything-else."""
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(
        settings, "MCP_AUTH_ISSUER", "https://tenant.eu.auth0.com/", raising=False
    )

    async def _ok():
        return True, "3 signing key(s)"

    async def _no_dcr():
        return False, "no registration_endpoint"

    monkeypatch.setattr(diag, "_jwks_reachable", _ok)
    monkeypatch.setattr(diag, "_dcr_advertised", _no_dcr)
    body = client.get("/connect/diagnostics").json()
    row = _check(body, "dcr_advertised")
    assert row["ok"] is False
    assert "Dynamic Application Registration" in row["fix"]
    assert body["ready"] is False


def test_diagnostics_shows_the_tools_this_process_actually_serves(client):
    """Three times running, a client's cached schema was debugged as the
    server: "46 tools, transit_arc answers Unknown tool". The server has
    never listed those names since WP-10. This field is the proof a browser
    can open: whatever a client shows that is not in this list is the
    client's cache, and the fix is re-adding the connector."""
    body = client.get("/connect/diagnostics").json()
    tools = body["tools"]
    assert tools["count"] == len(tools["names"]) > 0
    assert "calculate_natal_chart" in tools["names"]
    for ghost in (
        "transit_arc", "transit_meaning", "electional_day",
        "list_event_types", "horoscope_report", "profile_report_file",
        "physiognomy_methods", "generate_horoscope",
    ):
        assert ghost not in tools["names"], (
            f"{ghost} is served again — the cached-client diagnosis in the "
            "session log is now wrong, re-investigate"
        )


def test_the_cheap_dcr_check_does_not_claim_more_than_it_tested(client, monkeypatch):
    """A green that meant nothing. Auth0 publishes `registration_endpoint`
    whether or not the tenant accepts dynamic registration, so reading the
    field reported ok while real registrations were refused — the connector
    said "Couldn't register with OneiroScope's sign-in service" against a
    fully green diagnostics page. The wording must now say what it proved."""
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(
        settings, "MCP_AUTH_ISSUER", "https://tenant.eu.auth0.com/", raising=False
    )

    async def _ok():
        return True, "3 signing key(s)"

    monkeypatch.setattr(diag, "_jwks_reachable", _ok)

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"registration_endpoint": "https://tenant.eu.auth0.com/oidc/register"}

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return _Resp()
        async def post(self, url, json):  # must not be reached without probe
            raise AssertionError("the default check must not POST")

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())

    row = _check(client.get("/connect/diagnostics").json(), "dcr_advertised")
    assert row["ok"] is True
    assert "NOT proof" in row["detail"] and "probe=1" in row["detail"]


def test_the_probe_separates_open_registration_from_refused(client, monkeypatch):
    """The probe posts an empty body: no client can be created either way.
    400 means the server took the request and disliked the payload — i.e.
    registration is open. 403 is the actual failure the owner hit."""
    monkeypatch.setattr(settings, "MCP_REQUIRE_AUTH", True, raising=False)
    monkeypatch.setattr(
        settings, "MCP_AUTH_ISSUER", "https://tenant.eu.auth0.com/", raising=False
    )

    async def _ok():
        return True, "3 signing key(s)"

    monkeypatch.setattr(diag, "_jwks_reachable", _ok)

    import httpx

    def _client_returning(post_status):
        class _Disc:
            status_code = 200
            @staticmethod
            def json():
                return {"registration_endpoint": "https://tenant.eu.auth0.com/oidc/register"}

        class _Reg:
            status_code = post_status

        class _Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return _Disc()
            async def post(self, url, json):
                assert json == {}, "the probe must not send a creatable payload"
                return _Reg()

        return lambda **kw: _Client()

    monkeypatch.setattr(httpx, "AsyncClient", _client_returning(400))
    row = _check(client.get("/connect/diagnostics?probe=1").json(), "dcr_advertised")
    assert row["ok"] is True and "accepts dynamic registration" in row["detail"]

    monkeypatch.setattr(httpx, "AsyncClient", _client_returning(403))
    row = _check(client.get("/connect/diagnostics?probe=1").json(), "dcr_advertised")
    assert row["ok"] is False
    assert "REFUSES" in row["detail"]
    # The fix must name the escape hatch that needs no DCR at all.
    assert "Regular Web Application" in row["fix"]
