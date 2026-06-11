import sqlalchemy as sa
from alembic import op

revision = "015_rename_occurrence_sections"
down_revision = "014_rename_username_to_email"
branch_labels = None
depends_on = None

_RENAMES = (("Surface", "Surface Hole"),)


_corrections = sa.table(
    "corrections",
    sa.column("field_name", sa.String),
    sa.column("original_value", sa.String),
    sa.column("corrected_value", sa.String),
)


def upgrade() -> None:
    occurrences = sa.table("occurrences", sa.column("section", sa.String))
    for old, new in _RENAMES:
        op.execute(occurrences.update().where(occurrences.c.section == old).values(section=new))
        op.execute(
            _corrections.update()
            .where(_corrections.c.field_name == "section", _corrections.c.original_value == old)
            .values(original_value=new)
        )
        op.execute(
            _corrections.update()
            .where(_corrections.c.field_name == "section", _corrections.c.corrected_value == old)
            .values(corrected_value=new)
        )


def downgrade() -> None:
    occurrences = sa.table("occurrences", sa.column("section", sa.String))
    for old, new in _RENAMES:
        op.execute(occurrences.update().where(occurrences.c.section == new).values(section=old))
        op.execute(
            _corrections.update()
            .where(_corrections.c.field_name == "section", _corrections.c.original_value == new)
            .values(original_value=old)
        )
        op.execute(
            _corrections.update()
            .where(_corrections.c.field_name == "section", _corrections.c.corrected_value == new)
            .values(corrected_value=old)
        )
