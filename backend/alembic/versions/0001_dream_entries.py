"""dream_entries: personal dream series with coded HVdC features

Revision ID: 0001_dream_entries
Revises:
Create Date: 2026-07-27

First real migration in the repository. The rest of the schema is still
created by `init_db()` (Base.metadata.create_all) — the users table must
therefore exist before this migration runs on a fresh database (run the
app once, or baseline the full schema in a later migration). This one
covers only the new table so existing deployments can apply it without a
full schema baseline.

Privacy note: the table stores deterministic HVdC features and symbol
ids, never the dream text. Rows are erased with the user via the FK
cascade (GDPR Art. 17) and exported in the GDPR export (Art. 20).
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_dream_entries"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dream_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dream_date", sa.Date(), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("coder_version", sa.String(length=16), nullable=False),
        sa.Column("hvdc", sa.JSON(), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=True),
        sa.Column("primary_emotion", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_dream_entries_user_id", "dream_entries", ["user_id"])
    op.create_index("ix_dream_entries_dream_date", "dream_entries", ["dream_date"])


def downgrade() -> None:
    op.drop_index("ix_dream_entries_dream_date", table_name="dream_entries")
    op.drop_index("ix_dream_entries_user_id", table_name="dream_entries")
    op.drop_table("dream_entries")
