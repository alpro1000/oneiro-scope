"""
OneiroScope FastAPI Application

Main entry point for the dream analysis service.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
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

    # Surface ephemeris mode at startup — same source as /health.
    try:
        from backend.api.v1.health import _ephemeris_mode

        eph = _ephemeris_mode()
        if eph["engine"] == "SWIEPH":
            logger.info(
                "Ephemeris: SWIEPH (path=%s, files=%d)",
                eph["ephe_path"],
                len(eph["files"]),
            )
        else:
            logger.warning(
                "Ephemeris: MOSEPH (analytic fallback) — set SE_EPHE_PATH "
                "to a directory containing .se1 binaries for arc-second precision."
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not determine ephemeris mode: %s", exc)

    # Initialize database
    if settings.ENVIRONMENT == "development":
        logger.info("Initializing database...")
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
app.include_router(dreams.router, prefix="/api/v1", tags=["Dreams"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(physiognomy.router, prefix="/api/v1", tags=["Physiognomy"])

# Portal: server-rendered landing / connect / pricing / legal pages. Same
# service as the API and /mcp — no second host, no build step.
# See docs/specs/product-architecture/.
from backend.portal.router import router as portal_router  # noqa: E402

app.include_router(portal_router)
# app.include_router(asr.router, prefix="/api/v1", tags=["ASR"])  # Coming soon
# app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])  # Coming soon


# --- Remote MCP connector surface --------------------------------------------
# Mounts the MCP server at settings.MCP_PATH so Claude / ChatGPT / Gemini can
# add this deployment as a connector by URL — same service, no extra host.
# Never fatal: if the mcp package or its auth config is missing, the REST API
# still boots and only this surface is skipped (see backend/mcp/remote.py).
from backend.mcp.remote import (  # noqa: E402  (after app creation by design)
    PROTECTED_RESOURCE_PATH,
    build_mcp_http_app,
    protected_resource_metadata,
)


@app.get(PROTECTED_RESOURCE_PATH, include_in_schema=False)
async def oauth_protected_resource():
    """RFC 9728 metadata: which authorization server guards the MCP endpoint.

    Clients fetch this after a 401 to learn where to send the user to log in.
    """
    return protected_resource_metadata()


_mcp_app, _mcp_session_manager = build_mcp_http_app()
if _mcp_app is not None:
    app.mount(settings.MCP_PATH, _mcp_app)
    app.state.mcp_session_manager = _mcp_session_manager
    logger.info("Remote MCP mounted at %s", settings.MCP_PATH)


# Root endpoint — the portal owns "/", so API metadata moves to /api
@app.get("/api")
async def root():
    """API information (the human-facing landing page lives at /)"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
