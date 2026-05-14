import sqlalchemy as sa
from alembic import op

revision = "005_operator_area"
down_revision = "004_well_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ddrs", sa.Column("operator", sa.Text(), nullable=True))
    op.add_column("ddrs", sa.Column("area", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ddrs", "area")
    op.drop_column("ddrs", "operator")
