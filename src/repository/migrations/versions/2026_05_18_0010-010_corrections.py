import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "010_corrections"
down_revision = "009_ddr_uploader"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corrections",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::BIGINT"), nullable=False),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("idx_corrections_ddr_id", "corrections", ["ddr_id"], if_not_exists=True)
    op.create_index("idx_corrections_occurrence_id", "corrections", ["occurrence_id"], if_not_exists=True)
    op.create_index("idx_corrections_field_name_ddr_id", "corrections", ["field_name", "ddr_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_corrections_field_name_ddr_id", table_name="corrections")
    op.drop_index("idx_corrections_occurrence_id", table_name="corrections")
    op.drop_index("idx_corrections_ddr_id", table_name="corrections")
    op.drop_table("corrections")
