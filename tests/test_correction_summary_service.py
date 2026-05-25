import asyncio
from types import SimpleNamespace

from src.services.correction.summary import CorrectionSummaryService, EditSummaryResponse


class StubSummaryRepository:
    def __init__(self):
        self.calls = []

    async def upsert_date_summary(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(**kwargs)


class StubSummaryClient:
    def __init__(self, lines):
        self.lines = lines
        self.prompts = []

    async def generate_summary(self, prompt: str):
        self.prompts.append(prompt)
        return EditSummaryResponse(summary_lines=self.lines)


def make_date():
    return SimpleNamespace(
        id="date-1",
        ddr_id="ddr-1",
        date="20261207",
        final_json={
            "time_logs": [
                {
                    "start_time": "06:00",
                    "end_time": "07:00",
                    "depth_md": 2767,
                    "page_number": 65,
                    "activity": "Flow check after pit gain",
                    "comment": "Confirmed well flowing",
                }
            ]
        },
    )


def make_correction(field="type", before="Kick / Well Control", after="Lost Circulation", reason="pit gain with flow"):
    return SimpleNamespace(
        field_name=field,
        original_value=before,
        corrected_value=after,
        reason=reason,
        created_at=1700000000,
    )


def test_refresh_date_summary_upserts_guarded_llm_summary():
    async def run():
        repo = StubSummaryRepository()
        client = StubSummaryClient([
            "type: Kick / Well Control -> Lost Circulation when source logs mention pit gain "
            "and confirmed well flowing."
        ])
        service = CorrectionSummaryService(repo, client=client)

        await service.refresh_date_summary(make_date(), [make_correction()])

        assert len(repo.calls) == 1
        call = repo.calls[0]
        assert call["ddr_id"] == "ddr-1"
        assert call["ddr_date_id"] == "date-1"
        assert call["correction_count"] == 1
        assert "Kick / Well Control -> Lost Circulation" in call["summary"]
        assert call["source_logs"][0]["text"] == "Flow check after pit gain Confirmed well flowing"
        assert call["edit_details"][0]["field"] == "type"
        assert "Do not invent facts" in client.prompts[0]

    asyncio.run(run())


def test_ungrounded_llm_summary_falls_back_to_deterministic_summary():
    async def run():
        repo = StubSummaryRepository()
        client = StubSummaryClient(["This date has a broad operational learning."])
        service = CorrectionSummaryService(repo, client=client)

        await service.refresh_date_summary(make_date(), [make_correction()])

        summary = repo.calls[0]["summary"]
        assert "type: Kick / Well Control -> Lost Circulation" in summary
        assert "Apply when source logs support cues: pit gain, flow check, well flowing" in summary

    asyncio.run(run())


def test_multiple_edits_same_date_merge_into_one_summary_record():
    async def run():
        repo = StubSummaryRepository()
        service = CorrectionSummaryService(repo, client=None)
        service.resolve_client = lambda: None
        corrections = [
            make_correction(),
            make_correction("notes", "Gas detected at flare", "No gas noted", "log does not mention gas"),
        ]

        await service.refresh_date_summary(make_date(), corrections)

        assert len(repo.calls) == 1
        call = repo.calls[0]
        assert call["correction_count"] == 2
        assert len(call["summary"].split("\n")) == 3
        assert "type: Kick / Well Control -> Lost Circulation" in call["summary"]
        assert "notes: Gas detected at flare -> No gas noted" in call["summary"]

    asyncio.run(run())
