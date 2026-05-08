import importlib.util
from pathlib import Path

import sqlalchemy
from sqlalchemy.dialects import postgresql

from src.models.db.occurrence import Occurrence
from src.repository.crud.base import BaseCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository


def test_occurrence_model_table_name() -> None:
    assert Occurrence.__tablename__ == "occurrences"


def test_occurrence_model_columns_present() -> None:
    table = Occurrence.__table__
    expected = {
        "id", "ddr_id", "ddr_date_id", "well_name", "surface_location",
        "type", "section", "mmd", "density", "notes", "date",
        "is_exported", "created_at", "updated_at",
    }
    assert set(table.c.keys()) == expected


def test_occurrence_model_column_types_and_nullability() -> None:
    table = Occurrence.__table__

    assert isinstance(table.c.id.type, postgresql.UUID)
    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    assert isinstance(table.c.ddr_id.type, postgresql.UUID)
    assert not table.c.ddr_id.nullable
    assert next(iter(table.c.ddr_id.foreign_keys)).target_fullname == "ddrs.id"

    assert isinstance(table.c.ddr_date_id.type, postgresql.UUID)
    assert not table.c.ddr_date_id.nullable
    assert next(iter(table.c.ddr_date_id.foreign_keys)).target_fullname == "ddr_dates.id"

    assert isinstance(table.c.type.type, sqlalchemy.String)
    assert table.c.type.type.length == 100
    assert not table.c.type.nullable

    assert isinstance(table.c.section.type, sqlalchemy.String)
    assert table.c.section.type.length == 20
    assert table.c.section.nullable

    assert isinstance(table.c.mmd.type, sqlalchemy.Float)
    assert table.c.mmd.nullable

    assert isinstance(table.c.density.type, sqlalchemy.Float)
    assert table.c.density.nullable

    assert isinstance(table.c.is_exported.type, sqlalchemy.Boolean)
    assert not table.c.is_exported.nullable
    assert str(table.c.is_exported.server_default.arg) == "false"

    assert isinstance(table.c.created_at.type, sqlalchemy.BigInteger)
    assert not table.c.created_at.nullable

    assert isinstance(table.c.updated_at.type, sqlalchemy.BigInteger)
    assert not table.c.updated_at.nullable

    assert table.c.well_name.nullable
    assert table.c.surface_location.nullable
    assert table.c.notes.nullable
    assert table.c.date.nullable


def test_occurrence_model_indexes_present() -> None:
    table = Occurrence.__table__
    index_names = {index.name for index in table.indexes}

    assert "idx_occurrences_ddr_id" in index_names
    assert "idx_occurrences_type" in index_names
    assert "idx_occurrences_date" in index_names


def test_occurrence_in_base_metadata() -> None:
    from src.repository.table import Base

    assert "occurrences" in Base.metadata.tables


def test_occurrence_repository_extends_base() -> None:
    assert issubclass(OccurrenceCRUDRepository, BaseCRUDRepository)
    assert OccurrenceCRUDRepository.model is Occurrence


_MIGRATION_003 = Path(__file__).parent.parent / "src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py"


def test_migration_003_occurrences_exists_and_chain() -> None:
    migration_file = _MIGRATION_003
    assert migration_file.exists()

    text = migration_file.read_text()
    assert 'revision = "003_occurrences"' in text
    assert 'down_revision = "002_ddr_schema"' in text
    assert '"occurrences"' in text
    assert 'op.create_index("idx_occurrences_ddr_id"' in text
    assert 'op.create_index("idx_occurrences_type"' in text
    assert 'op.create_index("idx_occurrences_date"' in text
    assert "if_not_exists=True" in text


def test_migration_003_upgrade_idempotent(monkeypatch) -> None:
    class FakeOps:
        def __init__(self):
            self.tables = []
            self.indexes = []

        def create_table(self, name, *columns, **kwargs):
            self.tables.append((name, kwargs))

        def create_index(self, name, table_name, columns, **kwargs):
            self.indexes.append((name, kwargs))

        def drop_table(self, name):
            pass

        def drop_index(self, name, **kwargs):
            pass

    path = _MIGRATION_003
    spec = importlib.util.spec_from_file_location("003_occurrences", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ops = FakeOps()
    monkeypatch.setattr(module, "op", ops)
    module.upgrade()

    assert all(kw.get("if_not_exists") is True for _, kw in ops.tables)
    assert all(kw.get("if_not_exists") is True for _, kw in ops.indexes)
