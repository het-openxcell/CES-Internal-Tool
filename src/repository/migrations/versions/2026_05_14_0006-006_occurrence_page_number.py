import sqlalchemy as sa
from alembic import op

revision = "006_occurrence_page_number"
down_revision = "005_operator_area"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("occurrences", sa.Column("page_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("occurrences", "page_number")
