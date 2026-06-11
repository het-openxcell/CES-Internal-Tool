import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from src.models.schemas.ddr import DDRStatus
from src.services.ddr import DDRCancellationService
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService
from src.utilities.exceptions import BadRequestException


class StubDDRRepository:
    def __init__(self, ddr: SimpleNamespace) -> None:
        self.async_session = None
        self.ddr = ddr
        self.status_updates: list[str] = []
        self.finalize_calls: list[list[str]] = []

    async def read_ddr_by_id(self, ddr_id: str) -> SimpleNamespace:
        return self.ddr

    async def read_status(self, ddr_id: str) -> str:
        return self.ddr.status

    async def update_status(self, ddr: SimpleNamespace, status: str, commit: bool = True) -> SimpleNamespace:
        ddr.status = status
        self.status_updates.append(status)
        return ddr

    async def update_well_metadata(self, ddr: Any, well_name: Any, surface_location: Any, commit: bool = True) -> Any:
        return ddr

    async def finalize_status_from_dates(self, ddr: Any, statuses: Any) -> Any:
        self.finalize_calls.append(list(statuses))
        return ddr


class StubQueueRepository:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete_by_ddr_id(self, ddr_id: str) -> None:
        self.deleted.append(ddr_id)


class StubDateRepository:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.async_session = None
        self.rows = rows
        self.failed: list[str] = []

    async def read_dates_by_ddr_id(self, ddr_id: str) -> list[SimpleNamespace]:
        return list(self.rows)

    async def update_status(self, row: SimpleNamespace, status: str) -> SimpleNamespace:
        row.status = status
        return row

    async def mark_failed_preserve(
        self,
        row: SimpleNamespace,
        error_log: dict,
        raw_response: dict | None = None,
        commit: bool = True,
    ) -> SimpleNamespace:
        self.failed.append(row.date)
        row.status = "failed"
        return row


class StubStreamService:
    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish_processing_complete(self, ddr_id: str, **kwargs: Any) -> None:
        self.published.append({"ddr_id": ddr_id, **kwargs})


def test_cancel_marks_ddr_cancelled_and_clears_queue() -> None:
    async def run() -> None:
        ddr = SimpleNamespace(id="d1", status=DDRStatus.PROCESSING)
        ddr_repo = StubDDRRepository(ddr)
        queue_repo = StubQueueRepository()
        stream = StubStreamService()
        service = DDRCancellationService(
            ddr_repository=ddr_repo,
            processing_queue_repository=queue_repo,
            ddr_date_repository=StubDateRepository([]),
            status_stream_service=stream,
        )

        result = await service.cancel("d1")

        assert result.status == DDRStatus.CANCELLED
        assert queue_repo.deleted == ["d1"]
        assert stream.published[0]["ddr_status"] == DDRStatus.CANCELLED

    asyncio.run(run())


def test_cancel_rejects_terminal_statuses() -> None:
    async def run() -> None:
        for status in (DDRStatus.COMPLETE, DDRStatus.FAILED, DDRStatus.CANCELLED):
            service = DDRCancellationService(
                ddr_repository=StubDDRRepository(SimpleNamespace(id="d1", status=status)),
                processing_queue_repository=StubQueueRepository(),
            )
            with pytest.raises(BadRequestException):
                await service.cancel("d1")

    asyncio.run(run())


def test_snapshot_emits_terminal_frame_for_cancelled_ddr() -> None:
    service = ProcessingStatusStreamService()
    ddr = SimpleNamespace(id="d1", status=DDRStatus.CANCELLED)
    events = service.snapshot_events(ddr, rows=[])

    assert events, "cancelled DDR must emit a terminal processing_complete frame"
    assert events[-1].name == "processing_complete"
    assert events[-1].payload.ddr_status == DDRStatus.CANCELLED


def test_reprocess_dates_skips_finalize_when_cancelled_mid_run() -> None:
    async def run() -> None:
        ddr = SimpleNamespace(id="d1", status=DDRStatus.COMPLETE)
        ddr_repo = StubDDRRepository(ddr)
        row = SimpleNamespace(ddr_id="d1", date="20240101", status="success", source_page_numbers=[1])
        date_repo = StubDateRepository([row])

        class CancellingStorage:
            async def download_chunk(self, ddr_id: str, date: str) -> bytes:
                ddr.status = DDRStatus.CANCELLED
                raise RuntimeError("storage interrupted by cancel")

        service = PreSplitPipelineService(
            ddr_repository=ddr_repo,
            ddr_date_repository=date_repo,
            storage_service=CancellingStorage(),
            extractor=object(),
            max_concurrent=1,
        )

        total = await service.reprocess_dates("d1", ["20240101"])

        assert total == 0
        assert ddr_repo.finalize_calls == []
        assert ddr.status == DDRStatus.CANCELLED

    asyncio.run(run())
