"""The chart gate against a REAL Postgres + a real ORM session.

Why this file exists: `test_chart_gate.py` builds its users with
`SimpleNamespace`, so no table, no session and no lazy load is ever involved.
Two production outages walked straight past it:

  1. `UndefinedTable: relation "users" does not exist` — nothing ever created
     the table outside the dev-only `init_db()`;
  2. `greenlet_spawn has not been called` — `current_tier()` read an unloaded
     `user.subscriptions` from synchronous code inside an async request.

Both are invisible to a fake. Both are caught here, because this exercises the
real `_gate_chart_issuance` against a real database:
`Base.metadata.create_all` must actually render every column (Postgres-only
`UUID` included — SQLite cannot, which is why this is not a SQLite test), and
a brand-new connector account must survive the commit-then-read-tier path.

Skips cleanly when TEST_DATABASE_URL is unset, so local runs are unaffected.
"""

from __future__ import annotations

import asyncio
import os

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB, reason="TEST_DATABASE_URL not set (needs a live Postgres)"
)

# Zaporizhzhia, 1977-07-01 22:30 local. The second key is the SAME birth as
# geocoded rather than typed — 1.4 km away, which the gate must treat as the
# same chart (see `same_chart`).
_UTC = "1977-07-01T19:30:00Z"
KEY_TYPED = f"{_UTC}|47.8388|35.1396"
KEY_GEOCODED = f"{_UTC}|47.85167|35.11714"
KEY_OTHER_CHART = "1985-03-10T06:00:00Z|50.4501|30.5234"


def _engine_and_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    url = TEST_DB
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    # Same configuration as production (backend/core/database.py).
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
def gate(monkeypatch):
    """Real Postgres schema + the gate wired to it, as one authenticated subject."""
    from backend.core.database import Base
    import backend.core.database as dbmod
    import backend.models  # noqa: F401 — registers every model on Base
    from backend.mcp.tools import astrology as A
    from backend.core import config

    engine, factory = _engine_and_factory()

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            # If this cannot render a column, the deployed schema could not
            # have been created either — exactly the first outage.
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())

    monkeypatch.setattr(dbmod, "get_sessionmaker", lambda: factory)
    monkeypatch.setattr(config.settings, "MCP_REQUIRE_AUTH", True)
    monkeypatch.setattr(A, "mcp_auth_context", lambda: (True, "oauth|test-subject"))

    yield A

    asyncio.run(engine.dispose())


def test_first_chart_for_a_brand_new_account_is_issued(gate):
    """The greenlet regression: a NEW account commits, then the tier is read.

    Every connector account took this branch after the users table was first
    created, so this was a 100% failure path in production.
    """
    refusal, stamp = asyncio.run(gate._gate_chart_issuance(KEY_TYPED))

    assert refusal is None, f"first chart must be issued, got refusal: {refusal}"
    assert stamp["gated"] is True
    assert stamp["tier"] == "free"


def test_the_same_chart_is_free_forever_and_survives_a_geocoder_shift(gate):
    """Re-fetching your own chart never costs a second grant — including when
    the coordinates arrive by a different route than the first time."""
    asyncio.run(gate._gate_chart_issuance(KEY_TYPED))

    exact, _ = asyncio.run(gate._gate_chart_issuance(KEY_TYPED))
    assert exact is None, "re-fetching the identical key must be free"

    shifted, _ = asyncio.run(gate._gate_chart_issuance(KEY_GEOCODED))
    assert shifted is None, (
        "the same birth 1.4 km away is the same chart — refusing it bills a "
        "user for their own chart"
    )


def test_a_genuinely_different_chart_is_refused(gate):
    """The paywall still holds: the tolerance must not open a second chart."""
    asyncio.run(gate._gate_chart_issuance(KEY_TYPED))

    refusal, stamp = asyncio.run(gate._gate_chart_issuance(KEY_OTHER_CHART))

    assert refusal is not None, "a different birth must consume the allowance"
    assert refusal["error"] == "entitlement_required"
    assert refusal["reason"] == "free_natal_chart_used"
    assert stamp == {"gated": True}


def test_the_grant_is_persisted_not_just_in_memory(gate):
    """A second process must see the same decision — the grant is a DB row."""
    asyncio.run(gate._gate_chart_issuance(KEY_TYPED))

    _, factory = _engine_and_factory()

    async def _read_back():
        from sqlalchemy import select

        from backend.models.user import User

        async with factory() as db:
            result = await db.execute(
                select(User).where(User.oauth_subject == "oauth|test-subject")
            )
            user = result.scalar_one()
            return user.free_natal_used, user.free_natal_chart_key

    used, key = asyncio.run(_read_back())
    assert used is True
    assert key == KEY_TYPED
