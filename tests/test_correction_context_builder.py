import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.schemas.ddr import DDRDateStatus


def _make_correction(field_name, original_value, corrected_value, reason, created_at):
    return SimpleNamespace(
        field_name=field_name,
        original_value=original_value,
        corrected_value=corrected_value,
        reason=reason,
        created_at=created_at,
    )


def _make_date_row(id_, date, status, time_logs=None):
    row = MagicMock()
    row.id = id_
    row.date = date
    row.status = status
    row.final_json = {"time_logs": time_logs or [], "mud_records": [], "deviation_surveys": [], "bit_records": []}
    return row


def _tl(activity, depth=None):
    return {
        "start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0,
        "activity": activity, "depth_md": depth, "comment": None, "page_number": None,
    }


def test_build_cap_25_returns_only_20():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        corrections = [
            _make_correction(f"field_{i}", f"old_{i}", f"new_{i}", f"reason_{i}", 1000 - i)
            for i in range(25)
        ]
        repo = AsyncMock()
        repo.get_recent.return_value = corrections

        builder = CorrectionContextBuilder(repo)
        result = await builder.build()

        repo.get_recent.assert_awaited_once_with(20)
        lines = result.strip().split("\n")
        assert len(lines) == 20
        for i in range(20):
            assert f"field_{i}" in result
        for i in range(20, 25):
            assert f"field_{i}" not in result

    asyncio.run(run())


def test_build_grouping_count_and_format():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        corrections = [
            _make_correction("type", "Ream", "Back Ream", "newest reason", 1003),
            _make_correction("type", "Ream", "Back Ream", "middle reason", 1002),
            _make_correction("type", "Ream", "Back Ream", "oldest reason", 1001),
        ]
        repo = AsyncMock()
        repo.get_recent.return_value = corrections

        builder = CorrectionContextBuilder(repo)
        result = await builder.build()

        expected = "Field 'type': 'Ream' corrected to 'Back Ream' (3 times). Reason: newest reason"
        assert result == expected

    asyncio.run(run())


def test_build_empty_store_returns_empty_string():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        repo = AsyncMock()
        repo.get_recent.return_value = []

        builder = CorrectionContextBuilder(repo)
        result = await builder.build()

        assert result == ""

    asyncio.run(run())


def test_build_fewer_than_20_uses_all():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        corrections = [
            _make_correction("type", "Ream", "Back Ream", "r1", 1004),
            _make_correction("type", "Ream", "Back Ream", "r2", 1003),
            _make_correction("notes", "normal", "stuck", "r3", 1002),
            _make_correction("notes", "normal", "stuck", "r4", 1001),
        ]
        repo = AsyncMock()
        repo.get_recent.return_value = corrections

        builder = CorrectionContextBuilder(repo)
        result = await builder.build()

        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "'Back Ream' (2 times)" in lines[0]
        assert "'stuck' (2 times)" in lines[1]

    asyncio.run(run())


def test_build_defensive_slice_caps_even_if_repo_returns_more():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        corrections = [
            _make_correction(f"field_{i}", f"old_{i}", f"new_{i}", f"reason_{i}", 1000 - i)
            for i in range(30)
        ]
        repo = AsyncMock()
        repo.get_recent.return_value = corrections

        builder = CorrectionContextBuilder(repo)
        result = await builder.build()

        lines = result.strip().split("\n")
        assert len(lines) == 20

    asyncio.run(run())


def test_build_scopes_by_ddr_when_ddr_id_provided():
    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        corrections = [_make_correction("type", "Ream", "Back Ream", "human fixed it", 1001)]
        repo = AsyncMock()
        repo.get_by_ddr_id.return_value = corrections

        builder = CorrectionContextBuilder(repo)
        result = await builder.build(ddr_id="ddr-1")

        repo.get_by_ddr_id.assert_awaited_once_with("ddr-1", limit=20)
        repo.get_recent.assert_not_called()
        assert "Back Ream" in result

    asyncio.run(run())


def test_prompt_injection_with_correction_repository():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        correction_repo = AsyncMock()
        correction_repo.get_by_ddr_id.return_value = [
            _make_correction("type", "Ream", "Back Ream", "human fixed it", 1001),
        ]
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.SUCCESS, time_logs=[_tl("drilling", 1500.0)]),
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
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo, correction_repo)
            await service.generate_for_ddr("d1")

        prompt = fake_models.generate_content.call_args.kwargs["contents"][0].text
        assert "PREVIOUSLY CORRECTED" in prompt
        assert "Field 'type': 'Ream' corrected to 'Back Ream' (1 times). Reason: human fixed it" in prompt
        assert "VALID TYPES" in prompt
        assert "CURRENT TIME LOGS" in prompt
        correction_repo.get_by_ddr_id.assert_awaited_once_with("d1", limit=20)

    asyncio.run(run())


def test_prompt_generation_continues_when_correction_context_fails():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        correction_repo = AsyncMock()
        correction_repo.get_by_ddr_id.side_effect = RuntimeError("db unavailable")
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.SUCCESS, time_logs=[_tl("drilling", 1500.0)]),
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
            service = LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo, correction_repo)
            await service.generate_for_ddr("d1")

        prompt = fake_models.generate_content.call_args.kwargs["contents"][0].text
        assert "PREVIOUSLY CORRECTED" not in prompt
        assert "VALID TYPES" in prompt
        assert "CURRENT TIME LOGS" in prompt

    asyncio.run(run())


def test_no_correction_repo_prompt_has_no_correction_block():
    from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService

    async def run():
        ddr_date_repo = AsyncMock()
        occurrence_repo = AsyncMock()
        ddr_date_repo.read_dates_by_ddr_id.return_value = [
            _make_date_row("dd1", "20240115", DDRDateStatus.SUCCESS, time_logs=[_tl("drilling", 1500.0)]),
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
            await service.generate_for_ddr("d1")

        prompt = fake_models.generate_content.call_args.kwargs["contents"][0].text
        assert "PREVIOUSLY CORRECTED" not in prompt
        assert "VALID TYPES" in prompt
        assert "CURRENT TIME LOGS" in prompt

    asyncio.run(run())


def test_build_includes_date_scoped_summaries_and_recent_exact_corrections():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from src.services.correction.context_builder import CorrectionContextBuilder

    async def run():
        correction_repo = AsyncMock()
        summary_repo = AsyncMock()
        summary_repo.get_by_ddr_id.return_value = [
            SimpleNamespace(
                date="20261207",
                ddr_date_id="date-1",
                summary="type: Kick / Well Control -> Lost Circulation when source logs mention pit gain.",
            )
        ]
        correction_repo.get_by_ddr_id.return_value = [
            SimpleNamespace(
                field_name="type",
                original_value="Kick / Well Control",
                corrected_value="Lost Circulation",
                reason="pit gain with losses",
            )
        ]

        result = await CorrectionContextBuilder(correction_repo, summary_repo).build(ddr_id="ddr-1")

        assert "[20261207] type: Kick / Well Control -> Lost Circulation when source logs mention pit gain." in result
        assert "Field 'type': 'Kick / Well Control' corrected to 'Lost Circulation'" in result
        summary_repo.get_by_ddr_id.assert_awaited_once_with("ddr-1", limit=12)
        correction_repo.get_by_ddr_id.assert_awaited_once_with("ddr-1", limit=20)

    asyncio.run(run())
