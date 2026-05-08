from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_occurrences"
down_revision = "002_ddr_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ddr_date_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("well_name", sa.Text(), nullable=True),
        sa.Column("surface_location", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("section", sa.String(length=20), nullable=True),
        sa.Column("mmd", sa.Float(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("date", sa.String(length=8), nullable=True),
        sa.Column("is_exported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ddr_date_id"], ["ddr_dates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("idx_occurrences_ddr_id", "occurrences", ["ddr_id"], if_not_exists=True)
    op.create_index("idx_occurrences_type", "occurrences", ["type"], if_not_exists=True)
    op.create_index("idx_occurrences_date", "occurrences", ["date"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_occurrences_date", table_name="occurrences")
    op.drop_index("idx_occurrences_type", table_name="occurrences")
    op.drop_index("idx_occurrences_ddr_id", table_name="occurrences")
    op.drop_table("occurrences")
