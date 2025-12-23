"""Database configuration and session management.

The original implementation eagerly created SQLAlchemy engines during module
import. That made test collection fail whenever required environment variables
(`DATABASE_URL`, `DATABASE_URL_SYNC`) were not provided, because Pydantic would
raise validation errors before any tests could even run. Engines are now created
lazily when first requested so missing configuration doesn't block imports. When
database access is required, configure `DATABASE_URL`/`DATABASE_URL_SYNC` via
environment variables or a `.env` file.
"""

import logging
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine

from backend.core.config import settings

logger = logging.getLogger(__name__)


def _ensure_async_driver(url: str) -> str:
    """Convert a Postgres DSN to use the asyncpg driver if needed."""

    if url.startswith("postgresql+asyncpg://"):
        return url

    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")

    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")

    return url


def _require_setting(name: str, value: str | None) -> str:
    """Return a setting value or raise a clear error if it's missing."""

    if not value:
        raise RuntimeError(
            f"{name} is not configured. Set the {name} environment variable "
            "or provide it in the .env file before using the database layer."
        )
    return value


@lru_cache
def get_async_engine():
    """Create (or return) a cached async engine using configured settings."""

    url = _require_setting("DATABASE_URL", settings.DATABASE_URL)
    engine = create_async_engine(
        _ensure_async_driver(url),
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    logger.debug("Async engine created for %s", url)
    return engine


@lru_cache
def get_sync_engine():
    """Create (or return) a cached sync engine for migrations."""

    url = _require_setting("DATABASE_URL_SYNC", settings.DATABASE_URL_SYNC)
    engine = create_engine(
        url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    logger.debug("Sync engine created for %s", url)
    return engine


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return a cached session factory bound to the async engine."""

    return async_sessionmaker(
        get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async_session_factory = get_sessionmaker()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables"""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await get_async_engine().dispose()
