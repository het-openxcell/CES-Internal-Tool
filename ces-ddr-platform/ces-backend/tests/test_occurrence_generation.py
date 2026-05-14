import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.schemas.ddr import DDRDateStatus
from src.services.keywords.loader import KeywordLoader
from src.services.occurrence.generate import OccurrenceGenerationService


def _make_date_row(id_, date, status, time_logs=None, mud_records=None):
    row = MagicMock()
    row.id = id_
    row.date = date
    row.status = status
    row.final_json = {
        "time_logs": time_logs or [],
        "mud_records": mud_records or [],
        "deviation_surveys": [],
        "bit_records": [],
    }
    return row


def _tl(activity, depth=None, comment=None, page_number=None):
    return {
        "start_time": "06:00",
        "end_time": "07:00",
        "duration_hours": 1.0,
        "activity": activity,
        "depth_md": depth,
        "comment": comment,
        "page_number": page_number,
    }


def _mud(depth, weight):
    return {"depth_md": depth, "mud_weight": weight, "viscosity": None, "ph": None}


def _bulk_args(occurrence_repo):
    """Return the list of occurrence dicts passed to replace_for_ddr."""
    return occurrence_repo.replace_for_ddr.call_args[0][1]


@pytest.fixture
def occurrence_repo():
    return AsyncMock()


@pytest.fixture
def ddr_date_repo():
    return AsyncMock()


@pytest.fixture
def service(ddr_date_repo, occurrence_repo):
    return OccurrenceGenerationService(
        ddr_date_repository=ddr_date_repo,
        occurrence_repository=occurrence_repo,
    )


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe", "lost": "Lost Circulation"})
def test_skips_failed_date_rows(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.FAILED),
            _make_date_row("dd2", "20240116", DDRDateStatus.WARNING),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once_with("d1", [])
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        assert occurrence_repo.replace_for_ddr.call_args[0][1] == []

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_skips_unclassified_time_logs(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("normal drilling", 1000.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        assert occurrence_repo.replace_for_ddr.call_args[0][1] == []

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_classified_entry_creates_occurrence(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe at 1500", 1500.0)],
                mud_records=[_mud(1500.0, 12.5)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["ddr_id"] == "d1"
        assert occ["type"] == "Stuck Pipe"
        assert occ["mmd"] == 1500.0
        assert occ["section"] == "Int."
        assert occ["density"] == 12.5

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_occurrence_has_ddr_id_and_date(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["ddr_id"] == "d1"
        assert occ["date"] == "20240115"
        assert occ["ddr_date_id"] == "dd1"

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_well_name_propagated(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1", ddr_well_name="Well-A")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["well_name"] == "Well-A"

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_surface_location_none_when_not_supplied(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["surface_location"] is None

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_mmd_and_section_inferred(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["mmd"] == 500.0
        assert occ["section"] == "Surface"

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_density_from_mud_records(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0)],
                mud_records=[_mud(1400.0, 11.0), _mud(1500.0, 12.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["density"] == 12.0

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_empty_final_json_skipped(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        row = MagicMock()
        row.id = "dd1"
        row.date = "20240115"
        row.status = DDRDateStatus.SUCCESS
        row.final_json = None
        ddr_date_repo.read_dates_by_ddr_id.return_value = [row]
        count = await service.generate_for_ddr("d1")
        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        assert occurrence_repo.replace_for_ddr.call_args[0][1] == []

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_dedup_within_same_date(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[
                    _tl("stuck pipe", 1500.0),
                    _tl("stuck pipe again", 1500.0),
                ],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        assert len(_bulk_args(occurrence_repo)) == 1

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_same_type_mmd_different_dates_preserved(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0)],
            ),
            _make_date_row(
                "dd2",
                "20240116",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 2
        assert len(_bulk_args(occurrence_repo)) == 2

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_returns_count_of_inserted_occurrences(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_no_successful_dates_returns_zero(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.FAILED),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        assert occurrence_repo.replace_for_ddr.call_args[0][1] == []

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_notes_equals_text_used_for_classification(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0, comment="while drilling")],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["notes"] == "stuck pipe while drilling"

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_notes_is_none_when_activity_is_empty(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[
                    {
                        "start_time": "06:00",
                        "end_time": "07:00",
                        "duration_hours": 1.0,
                        "activity": "",
                        "comment": "",
                    }
                ],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once()
        assert occurrence_repo.replace_for_ddr.call_args[0][1] == []

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_custom_shoe_depths(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 400.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1", surface_shoe=500.0, intermediate_shoe=2000.0)
        assert count == 1
        occ = _bulk_args(occurrence_repo)[0]
        assert occ["section"] == "Surface"

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_invalid_shoe_depths_raises(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        with pytest.raises(ValueError, match="surface_shoe"):
            await service.generate_for_ddr("d1", surface_shoe=3000.0, intermediate_shoe=500.0)

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_non_dict_time_log_skipped(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=["not-a-dict", _tl("stuck pipe", 1500.0)],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 1
        occurrence_repo.replace_for_ddr.assert_awaited_once()

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe", "lost": "Lost Circulation"})
def test_multiple_time_logs_same_date(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[
                    _tl("stuck pipe", 1500.0),
                    _tl("lost circulation", 2000.0),
                ],
            ),
        ]
        count = await service.generate_for_ddr("d1")
        assert count == 2
        assert len(_bulk_args(occurrence_repo)) == 2

    asyncio.run(run())


@patch.object(KeywordLoader, "get_keywords", return_value={"stuck": "Stuck Pipe"})
def test_rerun_clears_existing_occurrences(mock_keywords, service, ddr_date_repo, occurrence_repo):
    async def run():
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("normal drilling", 1500.0)],
            ),
        ]
        await service.generate_for_ddr("ddr-x")
        occurrence_repo.replace_for_ddr.assert_awaited_once_with("ddr-x", [])

    asyncio.run(run())


def test_pipeline_service_generate_occurrences_returns_zero_when_no_repo():
    from src.services.pipeline_service import PreSplitPipelineService

    async def run():
        service = PreSplitPipelineService(
            ddr_repository=MagicMock(),
            ddr_date_repository=MagicMock(),
            occurrence_repository=None,
        )
        count = await service._generate_occurrences("d1", MagicMock())
        assert count == 0

    asyncio.run(run())


def test_llm_generation_allows_model_to_remove_previous_occurrences():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        occurrence_repo.get_by_ddr_id_filtered.return_value = [
            SimpleNamespace(date="20240115", type="Stuck Pipe", mmd=1500.0, notes="old")
        ]
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("normal drilling", 1500.0)],
            ),
        ]

        fake_llm_response = MagicMock()
        fake_llm_response.text = json.dumps({"occurrences": []})
        fake_models = MagicMock()
        fake_models.generate_content = AsyncMock(return_value=fake_llm_response)
        fake_aio = MagicMock()
        fake_aio.models = fake_models
        fake_client = MagicMock()
        fake_client.aio = fake_aio

        with patch("src.services.occurrence.llm_generate.genai.Client", return_value=fake_client):
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo)
            count = await service.generate_for_ddr("d1")

        assert count == 0
        occurrence_repo.replace_for_ddr.assert_awaited_once_with("d1", [])
        prompt = fake_models.generate_content.call_args.kwargs["contents"][0].text
        assert "Validate previous occurrences against current time logs" in prompt
        assert "Stuck Pipe" in prompt

    asyncio.run(run())


def test_llm_generation_derives_page_number_from_source_log_indexes():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        occurrence_repo.get_by_ddr_id_filtered.return_value = []
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0, page_number=5), _tl("worked pipe", 1510.0, page_number=6)],
            ),
        ]
        fake_llm_response = MagicMock()
        fake_llm_response.text = json.dumps({
            "occurrences": [
                {
                    "date": "20240115",
                    "type": "Stuck Pipe",
                    "mmd": 1500.0,
                    "notes": "stuck pipe",
                    "page_number": None,
                    "source_log_indexes": [1],
                }
            ]
        })
        fake_models = MagicMock()
        fake_models.generate_content = AsyncMock(return_value=fake_llm_response)
        fake_aio = MagicMock()
        fake_aio.models = fake_models
        fake_client = MagicMock()
        fake_client.aio = fake_aio

        with patch("src.services.occurrence.llm_generate.genai.Client", return_value=fake_client):
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo)
            count = await service.generate_for_ddr("d1")

        assert count == 1
        assert occurrence_repo.replace_for_ddr.call_args[0][1][0]["page_number"] == 6

    asyncio.run(run())


def test_llm_generation_source_log_indexes_match_original_time_log_positions():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        occurrence_repo.get_by_ddr_id_filtered.return_value = []
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=["bad-row", _tl("stuck pipe", 1500.0, page_number=7)],
            ),
        ]
        fake_llm_response = MagicMock()
        fake_llm_response.text = json.dumps({
            "occurrences": [
                {
                    "date": "20240115",
                    "type": "Stuck Pipe",
                    "mmd": 1500.0,
                    "notes": "stuck pipe",
                    "source_log_indexes": [1],
                }
            ]
        })
        fake_models = MagicMock()
        fake_models.generate_content = AsyncMock(return_value=fake_llm_response)
        fake_aio = MagicMock()
        fake_aio.models = fake_models
        fake_client = MagicMock()
        fake_client.aio = fake_aio

        with patch("src.services.occurrence.llm_generate.genai.Client", return_value=fake_client):
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo)
            await service.generate_for_ddr("d1")

        assert occurrence_repo.replace_for_ddr.call_args[0][1][0]["page_number"] == 7

    asyncio.run(run())


def test_llm_generation_rejects_page_number_not_in_source_logs():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        occurrence_repo.get_by_ddr_id_filtered.return_value = []
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0, page_number=5)],
            ),
        ]
        fake_llm_response = MagicMock()
        fake_llm_response.text = json.dumps({
            "occurrences": [
                {
                    "date": "20240115",
                    "type": "Stuck Pipe",
                    "mmd": 1500.0,
                    "notes": "stuck pipe",
                    "page_number": 99,
                }
            ]
        })
        fake_models = MagicMock()
        fake_models.generate_content = AsyncMock(return_value=fake_llm_response)
        fake_aio = MagicMock()
        fake_aio.models = fake_models
        fake_client = MagicMock()
        fake_client.aio = fake_aio

        with patch("src.services.occurrence.llm_generate.genai.Client", return_value=fake_client):
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo)
            await service.generate_for_ddr("d1")

        assert occurrence_repo.replace_for_ddr.call_args[0][1][0]["page_number"] is None

    asyncio.run(run())


def test_pipeline_service_generate_occurrences_runs_service():
    from src.services.pipeline_service import PreSplitPipelineService

    fake_response_json = json.dumps({
        "occurrences": [
            {"date": "20240115", "type": "Stuck Pipe", "mmd": 1500.0, "notes": "stuck pipe"},
        ]
    })

    async def run():
        ddr_repo = MagicMock()
        date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        occurrence_repo.get_by_ddr_id_filtered.return_value = []
        date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row(
                "dd1",
                "20240115",
                DDRDateStatus.SUCCESS,
                time_logs=[_tl("stuck pipe", 1500.0)],
            ),
        ]

        fake_llm_response = MagicMock()
        fake_llm_response.text = fake_response_json

        fake_models = MagicMock()
        fake_models.generate_content = AsyncMock(return_value=fake_llm_response)

        fake_aio = MagicMock()
        fake_aio.models = fake_models

        fake_client = MagicMock()
        fake_client.aio = fake_aio

        with patch("src.services.occurrence.llm_generate.genai.Client", return_value=fake_client):
            service = PreSplitPipelineService(
                ddr_repository=ddr_repo,
                ddr_date_repository=date_repo,
                occurrence_repository=occurrence_repo,
            )
            count = await service._generate_occurrences("d1", "Well-X", None)
        assert count == 1
        occurrence_repo.replace_for_ddr.assert_awaited_once()

    asyncio.run(run())
