"""Remote-MCP surface: serve the MCP server over HTTP as a connector.

Turns the stdio MCP server (`backend/mcp/server.py`) into something Claude,
ChatGPT and Gemini can add by URL. Two pieces:

1. **Transport** — the FastMCP streamable-HTTP ASGI app, mounted into the main
   FastAPI app (see `backend/app/main.py`) so one Render service serves both
   the REST API and `/mcp`. No second paid service.

2. **Authorization** — the MCP spec requires OAuth 2.1 with PKCE; a bare API
   key is not a valid connector flow. This module implements the *resource
   server* half only:
   - publishes `/.well-known/oauth-protected-resource` (RFC 9728) pointing at
     an external authorization server (Auth0 / Clerk / Stytch / WorkOS — any AS
     with Dynamic Client Registration, which is what Claude prefers),
   - validates the incoming bearer JWT against that AS (signature via JWKS,
     `iss`, `aud`, `exp`, optional scopes),
   - answers unauthenticated calls with `401` + a `WWW-Authenticate` header
     carrying the metadata URL, which is how clients discover where to log in.

   Running your own authorization server is explicitly NOT attempted here —
   that is the part worth delegating to an identity provider.

Local development: set `MCP_DEV_TOKEN` and pass it as a bearer token. Refused
in production so a dev shortcut can never ship as the auth story.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from backend.core.config import settings

logger = logging.getLogger("oneiro.mcp.remote")

# RFC 9728 well-known path for OAuth 2.0 Protected Resource Metadata.
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource"

# JWKS cache: {jwks_url: (fetched_at_monotonic, keys)}
_JWKS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_JWKS_TTL_SECONDS = 600.0


class AuthError(Exception):
    """Bearer token missing or invalid. Carries the RFC 6750 error code."""

    def __init__(self, code: str, description: str, status: int = 401) -> None:
        super().__init__(description)
        self.code = code
        self.description = description
        self.status = status


# --- configuration helpers ----------------------------------------------------

def resource_url() -> str:
    """Canonical resource identifier for this MCP server.

    This is the audience clients must request a token for, and the `resource`
    value in the protected-resource metadata. Derived from MCP_PUBLIC_URL so
    it stays a single source of truth.
    """
    base = (settings.MCP_PUBLIC_URL or "").rstrip("/")
    if base:
        return base
    # Local fallback keeps dev usable without extra env vars.
    return f"http://localhost:8000{settings.MCP_PATH}"


def audience() -> str:
    return settings.MCP_AUTH_AUDIENCE or resource_url()


def jwks_url() -> Optional[str]:
    if settings.MCP_AUTH_JWKS_URL:
        return settings.MCP_AUTH_JWKS_URL
    issuer = (settings.MCP_AUTH_ISSUER or "").rstrip("/")
    if not issuer:
        return None
    return f"{issuer}/.well-known/jwks.json"


def auth_configured() -> bool:
    """True when a real authorization server is wired up."""
    return bool(settings.MCP_AUTH_ISSUER and jwks_url())


def required_scopes() -> list[str]:
    return [s for s in (settings.MCP_REQUIRED_SCOPES or "").split() if s]


def protected_resource_metadata() -> dict[str, Any]:
    """RFC 9728 document telling clients which AS guards this resource."""
    meta: dict[str, Any] = {
        "resource": resource_url(),
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://github.com/alpro1000/oneiro-scope",
    }
    if settings.MCP_AUTH_ISSUER:
        meta["authorization_servers"] = [settings.MCP_AUTH_ISSUER.rstrip("/")]
    scopes = required_scopes()
    if scopes:
        meta["scopes_supported"] = scopes
    return meta


def www_authenticate_header() -> str:
    """Value clients read to discover the authorization server."""
    base = resource_url().split(settings.MCP_PATH)[0].rstrip("/")
    return (
        'Bearer realm="OneiroScope MCP", '
        f'resource_metadata="{base}{PROTECTED_RESOURCE_PATH}"'
    )


# --- token verification -------------------------------------------------------

async def _fetch_jwks(url: str) -> list[dict[str, Any]]:
    now = time.monotonic()
    cached = _JWKS_CACHE.get(url)
    if cached and (now - cached[0]) < _JWKS_TTL_SECONDS:
        return cached[1]

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])

    _JWKS_CACHE[url] = (now, keys)
    return keys


async def verify_bearer(token: str) -> dict[str, Any]:
    """Validate a bearer token, returning its claims.

    Order matters: the dev token is only honoured outside production, so a
    misconfigured deploy fails closed instead of accepting a shared secret.
    """
    dev_token = settings.MCP_DEV_TOKEN
    if dev_token and token == dev_token:
        if settings.ENVIRONMENT == "production":
            raise AuthError(
                "invalid_token",
                "MCP_DEV_TOKEN is refused in production — configure an "
                "OAuth authorization server (MCP_AUTH_ISSUER).",
            )
        return {"sub": "dev", "aud": audience(), "scope": " ".join(required_scopes())}

    url = jwks_url()
    if not url:
        raise AuthError(
            "invalid_token",
            "This server has no authorization server configured "
            "(set MCP_AUTH_ISSUER / MCP_AUTH_JWKS_URL).",
        )

    try:
        keys = await _fetch_jwks(url)
    except Exception as exc:  # network/JWKS problems are server-side
        logger.warning("JWKS fetch failed for %s: %s", url, exc)
        raise AuthError("temporarily_unavailable", "Could not fetch JWKS", status=503)

    from jose import jwt as jose_jwt
    from jose.exceptions import JWTError

    try:
        header = jose_jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthError("invalid_token", f"Malformed token: {exc}")

    kid = header.get("kid")
    key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        # Key rotation: drop the cache once and retry with fresh keys.
        _JWKS_CACHE.pop(url, None)
        try:
            keys = await _fetch_jwks(url)
        except Exception as exc:
            logger.warning("JWKS refetch failed for %s: %s", url, exc)
            raise AuthError("temporarily_unavailable", "Could not fetch JWKS", status=503)
        key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        raise AuthError("invalid_token", "Unknown signing key")

    try:
        claims = jose_jwt.decode(
            token,
            key,
            algorithms=[header.get("alg", "RS256")],
            audience=audience(),
            issuer=settings.MCP_AUTH_ISSUER.rstrip("/") if settings.MCP_AUTH_ISSUER else None,
            options={"verify_at_hash": False},
        )
    except JWTError as exc:
        raise AuthError("invalid_token", f"Token rejected: {exc}")

    needed = set(required_scopes())
    if needed:
        granted = set(str(claims.get("scope", "")).split())
        granted |= set(claims.get("scp", []) or [])
        missing = needed - granted
        if missing:
            raise AuthError(
                "insufficient_scope",
                f"Missing scope(s): {' '.join(sorted(missing))}",
                status=403,
            )
    return claims


# --- ASGI plumbing ------------------------------------------------------------

class BearerAuthMiddleware:
    """Pure-ASGI guard in front of the MCP transport.

    Kept as raw ASGI (not BaseHTTPMiddleware) because the streamable-HTTP
    transport streams responses and long-lived SSE; wrapping those in a
    buffering middleware breaks them.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Preflight must stay unauthenticated or browser clients can't connect.
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        if not settings.MCP_REQUIRE_AUTH:
            await self.app(scope, receive, send)
            return

        token = _bearer_from_scope(scope)
        if not token:
            await _send_auth_error(
                send,
                AuthError("invalid_request", "Missing bearer token"),
            )
            return
        try:
            claims = await verify_bearer(token)
        except AuthError as exc:
            await _send_auth_error(send, exc)
            return

        # Hand identity to tools that need it (quotas, cost attribution).
        scope.setdefault("state", {})
        scope["state"]["mcp_subject"] = claims.get("sub")
        scope["state"]["mcp_claims"] = claims
        await self.app(scope, receive, send)


def _bearer_from_scope(scope: dict) -> Optional[str]:
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == b"authorization":
            value = raw_value.decode("latin-1")
            if value.lower().startswith("bearer "):
                return value[7:].strip()
    return None


async def _send_auth_error(send: Any, exc: AuthError) -> None:
    import json

    body = json.dumps(
        {"error": exc.code, "error_description": exc.description}
    ).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if exc.status == 401:
        headers.append((b"www-authenticate", www_authenticate_header().encode()))
    await send(
        {"type": "http.response.start", "status": exc.status, "headers": headers}
    )
    await send({"type": "http.response.body", "body": body})


def build_mcp_http_app() -> tuple[Optional[Any], Optional[Any]]:
    """Build the mountable MCP ASGI app.

    Returns `(asgi_app, session_manager)`. Either may be None:
    - `asgi_app is None` when MCP is disabled or the `mcp` package is absent
      (the REST API must still boot — MCP is an add-on surface, not a
      hard dependency of the web service).
    - `session_manager` is the object whose `.run()` the host application must
      enter for the lifetime of the process; None for stateless transports.
    """
    if not settings.MCP_ENABLED:
        logger.info("Remote MCP disabled (MCP_ENABLED=false)")
        return None, None

    try:
        from backend.mcp.server import mcp
    except Exception as exc:  # pragma: no cover - import-time env issues
        logger.warning("Remote MCP unavailable (%s: %s)", type(exc).__name__, exc)
        return None, None

    try:
        asgi_app = mcp.streamable_http_app()
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build MCP HTTP app: %s", exc)
        return None, None

    if settings.MCP_REQUIRE_AUTH and not auth_configured():
        if settings.ENVIRONMENT == "production":
            logger.error(
                "Remote MCP requires auth but no authorization server is "
                "configured — mounting refused. Set MCP_AUTH_ISSUER (and "
                "MCP_AUTH_AUDIENCE), or set MCP_REQUIRE_AUTH=false for a "
                "deliberately public server."
            )
            return None, None
        logger.warning(
            "Remote MCP: no MCP_AUTH_ISSUER; only MCP_DEV_TOKEN will be "
            "accepted (non-production only)."
        )

    session_manager = getattr(mcp, "session_manager", None)
    return BearerAuthMiddleware(asgi_app), session_manager
