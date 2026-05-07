from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_ddr_schema"
down_revision = "001_users_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ddrs",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("well_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_table(
        "ddr_dates",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("date", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("idx_ddr_dates_ddr_id", "ddr_dates", ["ddr_id"], if_not_exists=True)
    op.create_table(
        "processing_queue",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position", name="uq_processing_queue_position"),
        if_not_exists=True,
    )
    op.create_index("idx_processing_queue_ddr_id", "processing_queue", ["ddr_id"], if_not_exists=True)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_processing_queue_position'
            ) THEN
                ALTER TABLE processing_queue ADD CONSTRAINT uq_processing_queue_position UNIQUE (position);
            END IF;
        END
        $$;
        """
    )
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ddr_date_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("gemini_input_tokens", sa.Integer(), nullable=True),
        sa.Column("gemini_output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["ddr_date_id"], ["ddr_dates.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_index("idx_processing_queue_ddr_id", table_name="processing_queue")
    op.drop_table("processing_queue")
    op.drop_index("idx_ddr_dates_ddr_id", table_name="ddr_dates")
    op.drop_table("ddr_dates")
    op.drop_table("ddrs")
