"""Health check endpoints"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from backend.core.database import get_db
from backend.core.config import settings
from backend.core.ephemeris import startup_summary

router = APIRouter()


class EphemerisInfo(BaseModel):
    """Live Swiss Ephemeris configuration surfaced by /health."""

    engine: str
    swisseph_version: str
    ephe_path: str
    files: list[str]


class HealthResponse(BaseModel):
    """Contract of the basic /health check (keepalive.yml greps it)."""

    status: str
    service: str
    version: str
    ephemeris: EphemerisInfo


def _ephemeris_mode() -> dict:
    """Report the live Swiss Ephemeris configuration.

    Always SWIEPH since WP-1: the .se1 files ship in the repo and their
    absence fails startup, so there is no fallback mode to report. The
    block still surfaces path/files/version so validate-prod and
    operators can confirm which data the process actually loaded.
    """
    return startup_summary()


@router.get("/health", response_model=HealthResponse)
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
