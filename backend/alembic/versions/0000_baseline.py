"""baseline: the tables that were never in a migration

Revision ID: 0000_baseline
Revises:
Create Date: 2026-08-05

Until now NOTHING created the base tables — `users`, `subscriptions`,
`transactions`, `dream_usage`, `user_llm_keys`, `dreams` and friends. They
existed only because `init_db()` ran `Base.metadata.create_all`, which was
gated to development. Production therefore had no `users` table at all and the
entitlement gate raised `UndefinedTable` on every natal chart; migration 0001
assumed `users` existed (it references it by foreign key) and 0002 only ALTERed
it. This revision closes that hole: after it, a fresh database can be built by
`alembic upgrade head` alone.

Why it builds from `Base.metadata` rather than spelling the tables out: this is
a baseline for databases that ALREADY EXIST, created by `create_all` from these
very models. Re-declaring them by hand would risk describing something subtly
different from what production actually has, and there is no way to diff
against production from here. Deriving from the same metadata is the one form
guaranteed to agree with it. `checkfirst=True` makes it a no-op on every table
that is already there, so this is safe to run against production, a partially
built database, or an empty one.

Migrations after this one are ordinary hand-written DDL; the metadata import
belongs to the baseline only.
"""

from alembic import op

revision = "0000_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from backend.core.database import Base
    import backend.models  # noqa: F401 — registers every model on Base

    # checkfirst: create only what is missing, never touch what exists.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Deliberately not implemented. Downgrading a baseline means dropping every
    # table in the database, including whatever production data lives in them;
    # a migration must never be the thing that does that by accident.
    raise NotImplementedError(
        "The baseline cannot be downgraded — it would drop every table."
    )
