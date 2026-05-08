from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies.repository import get_repository
from src.models.schemas.ddr import DDRDateInResponse, DDRDetailResponse, DDRListItemResponse, DDRUploadResponse
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository, ProcessingQueueCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication, stream_query_token_authentication
from src.services.ddr import DDRProcessingTask, DDRUploadService
from src.services.processing_status import ProcessingStatusStreamService
from src.utilities.exceptions import EntityDoesNotExist

router = APIRouter(prefix="/ddrs", tags=["DDRs"])


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
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    processing_queue_repository: ProcessingQueueCRUDRepository = Depends(get_repository(ProcessingQueueCRUDRepository)),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRUploadResponse:
    processing_task = DDRProcessingTask(status_stream_service=status_stream_service)
    service = DDRUploadService(ddr_repository, processing_queue_repository, processing_task=processing_task)
    ddr = await service.upload(file)
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
