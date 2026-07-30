"""chart-core gate: connector identity + free-chart grant key

Revision ID: 0002_chart_gate_identity
Revises: 0001_dream_entries
Create Date: 2026-07-30

Two columns on `users`, both nullable so the migration applies to existing
rows without a backfill:

- `oauth_subject` — the external OAuth subject a connector (MCP) user
  authenticates as. A connector account is a User keyed on this, distinct
  from a password account, so the chart gate can meter the MCP transport by
  its principal. Unique + indexed: it is looked up on every gated MCP call
  and must not collide.
- `free_natal_chart_key` — the birth-instant identity of the ONE chart a
  free account was granted. Re-issuing that chart is free forever; a
  different one is refused. Null until the first chart is issued.

The `users` table itself is still created by `init_db()` on fresh databases
(see 0001's note); this migration only adds the two columns to an existing
one.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_chart_gate_identity"
down_revision = "0001_dream_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("oauth_subject", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_users_oauth_subject", "users", ["oauth_subject"], unique=True
    )
    op.add_column(
        "users",
        sa.Column("free_natal_chart_key", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "free_natal_chart_key")
    op.drop_index("ix_users_oauth_subject", table_name="users")
    op.drop_column("users", "oauth_subject")
