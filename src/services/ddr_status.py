from typing import Any

from src.services.processing_status import ProcessingStatusStreamService


class DDRStatusSnapshotFactory:
    def __init__(
        self,
        ddr_id: str,
        ddr_repository: Any,
        ddr_date_repository: Any,
        status_stream_service: ProcessingStatusStreamService,
    ) -> None:
        self.ddr_id = ddr_id
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.status_stream_service = status_stream_service

    async def events(self) -> list:
        ddr = await self.ddr_repository.read_by_id(self.ddr_id)
        if ddr is None:
            return []
        rows = list(await self.ddr_date_repository.read_dates_by_ddr_id(self.ddr_id))
        return self.status_stream_service.snapshot_events(ddr, rows)
