"""
OneiroScope FastAPI Application

Main entry point for the dream analysis service.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import time
import logging

from backend.core.config import settings
from backend.core.database import init_db, close_db
from backend.core.logging import logger
from backend.middleware import RateLimitMiddleware

# Import routers
from backend.api.v1 import (
    lunar,
    health,
    astrology,
    chart,
    dreams,
    auth,
    billing,
    users,
    physiognomy,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Startup verification (WP-1): importing backend.core.ephemeris has
    # already verified the .se1 files or killed the process — this line
    # records what the process actually loaded. No fallback branch exists.
    from backend.core.ephemeris import startup_summary

    eph = startup_summary()
    logger.info(
        "Ephemeris: SWIEPH %s (path=%s, files=%s)",
        eph["swisseph_version"],
        eph["ephe_path"],
        ",".join(eph["files"]),
    )

    # Ensure the database schema exists. init_db() is Base.metadata.create_all,
    # which is idempotent (checkfirst): it creates only MISSING tables and never
    # alters or drops. The base tables (users, dream_entries, …) have no
    # create-table migration — Alembic here only carries column deltas (0002
    # ALTERs `users`) — so create_all is currently the sole thing that creates
    # them. Gating it to `development` (an earlier hardening) meant production
    # never created `users`, so the natal entitlement gate raised UndefinedTable
    # (500) on every call. It runs in all environments until the base tables get
    # a real Alembic baseline + `alembic upgrade head` on deploy (tracked).
    logger.info("Ensuring database schema (create_all, idempotent)...")
    await init_db()

    logger.info("Application startup complete")

    # The streamable-HTTP transport keeps per-session state, so its session
    # manager has to be running for the lifetime of the process. Mounted
    # sub-apps don't get their own lifespan, hence entering it here.
    mcp_session_manager = getattr(app.state, "mcp_session_manager", None)
    if mcp_session_manager is not None:
        async with mcp_session_manager.run():
            logger.info("Remote MCP session manager running")
            yield
            logger.info("Stopping remote MCP session manager...")
    else:
        yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered dream analysis service with lunar calendar integration",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# Middleware

# Rate Limiting (v2.2 - Phase 2 Hardening)
app.add_middleware(
    RateLimitMiddleware,
    per_user_limit=settings.RATE_LIMIT_PER_USER,
    global_limit=settings.RATE_LIMIT_GLOBAL,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""

    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
    )

    # Add custom headers
    response.headers["X-Process-Time"] = str(duration)

    return response


# Exception handlers

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Not Found",
            "message": f"The requested resource was not found: {request.url.path}",
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(lunar.router, prefix="/api/v1", tags=["Lunar"])
app.include_router(astrology.router, prefix="/api/v1", tags=["Astrology"])
app.include_router(chart.router, prefix="/api/v1", tags=["Chart"])
app.include_router(dreams.router, prefix="/api/v1", tags=["Dreams"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(physiognomy.router, prefix="/api/v1", tags=["Physiognomy"])

# Portal: server-rendered landing / connect / pricing / legal pages. Same
# service as the API and /mcp — no second host, no build step.
# See docs/specs/product-architecture/.
from backend.portal.account import router as account_router  # noqa: E402
from backend.portal.router import router as portal_router  # noqa: E402

app.include_router(portal_router)
# Account page: plan, own model keys, data export, deletion — the few things
# a chat connector cannot do. See backend/portal/account.py.
app.include_router(account_router)
# Connector self-check at /connect/diagnostics — a URL that names whatever is
# misconfigured, for whoever is clicking through a dashboard.
from backend.portal.diagnostics import router as diagnostics_router  # noqa: E402

app.include_router(diagnostics_router)
# app.include_router(asr.router, prefix="/api/v1", tags=["ASR"])  # Coming soon
# app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])  # Coming soon


# --- Remote MCP connector surface --------------------------------------------
# Mounts the MCP server at settings.MCP_PATH so Claude / ChatGPT / Gemini can
# add this deployment as a connector by URL — same service, no extra host.
# Never fatal: if the mcp package or its auth config is missing, the REST API
# still boots and only this surface is skipped (see backend/mcp/remote.py).
from backend.mcp.remote import (  # noqa: E402  (after app creation by design)
    MCPPathDispatcher,
    build_mcp_http_app,
    oauth_discovery_enabled,
    protected_resource_metadata,
    protected_resource_paths,
)


class ProtectedResourceMetadata(BaseModel):
    """RFC 9728 protected-resource metadata (field names fixed by the RFC)."""

    resource: str
    authorization_servers: list[str] | None = None
    bearer_methods_supported: list[str]
    resource_documentation: str | None = None
    scopes_supported: list[str] | None = None


async def oauth_protected_resource():
    """RFC 9728 metadata: which authorization server guards the MCP endpoint.

    Clients fetch this after a 401 to learn where to send the user to log in.
    Absent an enforced authorization server there is nothing to point them at,
    and answering anyway sends them into a registration flow that cannot
    succeed — so this 404s until OAuth is both configured and required.

    Registered on every path in `protected_resource_paths()`: the RFC-canonical
    one for this resource (`/.well-known/oauth-protected-resource/mcp`, built by
    inserting the well-known segment between host and path) plus the bare form,
    which is what clients that ignore the path component probe.
    """
    if not oauth_discovery_enabled():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": (
                    "This MCP server does not use OAuth. Connect without "
                    "authorization, or configure MCP_AUTH_ISSUER with "
                    "MCP_REQUIRE_AUTH=true."
                ),
            },
        )
    return protected_resource_metadata()


for _prm_path in protected_resource_paths():
    app.get(
        _prm_path,
        response_model=ProtectedResourceMetadata,
        response_model_exclude_none=True,
        include_in_schema=False,
    )(oauth_protected_resource)


# Root endpoint — the portal owns "/", so API metadata moves to /api
class ApiInfo(BaseModel):
    """Response contract for the API metadata endpoint."""

    name: str
    version: str
    environment: str
    docs: str
    status: str


@app.get("/api", response_model=ApiInfo)
async def root() -> ApiInfo:
    """API information (the human-facing landing page lives at /)"""
    return ApiInfo(
        name=settings.APP_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        docs="/docs" if settings.DEBUG else "disabled",
        status="operational",
    )


# --- MCP dispatch (must stay last: `app` stops being a FastAPI instance) ------
# The transport streams SSE, and every middleware above would sit in front of
# that stream — GZip withholding bytes, BaseHTTPMiddleware re-framing the
# response — so /mcp is dispatched above the stack instead. `api_app` keeps the
# FastAPI object reachable for anything that needs the real thing.
api_app = app

_mcp_app, _mcp_session_manager = build_mcp_http_app()
if _mcp_app is not None:
    api_app.state.mcp_session_manager = _mcp_session_manager
    app = MCPPathDispatcher(api_app, _mcp_app, settings.MCP_PATH)
    logger.info("Remote MCP served at %s", settings.MCP_PATH)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
