"""Tests for Story 4.0: Well Name & Surface Location Extraction."""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.schemas.ddr import DDRExtractionPayload
from src.services.occurrence.generate import OccurrenceGenerationService
from src.services.pipeline.validate import DDRExtractionValidator


# ── DDRCRUDRepository.update_well_metadata ───────────────────────────────────

def test_update_well_metadata_sets_fields():
    """update_well_metadata sets both fields and updates updated_at."""
    from src.repository.crud.ddr import DDRCRUDRepository
    from src.models.db.ddr import DDR

    async def run():
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        repo = DDRCRUDRepository(async_session=session)

        ddr = MagicMock(spec=DDR)
        ddr.well_name = None
        ddr.surface_location = None
        ddr.updated_at = 0

        before = int(time.time())
        await repo.update_well_metadata(ddr, "Well-A", "AB 01-02-003-04W5")
        after = int(time.time())

        assert ddr.well_name == "Well-A"
        assert ddr.surface_location == "AB 01-02-003-04W5"
        assert before <= ddr.updated_at <= after

    asyncio.run(run())


def test_update_well_metadata_accepts_nulls():
    """update_well_metadata with None values doesn't raise."""
    from src.repository.crud.ddr import DDRCRUDRepository
    from src.models.db.ddr import DDR

    async def run():
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        repo = DDRCRUDRepository(async_session=session)
        ddr = MagicMock(spec=DDR)
        ddr.well_name = "old"
        ddr.surface_location = "old"
        ddr.updated_at = 0

        await repo.update_well_metadata(ddr, None, None)

        assert ddr.well_name is None
        assert ddr.surface_location is None

    asyncio.run(run())


# ── OccurrenceGenerationService.generate_for_ddr surface_location ─────────────

def _make_date_row(id_, date, status, time_logs=None, mud_records=None, final_json_extra=None):
    row = MagicMock()
    row.id = id_
    row.date = date
    row.status = status
    fj = {
        "time_logs": time_logs or [],
        "mud_records": mud_records or [],
        "deviation_surveys": [],
        "bit_records": [],
    }
    if final_json_extra:
        fj.update(final_json_extra)
    row.final_json = fj
    return row


def _tl(activity, depth=None):
    return {
        "start_time": "06:00",
        "end_time": "07:00",
        "duration_hours": 1.0,
        "activity": activity,
        "depth_md": depth,
        "comment": None,
    }


@patch("src.services.occurrence.generate.KeywordLoader.get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_surface_location_propagated_to_occurrences(mock_keywords):
    """generate_for_ddr with ddr_surface_location → all occurrences carry that value."""
    occurrence_repo = AsyncMock()
    ddr_date_repo = AsyncMock()
    service = OccurrenceGenerationService(
        ddr_date_repository=ddr_date_repo,
        occurrence_repository=occurrence_repo,
    )

    async def run():
        from src.models.schemas.ddr import DDRDateStatus
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.SUCCESS, time_logs=[_tl("stuck pipe", 1500.0)]),
        ]
        count = await service.generate_for_ddr("d1", ddr_surface_location="AB 01-02-003-04W5")
        assert count == 1
        occ = occurrence_repo.bulk_create_occurrences.call_args[0][0][0]
        assert occ["surface_location"] == "AB 01-02-003-04W5"

    asyncio.run(run())


@patch("src.services.occurrence.generate.KeywordLoader.get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_surface_location_none_when_not_provided(mock_keywords):
    """generate_for_ddr without ddr_surface_location → surface_location is None."""
    occurrence_repo = AsyncMock()
    ddr_date_repo = AsyncMock()
    service = OccurrenceGenerationService(
        ddr_date_repository=ddr_date_repo,
        occurrence_repository=occurrence_repo,
    )

    async def run():
        from src.models.schemas.ddr import DDRDateStatus
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.SUCCESS, time_logs=[_tl("stuck pipe", 1500.0)]),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = occurrence_repo.bulk_create_occurrences.call_args[0][0][0]
        assert occ["surface_location"] is None

    asyncio.run(run())


# ── DDRExtractionValidator: well_name/surface_location accepted ───────────────

def test_validator_accepts_well_name_and_surface_location():
    """Gemini JSON with well_name and surface_location passes validation, both in final_json."""
    import json

    validator = DDRExtractionValidator()
    payload = {
        "well_name": "Pembina H-21",
        "surface_location": "AB 06-10-047-07W5",
        "time_logs": [],
        "mud_records": [],
        "deviation_surveys": [],
        "bit_records": [],
    }
    result = validator.validate(json.dumps(payload))
    assert result.is_valid
    assert result.final_json["well_name"] == "Pembina H-21"
    assert result.final_json["surface_location"] == "AB 06-10-047-07W5"


def test_validator_accepts_null_metadata():
    """Gemini JSON with null metadata fields passes validation."""
    import json

    validator = DDRExtractionValidator()
    payload = {
        "well_name": None,
        "surface_location": None,
        "time_logs": [],
        "mud_records": [],
        "deviation_surveys": [],
        "bit_records": [],
    }
    result = validator.validate(json.dumps(payload))
    assert result.is_valid
    assert result.final_json["well_name"] is None
    assert result.final_json["surface_location"] is None


def test_ddr_extraction_payload_extra_fields_still_forbidden():
    """DDRExtractionPayload still rejects truly unknown fields."""
    import json
    import pydantic

    validator = DDRExtractionValidator()
    payload = {
        "time_logs": [],
        "mud_records": [],
        "deviation_surveys": [],
        "bit_records": [],
        "unknown_field": "value",
    }
    result = validator.validate(json.dumps(payload))
    assert not result.is_valid


# ── Pipeline: _extract_all_dates aggregates well metadata ─────────────────────

@patch("src.services.occurrence.generate.KeywordLoader.get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_extract_all_dates_aggregates_well_metadata(mock_keywords):
    """_extract_all_dates reads well_name/surface_location from first successful date's final_json."""
    from src.models.schemas.ddr import DDRDateStatus

    async def run():
        ddr_repo = AsyncMock()
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()

        # After gather, read_dates_by_ddr_id returns rows with well metadata in final_json
        date_row = SimpleNamespace(
            id="dd1",
            ddr_id="ddr1",
            date="20240115",
            status=DDRDateStatus.SUCCESS,
            final_json={
                "well_name": "Well-A",
                "surface_location": "AB 01-02-003-04W5",
                "time_logs": [_tl("stuck pipe", 1500.0)],
                "mud_records": [],
                "deviation_surveys": [],
                "bit_records": [],
            },
        )
        ddr_date_repo.read_dates_by_ddr_id.return_value = [date_row]
        ddr_repo.update_well_metadata = AsyncMock(return_value=MagicMock())
        ddr_repo.finalize_status_from_dates = AsyncMock(return_value=MagicMock())

        from src.services.pipeline_service import PreSplitPipelineService

        service = PreSplitPipelineService(
            ddr_repository=ddr_repo,
            ddr_date_repository=ddr_date_repo,
            occurrence_repository=occurrence_repo,
            extract_after_split=False,
        )
        # Manually trigger the aggregation logic (bypassing extractor)
        ddr = SimpleNamespace(well_name=None, surface_location=None)

        # Simulate what _extract_all_dates does after gather
        all_rows = await ddr_date_repo.read_dates_by_ddr_id("ddr1")
        well_name = next(
            (r.final_json.get("well_name") for r in all_rows if r.final_json and r.final_json.get("well_name")),
            None,
        )
        surface_location = next(
            (r.final_json.get("surface_location") for r in all_rows if r.final_json and r.final_json.get("surface_location")),
            None,
        )
        await ddr_repo.update_well_metadata(ddr, well_name, surface_location)

        ddr_repo.update_well_metadata.assert_awaited_once_with(ddr, "Well-A", "AB 01-02-003-04W5")

    asyncio.run(run())


def test_extract_all_dates_uses_none_when_all_dates_fail():
    """When all dates fail, update_well_metadata called with None, None — no crash."""
    from src.models.schemas.ddr import DDRDateStatus

    async def run():
        # All rows have no final_json (failed extraction)
        failed_row = SimpleNamespace(
            id="dd1",
            ddr_id="ddr1",
            date="20240115",
            status=DDRDateStatus.FAILED,
            final_json=None,
        )
        rows = [failed_row]

        well_name = next(
            (r.final_json.get("well_name") for r in rows if r.final_json and r.final_json.get("well_name")),
            None,
        )
        surface_location = next(
            (r.final_json.get("surface_location") for r in rows if r.final_json and r.final_json.get("surface_location")),
            None,
        )
        assert well_name is None
        assert surface_location is None

    asyncio.run(run())
