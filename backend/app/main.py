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

# Import routers
from backend.api.v1 import lunar, health, astrology


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database
    if settings.ENVIRONMENT == "development":
        logger.info("Initializing database...")
        await init_db()

    logger.info("Application startup complete")

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
# app.include_router(dreams.router, prefix="/api/v1", tags=["Dreams"])  # Coming soon
# app.include_router(asr.router, prefix="/api/v1", tags=["ASR"])  # Coming soon
# app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])  # Coming soon


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
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
