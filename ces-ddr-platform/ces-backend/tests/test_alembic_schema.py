from pathlib import Path

import tomllib

from alembic import command
from alembic.config import Config

from app.config import AppSettings
from app.migration_config import MigrationDatabaseUrl


ROOT = Path(__file__).resolve().parents[1]


def test_alembic_dependencies_are_declared() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = "\n".join(pyproject["project"]["dependencies"])

    assert "alembic" in dependencies
    assert "sqlalchemy" in dependencies
    assert "psycopg[binary]" in dependencies


def test_alembic_config_uses_app_settings_postgres_dsn() -> None:
    alembic_config = Config(str(ROOT / "alembic.ini"))
    settings = AppSettings()

    assert alembic_config.get_main_option("script_location") == "alembic"
    assert settings.postgres_dsn


def test_migration_database_url_uses_psycopg_driver() -> None:
    urls = {
        "postgresql://ces:pass@localhost:5432/ces_ddr": "postgresql+psycopg://ces:pass@localhost:5432/ces_ddr",
        "postgres://ces:pass@localhost:5432/ces_ddr": "postgresql+psycopg://ces:pass@localhost:5432/ces_ddr",
        "postgresql+psycopg://ces:pass@localhost:5432/ces_ddr": "postgresql+psycopg://ces:pass@localhost:5432/ces_ddr",
    }

    for source, expected in urls.items():
        assert MigrationDatabaseUrl(source).sqlalchemy_url() == expected


def test_alembic_migration_defines_users_schema() -> None:
    migration = (ROOT / "alembic" / "versions" / "001_initial_schema.py").read_text()
    epoch_migration = (ROOT / "alembic" / "versions" / "002_datetime_epoch.py").read_text()

    expected_fragments = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        "sa.Column(\"id\", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text(\"gen_random_uuid()\"))",
        "sa.Column(\"username\", sa.String(length=255), nullable=False)",
        "sa.Column(\"password_hash\", sa.Text(), nullable=False)",
        "sa.Column(\"created_at\", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text(\"now()\"))",
        "sa.Column(\"updated_at\", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text(\"now()\"))",
        "sa.UniqueConstraint(\"username\", name=\"users_username_key\")",
    ]

    for fragment in expected_fragments:
        assert fragment in migration

    assert "ALTER COLUMN created_at TYPE BIGINT USING EXTRACT(EPOCH FROM created_at)::BIGINT" in epoch_migration
    assert "ALTER COLUMN updated_at TYPE BIGINT USING EXTRACT(EPOCH FROM updated_at)::BIGINT" in epoch_migration


def test_alembic_upgrade_generates_canonical_users_schema_sql(capsys) -> None:
    alembic_config = Config(str(ROOT / "alembic.ini"))

    command.upgrade(alembic_config, "head", sql=True)
    generated_sql = capsys.readouterr().out

    expected_fragments = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        "CREATE TABLE IF NOT EXISTS users",
        "id UUID DEFAULT gen_random_uuid() NOT NULL",
        "username VARCHAR(255) NOT NULL",
        "password_hash TEXT NOT NULL",
        "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL",
        "updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL",
        "ALTER COLUMN created_at TYPE BIGINT USING EXTRACT(EPOCH FROM created_at)::BIGINT",
        "ALTER COLUMN updated_at TYPE BIGINT USING EXTRACT(EPOCH FROM updated_at)::BIGINT",
        "PRIMARY KEY (id)",
        "CONSTRAINT users_username_key UNIQUE (username)",
    ]

    for fragment in expected_fragments:
        assert fragment in generated_sql


def test_alembic_downgrade_generates_users_drop_sql(capsys) -> None:
    alembic_config = Config(str(ROOT / "alembic.ini"))

    command.downgrade(alembic_config, "001_initial_schema:base", sql=True)

    assert "DROP TABLE IF EXISTS users" in capsys.readouterr().out
