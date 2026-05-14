import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008_occurrence_edits"
down_revision = "007_ddr_date_source_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "occurrence_edits",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("field", sa.String(50), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_occurrence_edits_ddr_id", "occurrence_edits", ["ddr_id"])
    op.create_index("idx_occurrence_edits_occurrence_id", "occurrence_edits", ["occurrence_id"])
    op.create_index("idx_occurrence_edits_created_at", "occurrence_edits", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_occurrence_edits_created_at", table_name="occurrence_edits")
    op.drop_index("idx_occurrence_edits_occurrence_id", table_name="occurrence_edits")
    op.drop_index("idx_occurrence_edits_ddr_id", table_name="occurrence_edits")
    op.drop_table("occurrence_edits")
