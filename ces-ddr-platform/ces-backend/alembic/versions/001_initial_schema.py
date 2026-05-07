from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


class InitialSchemaMigration:
    def upgrade(self) -> None:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("username", name="users_username_key"),
            if_not_exists=True,
        )

    def downgrade(self) -> None:
        op.drop_table("users", if_exists=True)


def upgrade() -> None:
    InitialSchemaMigration().upgrade()


def downgrade() -> None:
    InitialSchemaMigration().downgrade()
