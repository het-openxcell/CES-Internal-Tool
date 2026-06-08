import sqlalchemy as sa
from alembic import op

revision = "015_rename_occurrence_sections"
down_revision = "014_rename_username_to_email"
branch_labels = None
depends_on = None

_RENAMES = (("Surface", "Surface Hole"),)


def upgrade() -> None:
    occurrences = sa.table("occurrences", sa.column("section", sa.String))
    for old, new in _RENAMES:
        op.execute(occurrences.update().where(occurrences.c.section == old).values(section=new))


def downgrade() -> None:
    occurrences = sa.table("occurrences", sa.column("section", sa.String))
    for old, new in _RENAMES:
        op.execute(occurrences.update().where(occurrences.c.section == new).values(section=old))
