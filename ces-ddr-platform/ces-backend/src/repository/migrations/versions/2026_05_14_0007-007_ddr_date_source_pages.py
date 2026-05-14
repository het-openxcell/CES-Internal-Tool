import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007_ddr_date_source_pages"
down_revision = "006_occurrence_page_number"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ddr_dates", sa.Column("source_page_numbers", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("ddr_dates", "source_page_numbers")
