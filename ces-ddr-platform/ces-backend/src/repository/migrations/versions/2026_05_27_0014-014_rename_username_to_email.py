import sqlalchemy as sa
from alembic import op

revision = "014_rename_username_to_email"
down_revision = "013_rbac_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "username", new_column_name="email")


def downgrade() -> None:
    op.alter_column("users", "email", new_column_name="username")
