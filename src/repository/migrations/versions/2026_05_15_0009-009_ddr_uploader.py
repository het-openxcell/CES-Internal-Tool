import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_ddr_uploader"
down_revision = "008_occurrence_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ddrs",
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_ddrs_uploaded_by_user_id",
        "ddrs",
        "users",
        ["uploaded_by_user_id"],
        ["id"],
    )
    op.create_index("idx_ddrs_uploaded_by_user_id", "ddrs", ["uploaded_by_user_id"])
    op.execute("""
        UPDATE ddrs
        SET uploaded_by_user_id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1)
        WHERE uploaded_by_user_id IS NULL
          AND EXISTS (SELECT 1 FROM users)
    """)


def downgrade() -> None:
    op.drop_index("idx_ddrs_uploaded_by_user_id", table_name="ddrs")
    op.drop_constraint("fk_ddrs_uploaded_by_user_id", "ddrs", type_="foreignkey")
    op.drop_column("ddrs", "uploaded_by_user_id")
