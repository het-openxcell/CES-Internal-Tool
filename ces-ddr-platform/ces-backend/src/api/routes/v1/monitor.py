from fastapi import APIRouter, Depends, Query

from src.api.dependencies.repository import get_repository
from src.models.schemas.monitor import MonitorMetrics, OccurrenceEditResponse, QueueItemResponse
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.monitor import MonitorService

router = APIRouter(prefix="/monitor", tags=["Monitor"])


@router.get("/metrics", response_model=MonitorMetrics)
async def get_monitor_metrics(
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> MonitorMetrics:
    return await MonitorService(ddr_repository, ddr_date_repository, edit_repository).metrics()


@router.get("/queue", response_model=list[QueueItemResponse])
async def get_monitor_queue(
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> list[QueueItemResponse]:
    return await MonitorService(ddr_repository, ddr_date_repository, edit_repository).queue()


@router.get("/corrections", response_model=list[OccurrenceEditResponse])
async def get_monitor_corrections(
    field: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(jwt_authentication),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> list[OccurrenceEditResponse]:
    edits = await MonitorService(None, None, edit_repository).corrections(field, limit, offset)
    return [OccurrenceEditResponse.model_validate(e) for e in edits]
