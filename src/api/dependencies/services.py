from fastapi import Depends, Request

from src.api.dependencies.repository import get_repository
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository
from src.services.ddr import (
    DDRReprocessService,
    DDRReprocessTask,
    OccurrenceCorrectionService,
)
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService
from src.services.storage_service import StorageService


def get_storage_service() -> StorageService:
    return StorageService()


def get_processing_status_stream_service(request: Request) -> ProcessingStatusStreamService:
    return request.app.state.processing_status_stream_service


def get_pipeline_service(
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> PreSplitPipelineService:
    return PreSplitPipelineService(
        ddr_repository=ddr_repository,
        ddr_date_repository=ddr_date_repository,
        occurrence_repository=occurrence_repository,
        storage_service=storage_service,
        status_stream_service=status_stream_service,
    )


def get_ddr_reprocess_service(
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    storage_service: StorageService = Depends(get_storage_service),
) -> DDRReprocessService:
    return DDRReprocessService(ddr_repository, ddr_date_repository, occurrence_repository, storage_service)


def get_ddr_reprocess_task(
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRReprocessTask:
    return DDRReprocessTask(status_stream_service=status_stream_service, storage_service=storage_service)


def get_occurrence_correction_service(
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    edit_repository: OccurrenceEditCRUDRepository = Depends(get_repository(OccurrenceEditCRUDRepository)),
) -> OccurrenceCorrectionService:
    return OccurrenceCorrectionService(ddr_repository, occurrence_repository, edit_repository)
