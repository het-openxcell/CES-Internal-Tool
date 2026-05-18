import importlib.util
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy
from sqlalchemy.dialects import postgresql

from src.models.db.correction import Correction
from src.models.schemas.correction import CorrectionInCreate, CorrectionInResponse
from src.repository.crud.base import BaseCRUDRepository
from src.repository.crud.correction import _MAX_LIMIT, CorrectionCRUDRepository


def test_correction_model_in_base_metadata() -> None:
    from src.repository.table import Base

    assert "corrections" in Base.metadata.tables


def test_correction_model_has_no_updated_at() -> None:
    assert not hasattr(Correction, "updated_at")
    assert "updated_at" not in Correction.__table__.c.keys()


def test_correction_model_columns_present() -> None:
    table = Correction.__table__
    expected = {
        "id", "occurrence_id", "ddr_id", "field_name",
        "original_value", "corrected_value", "reason", "user_id", "created_at",
    }
    assert set(table.c.keys()) == expected


def test_correction_model_column_types_and_nullability() -> None:
    table = Correction.__table__

    assert isinstance(table.c.id.type, postgresql.UUID)
    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    assert isinstance(table.c.occurrence_id.type, postgresql.UUID)
    assert not table.c.occurrence_id.nullable
    assert next(iter(table.c.occurrence_id.foreign_keys)).target_fullname == "occurrences.id"

    assert isinstance(table.c.ddr_id.type, postgresql.UUID)
    assert not table.c.ddr_id.nullable
    assert next(iter(table.c.ddr_id.foreign_keys)).target_fullname == "ddrs.id"

    assert isinstance(table.c.field_name.type, sqlalchemy.String)
    assert table.c.field_name.type.length == 100
    assert not table.c.field_name.nullable

    assert isinstance(table.c.original_value.type, sqlalchemy.Text)
    assert not table.c.original_value.nullable

    assert isinstance(table.c.corrected_value.type, sqlalchemy.Text)
    assert not table.c.corrected_value.nullable

    assert isinstance(table.c.reason.type, sqlalchemy.Text)
    assert not table.c.reason.nullable

    assert isinstance(table.c.user_id.type, postgresql.UUID)
    assert not table.c.user_id.nullable
    assert next(iter(table.c.user_id.foreign_keys)).target_fullname == "users.id"

    assert isinstance(table.c.created_at.type, sqlalchemy.BigInteger)
    assert not table.c.created_at.nullable
    assert table.c.created_at.server_default is not None
    assert "EPOCH" in str(table.c.created_at.server_default.arg)


def test_correction_model_fk_ondelete_rules() -> None:
    table = Correction.__table__

    occ_fk = next(iter(table.c.occurrence_id.foreign_keys))
    assert occ_fk.ondelete == "CASCADE"

    ddr_fk = next(iter(table.c.ddr_id.foreign_keys))
    assert ddr_fk.ondelete == "CASCADE"

    user_fk = next(iter(table.c.user_id.foreign_keys))
    assert user_fk.ondelete == "RESTRICT"


def test_correction_model_indexes_present() -> None:
    index_names = {index.name for index in Correction.__table__.indexes}
    assert "idx_corrections_ddr_id" in index_names
    assert "idx_corrections_occurrence_id" in index_names
    assert "idx_corrections_field_name_ddr_id" in index_names


def test_correction_repository_extends_base() -> None:
    assert issubclass(CorrectionCRUDRepository, BaseCRUDRepository)
    assert CorrectionCRUDRepository.model is Correction


_MIGRATION_010 = Path(__file__).parent.parent / "src/repository/migrations/versions/2026_05_18_0010-010_corrections.py"


def test_migration_010_corrections_chain() -> None:
    assert _MIGRATION_010.exists()

    text = _MIGRATION_010.read_text()
    assert 'revision = "010_corrections"' in text
    assert 'down_revision = "009_ddr_uploader"' in text
    assert '"corrections"' in text
    assert 'op.create_index("idx_corrections_ddr_id"' in text
    assert 'op.create_index("idx_corrections_occurrence_id"' in text
    assert 'op.create_index("idx_corrections_field_name_ddr_id"' in text
    assert "if_not_exists=True" in text
    assert 'ondelete="CASCADE"' in text
    assert 'ondelete="RESTRICT"' in text
    assert "EXTRACT(EPOCH FROM now())" in text


def test_migration_010_upgrade_idempotent(monkeypatch) -> None:
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

    spec = importlib.util.spec_from_file_location("010_corrections", _MIGRATION_010)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ops = FakeOps()
    monkeypatch.setattr(module, "op", ops)
    module.upgrade()

    assert all(kw.get("if_not_exists") is True for _, kw in ops.tables)
    assert all(kw.get("if_not_exists") is True for _, kw in ops.indexes)


def test_create_correction_calls_base_create() -> None:
    import asyncio

    mock_session = AsyncMock()
    repo = CorrectionCRUDRepository(async_session=mock_session)

    async def run() -> None:
        with patch.object(BaseCRUDRepository, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(spec=Correction)
            await repo.create_correction(
                occurrence_id="occ-1",
                ddr_id="ddr-1",
                field_name="type",
                original_value="old",
                corrected_value="new",
                reason="typo",
                user_id="user-1",
            )

            mock_create.assert_awaited_once()
            call_args = mock_create.call_args[0][0]
            assert call_args["occurrence_id"] == "occ-1"
            assert call_args["ddr_id"] == "ddr-1"
            assert call_args["field_name"] == "type"
            assert call_args["original_value"] == "old"
            assert call_args["corrected_value"] == "new"
            assert call_args["reason"] == "typo"
            assert call_args["user_id"] == "user-1"
            assert "created_at" not in call_args

    asyncio.run(run())


def test_get_all_filters_before_pagination() -> None:
    source = inspect.getsource(CorrectionCRUDRepository.get_all)
    where_pos = source.find(".where(")
    limit_pos = source.find(".limit(")
    assert where_pos < limit_pos, "filters must appear before .limit() in get_all"


def test_get_all_source_uses_field_name_column() -> None:
    source = inspect.getsource(CorrectionCRUDRepository.get_all)
    assert "field_name" in source
    assert "ddr_id" in source
    assert ".desc()" in source


def test_get_recent_uses_created_at_desc() -> None:
    source = inspect.getsource(CorrectionCRUDRepository.get_recent)
    assert "created_at" in source
    assert ".desc()" in source


def test_max_limit_cap_applied() -> None:
    source_all = inspect.getsource(CorrectionCRUDRepository.get_all)
    source_recent = inspect.getsource(CorrectionCRUDRepository.get_recent)
    source_by_ddr = inspect.getsource(CorrectionCRUDRepository.get_by_ddr_id)
    assert "_MAX_LIMIT" in source_all
    assert "_MAX_LIMIT" in source_recent
    assert "_MAX_LIMIT" in source_by_ddr
    assert _MAX_LIMIT == 500


def test_correction_in_create_schema() -> None:
    schema = CorrectionInCreate(
        occurrence_id="occ-1",
        field_name="type",
        original_value="old",
        corrected_value="new",
        reason="typo",
    )
    assert schema.occurrence_id == "occ-1"
    assert schema.field_name == "type"
    assert not hasattr(schema, "user_id"), "user_id must not be in CorrectionInCreate"
    assert not hasattr(schema, "ddr_id"), "ddr_id must not be in CorrectionInCreate"


def test_correction_in_create_rejects_empty_strings() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CorrectionInCreate(
            occurrence_id="occ-1",
            field_name="type",
            original_value="",
            corrected_value="new",
            reason="typo",
        )

    with pytest.raises(ValidationError):
        CorrectionInCreate(
            occurrence_id="occ-1",
            field_name="  ",
            original_value="old",
            corrected_value="new",
            reason="typo",
        )


def test_correction_in_response_schema_from_attributes() -> None:
    assert CorrectionInResponse.model_config.get("from_attributes") is True

    schema = CorrectionInResponse(
        id="id-1",
        occurrence_id="occ-1",
        ddr_id="ddr-1",
        field_name="type",
        original_value="old",
        corrected_value="new",
        reason="typo",
        user_id="user-1",
        created_at=1700000000,
    )
    assert schema.id == "id-1"
    assert schema.created_at == 1700000000


def test_correction_in_response_inherits_base_config() -> None:
    assert CorrectionInResponse.model_config.get("populate_by_name") is True
    assert CorrectionInResponse.model_config.get("validate_assignment") is True
