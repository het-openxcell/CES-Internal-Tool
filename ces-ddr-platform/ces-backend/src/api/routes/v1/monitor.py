import time
from decimal import Decimal

import sqlalchemy
from fastapi import APIRouter, Depends, Query

from src.api.dependencies.repository import get_repository
from src.models.db.ddr import DDR, DDRDate, PipelineRun
from src.models.db.occurrence import Occurrence
from src.models.schemas.monitor import MonitorMetrics, OccurrenceEditResponse, QueueItemResponse
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication

router = APIRouter(prefix="/monitor", tags=["Monitor"])

_SECONDS_PER_WEEK = 7 * 24 * 3600


@router.get("/metrics", response_model=MonitorMetrics)
async def get_monitor_metrics(
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> MonitorMetrics:
    session = ddr_repository.async_session
    now = int(time.time())
    week_start = now - _SECONDS_PER_WEEK
    month_start = now - 30 * 24 * 3600

    # DDRs created this week
    ddrs_week = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(DDR.created_at >= week_start)
    )
    ddrs_this_week = int(ddrs_week.scalar_one() or 0)

    # Occurrences extracted this week
    occ_week = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(Occurrence.id)).where(Occurrence.created_at >= week_start)
    )
    occurrences_extracted = int(occ_week.scalar_one() or 0)

    # AI cost this week
    cost_week = await session.execute(
        sqlalchemy.select(sqlalchemy.func.coalesce(sqlalchemy.func.sum(PipelineRun.cost_usd), Decimal("0")))
        .where(PipelineRun.created_at >= week_start)
    )
    ai_cost_weekly = float(cost_week.scalar_one() or 0)

    # Failed date_dates (open)
    failed_dates = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(DDRDate.id)).where(DDRDate.status == "failed")
    )
    failed_dates_count = int(failed_dates.scalar_one() or 0)

    # Corrections this week
    corrections_this_week = await edit_repository.count_since(week_start)

    # Avg processing = avg(updated_at - created_at) for complete DDRs in last 30 days
    avg_time = await session.execute(
        sqlalchemy.select(
            sqlalchemy.func.avg(DDR.updated_at - DDR.created_at)
        ).where(DDR.status == "complete", DDR.created_at >= month_start)
    )
    avg_processing_seconds = round(float(avg_time.scalar_one() or 0), 1)

    # Exports this week (occurrences marked exported)
    exports_week = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(Occurrence.id)).where(
            Occurrence.is_exported.is_(True),
            Occurrence.updated_at >= week_start,
        )
    )
    exports_this_week = int(exports_week.scalar_one() or 0)

    # Uptime: % of DDRs in the last 30 days that completed (not failed)
    total_month = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(DDR.created_at >= month_start)
    )
    total_month_count = int(total_month.scalar_one() or 0)
    failed_month = await session.execute(
        sqlalchemy.select(sqlalchemy.func.count(DDR.id)).where(
            DDR.status == "failed", DDR.created_at >= month_start
        )
    )
    failed_month_count = int(failed_month.scalar_one() or 0)
    if total_month_count > 0:
        uptime_month = round(100.0 * (total_month_count - failed_month_count) / total_month_count, 1)
    else:
        uptime_month = 100.0

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


@router.get("/queue", response_model=list[QueueItemResponse])
async def get_monitor_queue(
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
) -> list[QueueItemResponse]:
    session = ddr_repository.async_session
    ddrs = await ddr_repository.read_all_descending()

    result = []
    for ddr in ddrs:
        dates = await ddr_date_repository.read_dates_by_ddr_id(ddr.id)
        date_total = len(dates)
        date_success = sum(1 for d in dates if d.status == "success")
        date_failed = sum(1 for d in dates if d.status == "failed")
        date_warning = sum(1 for d in dates if d.status == "warning")

        # Compute live date progress for processing DDRs
        result.append(
            QueueItemResponse(
                id=ddr.id,
                file_path=ddr.file_path,
                well_name=ddr.well_name,
                operator=ddr.operator,
                area=ddr.area,
                status=ddr.status,
                date_total=date_total,
                date_success=date_success,
                date_failed=date_failed,
                date_warning=date_warning,
                created_at=ddr.created_at,
                updated_at=ddr.updated_at,
            )
        )
    return result


@router.get("/corrections", response_model=list[OccurrenceEditResponse])
async def get_monitor_corrections(
    field: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(jwt_authentication),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> list[OccurrenceEditResponse]:
    edits = await edit_repository.list_all_descending(field_filter=field, limit=limit, offset=offset)
    return [OccurrenceEditResponse.model_validate(e) for e in edits]
