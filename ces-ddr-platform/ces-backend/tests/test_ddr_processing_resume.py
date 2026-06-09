import asyncio
import time
from types import SimpleNamespace
from typing import Any

from src.services.processing_resume import DDRProcessingResumeService


class StubDDRRepository:
    def __init__(self) -> None:
        self.by_status = {
            "queued": [SimpleNamespace(id="queued-1")],
            "processing": [SimpleNamespace(id="processing-1")],
        }

    async def read_ddrs_by_status(self, status: str) -> list[Any]:
        return self.by_status[status]


class StubQueueRepository:
    def __init__(self) -> None:
        self.rows = [
            SimpleNamespace(ddr_id="queued-1"),
            SimpleNamespace(ddr_id="processing-1"),
            SimpleNamespace(ddr_id="queued-1"),
        ]

    async def read_all_ordered(self) -> list[Any]:
        return list(self.rows)

    async def read_active_ordered(self) -> list[Any]:
        return list(self.rows)


class StubProcessingTask:
    def __init__(self) -> None:
        self.processed = []

    async def process(self, ddr_id: str) -> None:
        self.processed.append(ddr_id)


def test_resume_service_dispatches_queued_and_processing_once() -> None:
    async def run() -> None:
        task = StubProcessingTask()
        service = DDRProcessingResumeService(
            ddr_repository=StubDDRRepository(),
            processing_queue_repository=StubQueueRepository(),
            processing_task=task,
        )

        await service.resume()

        assert task.processed == ["queued-1", "processing-1"]

    asyncio.run(run())


class ReapStubDDRRepository:
    def __init__(self, ddrs: list[Any]) -> None:
        self.ddrs = ddrs
        self.failed: list[str] = []

    async def read_ddrs_by_status(self, status: str) -> list[Any]:
        return [ddr for ddr in self.ddrs if ddr.status == status]

    async def update_status(self, ddr: Any, status: str, commit: bool = True) -> Any:
        ddr.status = status
        self.failed.append(ddr.id)
        return ddr


class ReapStubQueueRepository:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def read_active_ordered(self) -> list[Any]:
        return []

    async def delete_by_ddr_id(self, ddr_id: str) -> None:
        self.deleted.append(ddr_id)


def test_resume_reaps_stuck_ddrs_and_skips_fresh_ones() -> None:
    async def run() -> None:
        now = int(time.time())
        ddr_repo = ReapStubDDRRepository(
            [
                SimpleNamespace(id="stuck-1", status="queued", updated_at=now - 99999),
                SimpleNamespace(id="fresh-1", status="processing", updated_at=now),
            ]
        )
        queue_repo = ReapStubQueueRepository()
        task = StubProcessingTask()
        service = DDRProcessingResumeService(
            ddr_repository=ddr_repo,
            processing_queue_repository=queue_repo,
            processing_task=task,
        )

        await service.resume()

        assert ddr_repo.failed == ["stuck-1"]
        assert queue_repo.deleted == ["stuck-1"]
        assert task.processed == ["fresh-1"]

    asyncio.run(run())


def test_resume_service_avoids_duplicate_concurrent_processing() -> None:
    async def run() -> None:
        task = StubProcessingTask()
        service = DDRProcessingResumeService(
            ddr_repository=StubDDRRepository(),
            processing_queue_repository=StubQueueRepository(),
            processing_task=task,
        )

        await asyncio.gather(service.resume(), service.resume())

        assert task.processed == ["queued-1", "processing-1"]

    asyncio.run(run())
