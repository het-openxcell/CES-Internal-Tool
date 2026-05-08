import asyncio
from typing import Any

from src.models.schemas.ddr import DDRStatus


class DDRProcessingResumeService:
    def __init__(
        self,
        ddr_repository: Any,
        processing_queue_repository: Any,
        processing_task: Any,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.processing_queue_repository = processing_queue_repository
        self.processing_task = processing_task
        self._active_ddr_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def resume(self) -> None:
        ddr_ids = await self._resumable_ddr_ids()
        tasks = []
        for ddr_id in ddr_ids:
            async with self._lock:
                if ddr_id in self._active_ddr_ids:
                    continue
                self._active_ddr_ids.add(ddr_id)
            tasks.append(self._process(ddr_id))
        if tasks:
            await asyncio.gather(*tasks)

    async def _process(self, ddr_id: str) -> None:
        try:
            await self.processing_task.process(ddr_id)
        finally:
            async with self._lock:
                self._active_ddr_ids.discard(ddr_id)

    async def _resumable_ddr_ids(self) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        queue_rows = await self.processing_queue_repository.read_active_ordered()
        for row in queue_rows:
            self._append_once(ordered, seen, row.ddr_id)
        for status in (DDRStatus.QUEUED, DDRStatus.PROCESSING):
            for ddr in await self.ddr_repository.read_ddrs_by_status(status):
                self._append_once(ordered, seen, ddr.id)
        return ordered

    def _append_once(self, ordered: list[str], seen: set[str], ddr_id: str) -> None:
        if ddr_id not in seen:
            ordered.append(ddr_id)
            seen.add(ddr_id)
