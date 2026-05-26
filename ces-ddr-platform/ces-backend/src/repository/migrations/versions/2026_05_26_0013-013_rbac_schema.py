import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "013_rbac_schema"
down_revision = "012_correction_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::BIGINT"), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::BIGINT"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_column("users", "is_active")
