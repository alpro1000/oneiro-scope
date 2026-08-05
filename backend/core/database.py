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


def _ensure_sync_driver(url: str) -> str:
    """Convert a Postgres DSN to use the psycopg2 driver if needed.

    The mirror of `_ensure_async_driver`, and it matters more than it looks:
    the deploy runs `alembic upgrade head` before uvicorn, joined with `&&`, so
    a URL the sync engine cannot load is no longer a lazy error on first query
    — it stops the service from booting. Three shapes reach us in practice:
    `postgres://` (legacy; SQLAlchemy 2.0 dropped the alias entirely),
    `postgresql://` (what Render hands out), and `postgresql+asyncpg://` (when
    the async URL is reused because DATABASE_URL_SYNC was never set).
    """
    for prefix in ("postgres://", "postgresql://", "postgresql+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url.removeprefix(prefix)

    return url


def migration_url() -> str:
    """The database `alembic upgrade` should migrate, driver resolved.

    DATABASE_URL_SYNC is the intended setting but it is optional, and the
    migration now runs ahead of uvicorn joined by `&&` — an environment that
    set only DATABASE_URL would fail to boot entirely rather than degrade. So
    fall back to the async URL and translate its driver, and when neither
    exists name the variables instead of dying on `None`.

    Lives here rather than in `alembic/env.py` because that file is a script
    alembic execs, not a module anything can import or test.
    """
    url = settings.DATABASE_URL_SYNC or settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "No database configured for migrations. Set DATABASE_URL_SYNC "
            "(preferred) or DATABASE_URL before running `alembic upgrade`."
        )
    return _ensure_sync_driver(url)


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
        _ensure_sync_driver(url),
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
    """Create any MISSING tables — idempotent ``create_all`` (checkfirst).

    Importing ``backend.models`` first registers every ORM model on
    ``Base.metadata``; without it a table whose module has not been imported
    yet would be silently skipped. ``create_all`` never alters or drops an
    existing table, so this is safe to run against a populated database — it
    only fills in what is absent (e.g. the ``users`` table on a prod DB that
    predates it).
    """
    import backend.models  # noqa: F401 — side effect: registers models on Base

    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await get_async_engine().dispose()
