import sqlalchemy as sa
from alembic import op

revision = "004_well_metadata"
down_revision = "003_occurrences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ddrs", sa.Column("surface_location", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ddrs", "surface_location")
