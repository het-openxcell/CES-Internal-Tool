from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012_correction_summaries"
down_revision = "011_drop_occurrence_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("corrections", sa.Column("ddr_date_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key(
        "fk_corrections_ddr_date_id_ddr_dates",
        "corrections",
        "ddr_dates",
        ["ddr_date_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_corrections_ddr_date_id", "corrections", ["ddr_date_id"], if_not_exists=True)
    op.execute(
        """
        UPDATE corrections
        SET ddr_date_id = occurrences.ddr_date_id
        FROM occurrences
        WHERE corrections.occurrence_id = occurrences.id
          AND corrections.ddr_date_id IS NULL
        """
    )

    op.create_table(
        "correction_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ddr_date_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_logs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("edit_details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("correction_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::BIGINT"), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::BIGINT"), nullable=False),
        sa.ForeignKeyConstraint(["ddr_date_id"], ["ddr_dates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ddr_date_id", "scope", name="uq_correction_summaries_date_scope"),
    )
    op.create_index("idx_correction_summaries_ddr_id", "correction_summaries", ["ddr_id"], if_not_exists=True)
    op.create_index("idx_correction_summaries_ddr_date_id", "correction_summaries", ["ddr_date_id"], if_not_exists=True)
    op.create_index("idx_correction_summaries_scope", "correction_summaries", ["scope"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_correction_summaries_scope", table_name="correction_summaries")
    op.drop_index("idx_correction_summaries_ddr_date_id", table_name="correction_summaries")
    op.drop_index("idx_correction_summaries_ddr_id", table_name="correction_summaries")
    op.drop_table("correction_summaries")
    op.drop_index("idx_corrections_ddr_date_id", table_name="corrections")
    op.drop_constraint("fk_corrections_ddr_date_id_ddr_dates", "corrections", type_="foreignkey")
    op.drop_column("corrections", "ddr_date_id")
