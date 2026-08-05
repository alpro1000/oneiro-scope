"""`alembic upgrade head` against a real Postgres — both starting points.

The baseline (0000) claims two things that must not be taken on trust, because
getting either wrong breaks the deploy that applies them:

  1. a FRESH database can be built by migrations alone — until now nothing
     created `users`, so a new environment came up without the table the
     entitlement gate needs;
  2. the EXISTING production database, whose tables were built by
     `create_all` before any migration ran, upgrades without error — the
     migrations must adopt what is already there rather than trying to create
     it again.

Both are asserted here against a live server; those tests skip without
TEST_DATABASE_URL. The first test needs no database at all — it checks that
the command the deploy actually runs can find the migrations.
"""

from __future__ import annotations

import os

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL")

needs_postgres = pytest.mark.skipif(
    not TEST_DB, reason="TEST_DATABASE_URL not set (needs a live Postgres)"
)


def _sync_url() -> str:
    """Alembic runs synchronously; translate the async test URL."""
    url = TEST_DB
    for prefix, repl in (
        ("postgresql+asyncpg://", "postgresql+psycopg2://"),
        ("postgres://", "postgresql+psycopg2://"),
    ):
        if url.startswith(prefix):
            return url.replace(prefix, repl, 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _engine():
    from sqlalchemy import create_engine

    return create_engine(_sync_url())


def _drop_everything() -> None:
    """A genuinely empty schema — not merely 'our tables dropped'."""
    from sqlalchemy import text

    with _engine().begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


def _ini_path() -> str:
    from pathlib import Path

    return str(Path(__file__).resolve().parents[1] / "alembic.ini")


def _alembic_config():
    """The SHIPPED config, with only the URL redirected.

    `script_location` is deliberately not overridden. An earlier version of
    this file set it explicitly and so passed against an alembic.ini whose
    relative `script_location = alembic` could not be resolved from the repo
    root — the exact directory the deploy runs from. The test has to fail on
    the config the deploy uses, not on a corrected copy of it.
    """
    from alembic.config import Config

    cfg = Config(_ini_path())
    cfg.set_main_option("sqlalchemy.url", _sync_url())
    return cfg


def test_the_deploys_command_can_find_the_migrations(monkeypatch):
    """`alembic -c backend/alembic.ini upgrade head`, run from the repo root.

    That is render.yaml's start command, chained with `&&` — if alembic cannot
    locate the versions directory the service does not boot at all. No database
    needed: this is a path-resolution check.
    """
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))

    revisions = [r.revision for r in script.walk_revisions()]
    assert "0000_baseline" in revisions, revisions
    assert script.get_current_head() == "0002_chart_gate_identity"


@pytest.fixture
def _point_settings_at_the_test_database(monkeypatch):
    """`alembic/env.py` reads the URL from settings, not from the config."""
    from backend.core import config

    monkeypatch.setattr(config.settings, "DATABASE_URL_SYNC", _sync_url())


def _tables() -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(_engine()).get_table_names())


def _user_columns() -> set[str]:
    from sqlalchemy import inspect

    return {c["name"] for c in inspect(_engine()).get_columns("users")}


@needs_postgres
@pytest.mark.usefixtures("_point_settings_at_the_test_database")
def test_a_fresh_database_is_built_by_migrations_alone():
    """What a brand-new environment gets. `users` missing here is the outage."""
    from alembic import command

    _drop_everything()
    command.upgrade(_alembic_config(), "head")

    tables = _tables()
    assert "users" in tables, "the entitlement gate has nothing to query"
    assert "dream_entries" in tables
    # 0002's columns must have landed on top of the baseline's table.
    assert {"oauth_subject", "free_natal_chart_key"} <= _user_columns()


@needs_postgres
@pytest.mark.usefixtures("_point_settings_at_the_test_database")
def test_upgrading_a_database_that_create_all_already_built_is_a_no_op():
    """Production's starting point: tables exist, alembic_version does not.

    Every migration has to adopt what it finds instead of re-creating it, or
    the first deploy that runs `upgrade head` dies on "already exists".
    """
    from alembic import command

    from backend.core.database import Base
    import backend.models  # noqa: F401 — registers every model on Base

    _drop_everything()
    with _engine().begin() as conn:
        Base.metadata.create_all(bind=conn)  # exactly how production was built

    assert "alembic_version" not in _tables(), "precondition: never stamped"

    command.upgrade(_alembic_config(), "head")  # must not raise

    assert "users" in _tables()
    assert {"oauth_subject", "free_natal_chart_key"} <= _user_columns()


@needs_postgres
@pytest.mark.usefixtures("_point_settings_at_the_test_database")
def test_running_upgrade_twice_changes_nothing():
    """Re-deploying the same revision must stay quiet."""
    from alembic import command

    _drop_everything()
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    before = _tables()

    command.upgrade(cfg, "head")  # must not raise

    assert _tables() == before


# --- the URL the deploy hands to alembic ------------------------------------
# `alembic upgrade head && uvicorn` means a URL the sync engine cannot load is
# no longer a lazy error on first query — it stops the service from booting.


@pytest.mark.parametrize(
    "given,expected",
    [
        # What Render's connectionString actually hands out.
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        # Legacy shape; SQLAlchemy 2.0 dropped the `postgres` dialect alias.
        ("postgres://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        # The async URL, reached by falling back when only DATABASE_URL is set.
        ("postgresql+asyncpg://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        # Already explicit — left alone.
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        # Not Postgres at all — not ours to rewrite.
        ("sqlite:///./local.db", "sqlite:///./local.db"),
    ],
)
def test_sync_driver_is_resolved_for_every_shape_that_reaches_us(given, expected):
    from backend.core.database import _ensure_sync_driver

    assert _ensure_sync_driver(given) == expected


def test_migration_url_falls_back_to_the_async_setting(monkeypatch):
    """Only DATABASE_URL set must not take the whole service down."""
    from backend.core import config

    monkeypatch.setattr(config.settings, "DATABASE_URL_SYNC", None)
    monkeypatch.setattr(config.settings, "DATABASE_URL", "postgresql+asyncpg://u@h/db")

    from backend.core.database import migration_url

    assert migration_url() == "postgresql+psycopg2://u@h/db"


def test_migration_url_names_the_variables_when_nothing_is_configured(monkeypatch):
    from backend.core import config

    monkeypatch.setattr(config.settings, "DATABASE_URL_SYNC", None)
    monkeypatch.setattr(config.settings, "DATABASE_URL", None)

    from backend.core.database import migration_url

    with pytest.raises(RuntimeError, match="DATABASE_URL_SYNC"):
        migration_url()
