import time
from decimal import Decimal
from typing import Any

import sqlalchemy

from src.constants.time import SECONDS_PER_WEEK
from src.models.db.ddr import DDR, DDRDate, PipelineRun
from src.models.db.occurrence import Occurrence
from src.models.schemas.monitor import MonitorMetrics, QueueItemResponse
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository


class MonitorService:
    def __init__(self, ddr_repository: Any, ddr_date_repository: Any, edit_repository: OccurrenceEditCRUDRepository):
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.edit_repository = edit_repository
        self.session = ddr_repository.async_session if ddr_repository is not None else None

    async def metrics(self) -> MonitorMetrics:
        now = int(time.time())
        week_start = now - SECONDS_PER_WEEK
        month_start = now - 30 * 24 * 3600
        ddrs_this_week = await self._count_ddrs_since(week_start)
        occurrences_extracted = await self._count_occurrences_since(week_start)
        ai_cost_weekly = await self._sum_pipeline_cost_since(week_start)
        failed_dates_count = await self._count_failed_dates()
        corrections_this_week = await self.edit_repository.count_since(week_start)
        avg_processing_seconds = await self._avg_processing_seconds_since(month_start)
        exports_this_week = await self._count_exports_since(week_start)
        uptime_month = await self._uptime_since(month_start)
        return MonitorMetrics(
            ddrs_this_week=ddrs_this_week,
            occurrences_extracted=occurrences_extracted,
            ai_cost_weekly=round(ai_cost_weekly, 4),
            failed_dates=failed_dates_count,
            corrections_this_week=corrections_this_week,
            avg_processing_seconds=avg_processing_seconds,
            exports_this_week=exports_this_week,
            uptime_month=uptime_month,
        )

    async def queue(self) -> list[QueueItemResponse]:
        ddrs = await self.ddr_repository.read_all_descending()
        result = []
        for ddr in ddrs:
            dates = await self.ddr_date_repository.read_dates_by_ddr_id(ddr.id)
            result.append(
                QueueItemResponse(
                    id=ddr.id,
                    file_path=ddr.file_path,
                    well_name=ddr.well_name,
                    operator=ddr.operator,
                    area=ddr.area,
                    status=ddr.status,
                    date_total=len(dates),
                    date_success=sum(1 for row in dates if row.status == "success"),
                    date_failed=sum(1 for row in dates if row.status == "failed"),
                    date_warning=sum(1 for row in dates if row.status == "warning"),
                    created_at=ddr.created_at,
                    updated_at=ddr.updated_at,
                )
            )
        return result

    async def corrections(self, field: str | None, limit: int, offset: int) -> list[Any]:
        return list(await self.edit_repository.list_all_descending(field_filter=field, limit=limit, offset=offset))

    async def _count_ddrs_since(self, since_ts: int) -> int:
        statement = sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(DDR.created_at >= since_ts)
        return await self._scalar_int(statement)

    async def _count_occurrences_since(self, since_ts: int) -> int:
        return await self._scalar_int(
            sqlalchemy.select(sqlalchemy.func.count(Occurrence.id)).where(Occurrence.created_at >= since_ts)
        )

    async def _sum_pipeline_cost_since(self, since_ts: int) -> float:
        result = await self.session.execute(
            sqlalchemy.select(sqlalchemy.func.coalesce(sqlalchemy.func.sum(PipelineRun.cost_usd), Decimal("0"))).where(
                PipelineRun.created_at >= since_ts
            )
        )
        return float(result.scalar_one() or 0)

    async def _count_failed_dates(self) -> int:
        statement = sqlalchemy.select(sqlalchemy.func.count(DDRDate.id)).where(DDRDate.status == "failed")
        return await self._scalar_int(statement)

    async def _avg_processing_seconds_since(self, since_ts: int) -> float:
        result = await self.session.execute(
            sqlalchemy.select(sqlalchemy.func.avg(DDR.updated_at - DDR.created_at)).where(
                DDR.status == "complete",
                DDR.created_at >= since_ts,
            )
        )
        return round(float(result.scalar_one() or 0), 1)

    async def _count_exports_since(self, since_ts: int) -> int:
        return await self._scalar_int(
            sqlalchemy.select(sqlalchemy.func.count(Occurrence.id)).where(
                Occurrence.is_exported.is_(True),
                Occurrence.updated_at >= since_ts,
            )
        )

    async def _uptime_since(self, since_ts: int) -> float:
        total_statement = sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(DDR.created_at >= since_ts)
        total = await self._scalar_int(total_statement)
        failed = await self._scalar_int(
            sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(DDR.status == "failed", DDR.created_at >= since_ts)
        )
        if total == 0:
            return 100.0
        return round(100.0 * (total - failed) / total, 1)

    async def _scalar_int(self, statement: Any) -> int:
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)
