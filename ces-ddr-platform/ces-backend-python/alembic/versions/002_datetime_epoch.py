from alembic import op


revision = "002_datetime_epoch"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


class DatetimeEpochMigration:
    def upgrade(self) -> None:
        op.execute(
            """
            ALTER TABLE users
                ALTER COLUMN created_at DROP DEFAULT,
                ALTER COLUMN updated_at DROP DEFAULT,
                ALTER COLUMN created_at TYPE BIGINT USING EXTRACT(EPOCH FROM created_at)::BIGINT,
                ALTER COLUMN updated_at TYPE BIGINT USING EXTRACT(EPOCH FROM updated_at)::BIGINT,
                ALTER COLUMN created_at SET DEFAULT EXTRACT(EPOCH FROM now())::BIGINT,
                ALTER COLUMN updated_at SET DEFAULT EXTRACT(EPOCH FROM now())::BIGINT
            """
        )

    def downgrade(self) -> None:
        op.execute(
            """
            ALTER TABLE users
                ALTER COLUMN created_at DROP DEFAULT,
                ALTER COLUMN updated_at DROP DEFAULT,
                ALTER COLUMN created_at TYPE TIMESTAMPTZ USING to_timestamp(created_at),
                ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING to_timestamp(updated_at),
                ALTER COLUMN created_at SET DEFAULT now(),
                ALTER COLUMN updated_at SET DEFAULT now()
            """
        )


def upgrade() -> None:
    DatetimeEpochMigration().upgrade()


def downgrade() -> None:
    DatetimeEpochMigration().downgrade()
