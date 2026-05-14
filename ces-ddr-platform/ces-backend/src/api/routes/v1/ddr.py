from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Path, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies.repository import get_repository
from src.models.schemas.ddr import (
    DDRDateInResponse,
    DDRDetailResponse,
    DDRListItemResponse,
    DDRReprocessAcceptedResponse,
    DDRReprocessDatesRequest,
    DDRReprocessOccurrencesResponse,
    DDRUploadResponse,
)
from src.models.schemas.monitor import OccurrenceEditResponse, OccurrencePatchRequest
from src.models.schemas.occurrence import OccurrenceInResponse
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository, ProcessingQueueCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication, stream_query_token_authentication
from src.services.ddr import DDRProcessingTask, DDRReprocessService, DDRReprocessTask, DDRUploadService
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService
from src.services.storage_service import StorageService
from src.utilities.exceptions import EntityDoesNotExist

router = APIRouter(prefix="/ddrs", tags=["DDRs"])


def get_storage_service() -> StorageService:
    return StorageService()


def get_processing_status_stream_service(request: Request) -> ProcessingStatusStreamService:
    service = getattr(request.app.state, "processing_status_stream_service", None)
    if service is None:
        service = ProcessingStatusStreamService()
        request.app.state.processing_status_stream_service = service
    return service


@router.post("/upload", response_model=DDRUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_ddr(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    operator: str | None = None,
    area: str | None = None,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    processing_queue_repository: ProcessingQueueCRUDRepository = Depends(get_repository(ProcessingQueueCRUDRepository)),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRUploadResponse:
    storage_service = StorageService()
    processing_task = DDRProcessingTask(
        status_stream_service=status_stream_service,
        storage_service=storage_service,
    )
    service = DDRUploadService(
        ddr_repository,
        processing_queue_repository,
        storage_service=storage_service,
        processing_task=processing_task,
    )
    ddr = await service.upload(file, operator=operator, area=area)
    background_tasks.add_task(service.dispatch_background, ddr.id)
    return DDRUploadResponse(id=ddr.id, status=ddr.status)


@router.get("", response_model=list[DDRListItemResponse])
async def list_ddrs(
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
) -> list[DDRListItemResponse]:
    ddrs = await ddr_repository.read_all_descending()
    return [DDRListItemResponse.model_validate(ddr) for ddr in ddrs]


@router.get("/{ddr_id}/status/stream")
async def stream_ddr_status(
    ddr_id: str,
    request: Request,
    current_user = Depends(stream_query_token_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> StreamingResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "DDR not found", "code": "NOT_FOUND", "details": {}},
        )
    async def snapshot_events() -> list:
        current_ddr = await ddr_repository.read_by_id(ddr_id)
        if current_ddr is None:
            return []
        rows = list(await ddr_date_repository.read_dates_by_ddr_id(ddr_id))
        return status_stream_service.snapshot_events(current_ddr, rows)

    stream = status_stream_service.stream(ddr_id, request, send_open_frame=True, initial_events_factory=snapshot_events)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{ddr_id}/occurrences", response_model=list[OccurrenceInResponse])
async def get_ddr_occurrences(
    ddr_id: str,
    occurrence_type: Annotated[str | None, Query(alias="type")] = None,
    section: str | None = None,
    date_from: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    date_to: Annotated[str | None, Query(pattern=r"^\d{8}$")] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
) -> list[OccurrenceInResponse]:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        raise EntityDoesNotExist("ddr_not_found")
    occurrences = await occurrence_repository.get_by_ddr_id_filtered(
        ddr_id=ddr_id,
        type_filter=occurrence_type,
        section_filter=section,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [OccurrenceInResponse.model_validate(o) for o in occurrences]


@router.get("/{ddr_id}", response_model=DDRDetailResponse)
async def get_ddr(
    ddr_id: str,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
) -> DDRDetailResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        raise EntityDoesNotExist("ddr_not_found")
    rows = await ddr_date_repository.read_dates_by_ddr_id(ddr_id)
    return DDRDetailResponse(
        id=ddr.id,
        file_path=ddr.file_path,
        status=ddr.status,
        well_name=ddr.well_name,
        created_at=ddr.created_at,
        dates=[DDRDateInResponse.model_validate(row) for row in rows],
    )


@router.post("/{ddr_id}/dates/{date}/retry", response_model=DDRDateInResponse)
async def retry_ddr_date(
    ddr_id: str,
    date: Annotated[str, Path(pattern=r"^\d{8}$")],
    background_tasks: BackgroundTasks,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRDateInResponse:
    service = PreSplitPipelineService(
        ddr_repository=ddr_repository,
        ddr_date_repository=ddr_date_repository,
        occurrence_repository=occurrence_repository,
        storage_service=storage_service,
        status_stream_service=status_stream_service,
    )
    row = await service.prepare_retry(ddr_id, date)
    background_tasks.add_task(service.execute_retry, ddr_id, date)
    return DDRDateInResponse.model_validate(row)


@router.post(
    "/{ddr_id}/reprocess/full",
    response_model=DDRReprocessAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_full(
    ddr_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRReprocessAcceptedResponse:
    service = DDRReprocessService(ddr_repository, ddr_date_repository, occurrence_repository, storage_service)
    await service.prepare_full(ddr_id)
    task = DDRReprocessTask(status_stream_service=status_stream_service, storage_service=storage_service)
    background_tasks.add_task(task.full, ddr_id)
    return DDRReprocessAcceptedResponse(status="accepted", mode="full")


@router.post(
    "/{ddr_id}/reprocess/dates",
    response_model=DDRReprocessAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_dates(
    ddr_id: str,
    background_tasks: BackgroundTasks,
    payload: DDRReprocessDatesRequest = Body(default_factory=DDRReprocessDatesRequest),
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRReprocessAcceptedResponse:
    dates = payload.selected_dates()
    service = DDRReprocessService(ddr_repository, ddr_date_repository, occurrence_repository, storage_service)
    await service.prepare_dates(ddr_id, dates)
    task = DDRReprocessTask(status_stream_service=status_stream_service, storage_service=storage_service)
    background_tasks.add_task(task.dates, ddr_id, dates)
    return DDRReprocessAcceptedResponse(status="accepted", mode="dates", dates=dates)


@router.post("/{ddr_id}/reprocess/occurrences", response_model=DDRReprocessOccurrencesResponse)
async def reprocess_occurrences(
    ddr_id: str,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
) -> DDRReprocessOccurrencesResponse | JSONResponse:
    service = DDRReprocessService(ddr_repository, ddr_date_repository, occurrence_repository, storage_service)
    try:
        total = await service.regenerate_occurrences(ddr_id)
        return DDRReprocessOccurrencesResponse(status="success", mode="occurrences", total_occurrences=total)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=DDRReprocessOccurrencesResponse(
                status="failed",
                mode="occurrences",
                error=str(exc),
            ).model_dump(),
        )


@router.patch(
    "/{ddr_id}/occurrences/{occurrence_id}",
    response_model=OccurrenceEditResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_occurrence(
    ddr_id: str,
    occurrence_id: str,
    payload: OccurrencePatchRequest,
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> OccurrenceEditResponse:
    import time as _time

    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        raise EntityDoesNotExist("ddr_not_found")

    occurrence = await occurrence_repository.read_by_id(occurrence_id)
    if occurrence is None or occurrence.ddr_id != ddr_id:
        raise EntityDoesNotExist("occurrence_not_found")

    allowed_fields = {"type", "section", "mmd", "notes", "density"}
    if payload.field not in allowed_fields:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"field must be one of {sorted(allowed_fields)}")

    original_value = str(getattr(occurrence, payload.field, None) or "") or None

    await occurrence_repository.update(
        occurrence,
        {payload.field: payload.value, "updated_at": int(_time.time())},
    )

    username = getattr(current_user, "username", None) or getattr(current_user, "email", None)
    edit = await edit_repository.create_edit(
        occurrence_id=occurrence_id,
        ddr_id=ddr_id,
        field=payload.field,
        original_value=original_value,
        corrected_value=payload.value,
        reason=payload.reason,
        created_by=username,
    )
    return OccurrenceEditResponse.model_validate(edit)
