"""funnel_counters: anonymous conversion counters

Revision ID: 0003_funnel_counters
Revises: 0002_chart_gate_identity
Create Date: 2026-08-11

One table, four columns, no foreign keys — and the absence of foreign keys is
the design, not an omission. Nothing in this table refers to a person, a
session or a device, so there is nothing to join against and nothing to erase
on a deletion request. A row says "on this day, this event happened N times,
M of them from browsers that had been here before", and that is the whole of
what the product measures about its funnel.

The alternative was a third-party analytics script, which would have meant
sending visitor data to another company and adding a section to the privacy
policy. Four conversion ratios do not justify that, so the counters live here.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_funnel_counters"
down_revision = "0002_chart_gate_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Same guard as 0001/0002: on a database created by `create_all` from the
    # current models the table already exists, and this migration must be a
    # no-op there rather than an error on startup.
    inspector = sa.inspect(op.get_bind())
    if "funnel_counters" in inspector.get_table_names():
        return

    op.create_table(
        "funnel_counters",
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("returning_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event", "day"),
    )


def downgrade() -> None:
    op.drop_table("funnel_counters")
