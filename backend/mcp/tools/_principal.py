"""Who is calling an MCP tool — and the account that belongs to them.

The remote-MCP surface authenticates against an EXTERNAL OAuth authorization
server (`backend/mcp/remote.py`). When `MCP_REQUIRE_AUTH` is on, its
`BearerAuthMiddleware` validates the bearer and stashes the token's subject
in the ASGI request scope (`scope["state"]["mcp_subject"]`). This module is
the read side of that handoff, plus the bridge from an opaque OAuth subject
to a durable `User` row the chart gate can meter.

Two deliberate properties:

- `mcp_subject()` NEVER raises. Reading a request-scoped value out of the
  FastMCP context is version-sensitive plumbing; a failure to read it must
  degrade to "no principal" (which the caller handles honestly), not crash a
  tool call. It returns None off the HTTP transport (e.g. stdio, or a direct
  in-process call) and whenever the value is absent.

- A connector account is a `User` keyed on `oauth_subject`, distinct from a
  password account keyed on email. Free tier, one chart, tracked durably —
  the same entitlement store both transports share, so "one chart forever"
  means the same thing whether the chart came through the web or a connector.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

logger = logging.getLogger("oneiro.mcp.principal")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.models.user import User


def _subject_from_request(request: object) -> Optional[str]:
    """Pull `mcp_subject` off a Starlette-style request's scope state.

    `Request.state` is backed by `scope["state"]`, which is exactly where
    `BearerAuthMiddleware` writes the subject — so either access path finds
    it. Both are attempted because the object handed to us may be the
    Starlette request or the raw ASGI scope, depending on transport version.
    """
    # Starlette Request → .state.mcp_subject
    state = getattr(request, "state", None)
    if state is not None:
        subject = getattr(state, "mcp_subject", None)
        if subject:
            return str(subject)
    # Raw scope dict → scope["state"]["mcp_subject"]
    scope = getattr(request, "scope", None)
    if isinstance(scope, dict):
        subject = (scope.get("state") or {}).get("mcp_subject")
        if subject:
            return str(subject)
    if isinstance(request, dict):
        subject = (request.get("state") or {}).get("mcp_subject")
        if subject:
            return str(subject)
    return None


def mcp_auth_context() -> tuple[bool, Optional[str]]:
    """`(on_http_transport, subject)` for the current MCP call.

    The gate needs to tell three situations apart, and a bare Optional
    subject cannot:

    - `(False, None)` — OFF the HTTP transport entirely: a stdio client
      (local, trusted, no OAuth concept) or a direct in-process call. There is
      no principal to expect, so issuance is simply not metered.
    - `(True, None)` — ON the HTTP transport but the subject is unreadable.
      Under `MCP_REQUIRE_AUTH` a valid bearer was required to get here, so this
      is a broken handoff: the gate fails CLOSED.
    - `(True, "sub…")` — a real authenticated principal to meter.

    Never raises: any failure to read the context degrades to `(False, None)`.
    """
    try:
        from mcp.server.lowlevel.server import request_ctx
    except Exception:  # pragma: no cover - mcp layout differences
        return False, None
    try:
        rc = request_ctx.get()
    except LookupError:
        return False, None  # No request in context (stdio / direct call).
    except Exception:  # pragma: no cover - defensive
        return False, None
    request = getattr(rc, "request", None)
    if request is None:
        return False, None
    try:
        return True, _subject_from_request(request)
    except Exception:  # pragma: no cover - defensive
        return True, None


def mcp_subject() -> Optional[str]:
    """The authenticated OAuth subject of the current MCP call, or None.

    Thin wrapper over `mcp_auth_context` for callers that only need the
    subject and treat None uniformly.
    """
    return mcp_auth_context()[1]


async def resolve_connector_user(db: AsyncSession, subject: str) -> User:
    """Find (or create) the connector account for this OAuth subject.

    Subscriptions are eager-loaded so tier computation does not lazy-load
    outside the greenlet. A brand-new connector account is free tier with no
    subscriptions — exactly the "one free chart" starting state — and stays a
    pending row until the caller commits (which it does only after a
    successful, entitled issuance).
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.models.user import User

    result = await db.execute(
        select(User)
        .options(selectinload(User.subscriptions))
        .where(User.oauth_subject == subject)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(oauth_subject=subject, is_active=True, is_verified=True)
        db.add(user)
    return user
