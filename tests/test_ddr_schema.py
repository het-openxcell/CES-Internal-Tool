import importlib.util
import inspect
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy.dialects import postgresql

from src.models.db.ddr import DDR, DDRDate, PipelineRun, ProcessingQueue
from src.models.schemas.ddr import DDRDateStatus, DDRInCreate, DDRStatus, DDRStatusUpdate, PipelineRunInCreate
from src.repository.crud.base import BaseCRUDRepository
from src.repository.crud.ddr import (
    DDRCRUDRepository,
    DDRDateCRUDRepository,
    PipelineRunCRUDRepository,
    ProcessingQueueCRUDRepository,
)


def test_ddr_models_match_table_contract() -> None:
    table = DDR.__table__

    assert table.name == "ddrs"
    assert isinstance(table.c.id.type, postgresql.UUID)
    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert isinstance(table.c.file_path.type, sqlalchemy.Text)
    assert not table.c.file_path.nullable
    assert isinstance(table.c.status.type, sqlalchemy.String)
    assert table.c.status.type.length == 20
    assert str(table.c.status.server_default.arg) == "'queued'"
    assert table.c.well_name.nullable
    assert isinstance(table.c.created_at.type, sqlalchemy.BigInteger)
    assert isinstance(table.c.updated_at.type, sqlalchemy.BigInteger)


def test_ddr_date_model_matches_table_contract() -> None:
    table = DDRDate.__table__

    assert table.name == "ddr_dates"
    assert set(table.c.keys()) == {
        "id",
        "ddr_id",
        "date",
        "status",
        "raw_response",
        "final_json",
        "error_log",
        "source_page_numbers",
        "created_at",
        "updated_at",
    }
    assert next(iter(table.c.ddr_id.foreign_keys)).target_fullname == "ddrs.id"
    assert isinstance(table.c.date.type, sqlalchemy.String)
    assert table.c.date.type.length == 8
    assert not table.c.date.nullable
    assert isinstance(table.c.raw_response.type, postgresql.JSONB)
    assert isinstance(table.c.final_json.type, postgresql.JSONB)
    assert isinstance(table.c.error_log.type, postgresql.JSONB)
    assert isinstance(table.c.source_page_numbers.type, postgresql.JSONB)
    assert table.c.source_page_numbers.nullable
    assert "idx_ddr_dates_ddr_id" in {index.name for index in table.indexes}


def test_processing_queue_and_pipeline_run_models_match_contract() -> None:
    queue_table = ProcessingQueue.__table__
    run_table = PipelineRun.__table__

    assert queue_table.name == "processing_queue"
    assert next(iter(queue_table.c.ddr_id.foreign_keys)).target_fullname == "ddrs.id"
    assert isinstance(queue_table.c.position.type, sqlalchemy.Integer)
    assert not queue_table.c.position.nullable
    assert "idx_processing_queue_ddr_id" in {index.name for index in queue_table.indexes}
    assert "uq_processing_queue_position" in {
        constraint.name for constraint in queue_table.constraints if isinstance(constraint, sqlalchemy.UniqueConstraint)
    }

    assert run_table.name == "pipeline_runs"
    assert next(iter(run_table.c.ddr_date_id.foreign_keys)).target_fullname == "ddr_dates.id"
    assert isinstance(run_table.c.gemini_input_tokens.type, sqlalchemy.Integer)
    assert isinstance(run_table.c.gemini_output_tokens.type, sqlalchemy.Integer)
    assert isinstance(run_table.c.cost_usd.type, sqlalchemy.Numeric)
    assert run_table.c.cost_usd.type.precision == 10
    assert run_table.c.cost_usd.type.scale == 6
    assert "decimal.Decimal" in str(PipelineRun.__annotations__["cost_usd"])
    assert isinstance(run_table.c.created_at.type, sqlalchemy.BigInteger)


def test_ddr_schemas_validate_status_values() -> None:
    assert DDRStatus.values() == ("queued", "processing", "complete", "failed")
    assert DDRDateStatus.values() == ("queued", "success", "warning", "failed")
    assert DDRInCreate(file_path="/tmp/ddr.pdf", status="queued").status == "queued"
    assert DDRStatusUpdate(status="processing").status == "processing"
    assert PipelineRunInCreate(
        ddr_date_id="11111111-1111-1111-1111-111111111111",
        gemini_input_tokens=10,
        gemini_output_tokens=20,
        cost_usd=Decimal("0.123456"),
    ).cost_usd == Decimal("0.123456")

    with pytest.raises(ValueError):
        DDRInCreate(file_path="/tmp/ddr.pdf", status="bad")

    with pytest.raises(ValueError):
        DDRStatusUpdate(status="success")


def test_ddr_repositories_extend_base_repository() -> None:
    assert issubclass(DDRCRUDRepository, BaseCRUDRepository)
    assert issubclass(DDRDateCRUDRepository, BaseCRUDRepository)
    assert issubclass(ProcessingQueueCRUDRepository, BaseCRUDRepository)
    assert issubclass(PipelineRunCRUDRepository, BaseCRUDRepository)
    assert DDRCRUDRepository.model is DDR
    assert DDRDateCRUDRepository.model is DDRDate
    assert ProcessingQueueCRUDRepository.model is ProcessingQueue
    assert PipelineRunCRUDRepository.model is PipelineRun
    assert (
        inspect.signature(PipelineRunCRUDRepository.create_pipeline_run).parameters["cost_usd"].annotation
        == Decimal | None
    )


def test_ddr_date_repository_reads_dates_in_ascending_order() -> None:
    statement_text = inspect.getsource(DDRDateCRUDRepository.read_dates_by_ddr_id)

    assert ".order_by(DDRDate.date.asc())" in statement_text


def test_migrations_include_users_baseline_and_ddr_schema() -> None:
    versions_dir = Path("src/repository/migrations/versions")
    user_migration = versions_dir / "2026_05_07_0001-001_users_schema.py"
    ddr_migration = versions_dir / "2026_05_07_0002-002_ddr_schema.py"

    assert user_migration.exists()
    assert ddr_migration.exists()

    user_text = user_migration.read_text()
    ddr_text = ddr_migration.read_text()

    assert 'revision = "001_users_schema"' in user_text
    assert 'down_revision = None' in user_text
    assert '"users"' in user_text
    assert 'revision = "002_ddr_schema"' in ddr_text
    assert 'down_revision = "001_users_schema"' in ddr_text
    assert '"ddrs"' in ddr_text
    assert '"ddr_dates"' in ddr_text
    assert '"processing_queue"' in ddr_text
    assert '"pipeline_runs"' in ddr_text
    assert 'op.create_index("idx_ddr_dates_ddr_id"' in ddr_text
    assert 'op.create_index("idx_processing_queue_ddr_id"' in ddr_text
    assert "if_not_exists=True" in user_text
    assert "if_not_exists=True" in ddr_text
    assert "uq_processing_queue_position" in ddr_text


def test_source_page_numbers_migration_exists() -> None:
    migration = Path("src/repository/migrations/versions/2026_05_14_0007-007_ddr_date_source_pages.py")
    text = migration.read_text()

    assert 'revision = "007_ddr_date_source_pages"' in text
    assert 'down_revision = "006_occurrence_page_number"' in text
    assert 'op.add_column("ddr_dates"' in text
    assert '"source_page_numbers"' in text
    assert 'op.drop_column("ddr_dates", "source_page_numbers")' in text


def test_startup_does_not_create_tables_outside_alembic() -> None:
    events_text = Path("src/repository/events.py").read_text()

    assert "Base.metadata.create_all" not in events_text


class FakeMigrationOperations:
    def __init__(self) -> None:
        self.tables = []
        self.indexes = []
        self.executed = []

    def create_table(self, name, *columns, **kwargs):
        self.tables.append((name, kwargs))

    def create_index(self, name, table_name, columns, **kwargs):
        self.indexes.append((name, table_name, columns, kwargs))

    def execute(self, statement):
        self.executed.append(statement)


def load_migration(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_upgrades_use_idempotent_operations(monkeypatch) -> None:
    versions_dir = Path("src/repository/migrations/versions")
    user_module = load_migration(versions_dir / "2026_05_07_0001-001_users_schema.py", "users_schema")
    ddr_module = load_migration(versions_dir / "2026_05_07_0002-002_ddr_schema.py", "ddr_schema")
    user_operations = FakeMigrationOperations()
    ddr_operations = FakeMigrationOperations()

    monkeypatch.setattr(user_module, "op", user_operations)
    monkeypatch.setattr(ddr_module, "op", ddr_operations)

    user_module.upgrade()
    ddr_module.upgrade()

    assert all(kwargs.get("if_not_exists") is True for _, kwargs in user_operations.tables)
    assert all(kwargs.get("if_not_exists") is True for _, kwargs in ddr_operations.tables)
    assert all(index[3].get("if_not_exists") is True for index in ddr_operations.indexes)
    assert any("uq_processing_queue_position" in statement for statement in ddr_operations.executed)


def test_docker_compose_declares_pdfs_volume() -> None:
    compose = Path("../docker-compose.yml").read_text()

    assert "\n  pdfs:" in compose
