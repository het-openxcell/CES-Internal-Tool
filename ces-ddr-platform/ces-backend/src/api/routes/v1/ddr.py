from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, status

from src.api.dependencies.repository import get_repository
from src.models.schemas.ddr import DDRDetailResponse, DDRListItemResponse, DDRUploadResponse
from src.repository.crud.ddr import DDRCRUDRepository, ProcessingQueueCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.ddr import DDRUploadService
from src.utilities.exceptions import EntityDoesNotExist

router = APIRouter(prefix="/ddrs", tags=["DDRs"])


@router.post("/upload", response_model=DDRUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_ddr(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    processing_queue_repository: ProcessingQueueCRUDRepository = Depends(get_repository(ProcessingQueueCRUDRepository)),
) -> DDRUploadResponse:
    service = DDRUploadService(ddr_repository, processing_queue_repository)
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


@router.get("/{ddr_id}", response_model=DDRDetailResponse)
async def get_ddr(
    ddr_id: str,
    current_user = Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
) -> DDRDetailResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        raise EntityDoesNotExist("ddr_not_found")
    return DDRDetailResponse.model_validate(ddr)
