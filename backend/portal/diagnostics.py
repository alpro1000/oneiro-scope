"""Connector self-check: one URL that says exactly what is misconfigured.

Setting this deployment up means getting four independent things right —
mount path, Host allow-list, OAuth discovery, and a reachable JWKS — and each
one fails with an error message that names none of them. A browser agent, or
an owner clicking around a dashboard, cannot run curl or read the server log.
So the server reports on itself.

Every check maps to a real failure mode we have actually hit; `fix` says which
environment variable moves it. Deliberately public and deliberately
secret-free: it returns booleans and values that are already discoverable from
outside (the issuer and the resource URL are published in the RFC 9728
document; the Host allow-list is observable by probing). Never a token, a key,
or a client secret.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.config import settings
from backend.mcp.remote import (
    PROTECTED_RESOURCE_PATH,
    allowed_transport_hosts,
    auth_configured,
    jwks_url,
    oauth_discovery_enabled,
    resource_url,
)

logger = logging.getLogger("oneiro.portal.diagnostics")

router = APIRouter(tags=["Portal"], include_in_schema=False)


class Check(BaseModel):
    """One verifiable fact about this deployment."""

    id: str
    ok: bool
    detail: str
    fix: Optional[str] = None


class Diagnostics(BaseModel):
    ready: bool
    mode: str
    connector_url: str
    checks: list[Check]
    config: dict[str, Any]


async def _jwks_reachable() -> tuple[bool, str]:
    """Fetch the JWKS the way token validation will, with a short timeout."""
    url = jwks_url()
    if not url:
        return False, "no JWKS URL (issuer not set)"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return False, f"{url} → HTTP {resp.status_code}"
        keys = resp.json().get("keys", [])
        if not keys:
            return False, f"{url} returned no keys"
        return True, f"{len(keys)} signing key(s) from {url}"
    except Exception as exc:
        return False, f"{url} unreachable: {type(exc).__name__}"


def _host_allowed(request_host: str, allowed: list[str]) -> bool:
    """Mirror the transport's own matching so the answer is not a guess."""
    if not allowed:
        return True  # protection disabled — everything passes
    if request_host in allowed:
        return True
    for pattern in allowed:
        if pattern.endswith(":*") and request_host.startswith(pattern[:-1]):
            return True
    return False


@router.get("/connect/diagnostics", response_model=Diagnostics)
async def diagnostics(request: Request) -> Diagnostics:
    """Machine-readable connector readiness. Open it in a browser."""
    from backend.app.main import api_app  # set at import; None-safe below

    mounted = getattr(api_app.state, "mcp_session_manager", None) is not None
    hosts = allowed_transport_hosts()
    request_host = request.headers.get("host", "")
    checks: list[Check] = []

    checks.append(Check(
        id="mcp_enabled",
        ok=settings.MCP_ENABLED,
        detail="MCP surface is enabled" if settings.MCP_ENABLED
               else "MCP_ENABLED is false — /mcp is not served",
        fix=None if settings.MCP_ENABLED else "set MCP_ENABLED=true",
    ))

    checks.append(Check(
        id="mcp_mounted",
        ok=mounted,
        detail="transport is mounted and its session manager is running"
               if mounted else
               "transport did NOT mount — with MCP_REQUIRE_AUTH=true in "
               "production and no MCP_AUTH_ISSUER the server refuses to expose "
               "tools unauthenticated, so /mcp returns 404",
        fix=None if mounted else
            "set MCP_AUTH_ISSUER (recommended) or MCP_REQUIRE_AUTH=false",
    ))

    has_public_url = bool(settings.MCP_PUBLIC_URL)
    checks.append(Check(
        id="public_url",
        ok=has_public_url,
        detail=f"MCP_PUBLIC_URL = {settings.MCP_PUBLIC_URL}" if has_public_url
               else "MCP_PUBLIC_URL is not set — the OAuth audience has no "
                    "canonical value and the Host allow-list is empty, so "
                    "DNS-rebinding protection is switched off",
        fix=None if has_public_url else
            "set MCP_PUBLIC_URL to the public /mcp URL of this service",
    ))

    host_ok = _host_allowed(request_host, hosts)
    checks.append(Check(
        id="host_allowed",
        ok=host_ok,
        detail=f"Host '{request_host}' is accepted by the transport" if host_ok
               else f"Host '{request_host}' is NOT in the allow-list {hosts} — "
                    "requests to /mcp answer 421",
        fix=None if host_ok else
            "add this hostname to MCP_ALLOWED_HOSTS, or correct MCP_PUBLIC_URL",
    ))

    enforced = bool(settings.MCP_REQUIRE_AUTH)
    checks.append(Check(
        id="auth_enforced",
        ok=enforced,
        detail="OAuth is required — /mcp refuses anonymous calls" if enforced
               else "OAuth is NOT required — anyone with the URL can call every "
                    "tool, and this path is outside the rate limiter",
        fix=None if enforced else
            "set MCP_AUTH_ISSUER, then MCP_REQUIRE_AUTH=true",
    ))

    if enforced or settings.MCP_AUTH_ISSUER:
        configured = auth_configured()
        checks.append(Check(
            id="auth_configured",
            ok=configured,
            detail=f"authorization server: {settings.MCP_AUTH_ISSUER}"
                   if configured else
                   "MCP_REQUIRE_AUTH is on but MCP_AUTH_ISSUER is empty — there "
                   "is no authorization server to send users to",
            fix=None if configured else "set MCP_AUTH_ISSUER (see "
                                        "docs/deploy/auth0-setup.md)",
        ))

        published = oauth_discovery_enabled()
        checks.append(Check(
            id="discovery_published",
            ok=published,
            detail=f"{PROTECTED_RESOURCE_PATH} is served"
                   if published else
                   "the discovery document is withheld — it is published only "
                   "when an issuer is set AND auth is enforced, so clients are "
                   "not sent into a login flow that cannot complete",
            fix=None if published else
                "set both MCP_AUTH_ISSUER and MCP_REQUIRE_AUTH=true",
        ))

        if configured:
            reachable, detail = await _jwks_reachable()
            checks.append(Check(
                id="jwks_reachable",
                ok=reachable,
                detail=detail,
                fix=None if reachable else
                    "check the issuer URL (Auth0 issuers end with a slash) and "
                    "that this service has outbound network access",
            ))

    # Not an MCP check, but the same class of failure and the same audience:
    # something is refused, the server looks healthy, and the reason is only
    # visible somewhere the person debugging cannot see. A browser blocked by
    # CORS reports "Failed to fetch" and nothing else; this row names the
    # variable that fixes it.
    cors_problem = settings.cors_problem()
    checks.append(Check(
        id="browser_origins",
        ok=cors_problem is None,
        detail=cors_problem or (
            f"CORS allows {settings.allowed_origins_list}"
            + (f" plus regex {settings.ALLOWED_ORIGIN_REGEX}"
               if settings.ALLOWED_ORIGIN_REGEX else "")
        ),
        fix=None if cors_problem is None else
            "set ALLOWED_ORIGINS to the frontend origin(s) WITH scheme, "
            "comma-separated (e.g. https://oneiroscope.vercel.app)",
    ))

    if enforced and auth_configured():
        mode = "oauth"
    elif settings.MCP_ENABLED and not enforced:
        mode = "public"
    else:
        mode = "unavailable"

    return Diagnostics(
        ready=all(c.ok for c in checks),
        mode=mode,
        connector_url=resource_url(),
        checks=checks,
        config={
            "environment": settings.ENVIRONMENT,
            "mcp_path": settings.MCP_PATH,
            "mcp_public_url": settings.MCP_PUBLIC_URL,
            "auth_issuer": settings.MCP_AUTH_ISSUER,
            "auth_audience": settings.MCP_AUTH_AUDIENCE or settings.MCP_PUBLIC_URL,
            "required_scopes": settings.MCP_REQUIRED_SCOPES or None,
            "allowed_hosts": hosts,
            "discovery_url": PROTECTED_RESOURCE_PATH,
        },
    )
