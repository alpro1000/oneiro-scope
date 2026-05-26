"""Health check endpoints"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from backend.core.database import get_db
from backend.core.config import settings

router = APIRouter()


def _ephemeris_mode() -> dict:
    """Report which Swiss Ephemeris mode the backend is configured to use.

    SWIEPH (binary files) is preferred for arc-second precision; MOSEPH
    (analytic) is the fallback when binaries are absent. Surfacing this in
    /health lets validate-prod skill and operators tell which mode is live.
    """
    path = os.getenv("SE_EPHE_PATH")
    if path and Path(path).is_dir():
        files = sorted(p.name for p in Path(path).glob("*.se1"))
        if files:
            return {"engine": "SWIEPH", "ephe_path": path, "files": files[:5]}
    return {"engine": "MOSEPH", "ephe_path": path or None, "files": []}


@router.get("/health")
async def health_check():
    """Basic health check + ephemeris mode."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "ephemeris": _ephemeris_mode(),
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with dependencies"""

    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "checks": {}
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"alive": True}
