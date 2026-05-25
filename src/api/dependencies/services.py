from fastapi import Depends, Request

from src.api.dependencies.repository import get_repository
from src.repository.crud.correction import CorrectionCRUDRepository
from src.repository.crud.correction_summary import CorrectionSummaryCRUDRepository
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.services.correction.review import CorrectionReviewService
from src.services.correction.summary import CorrectionSummaryService
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
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
    correction_summary_repository: CorrectionSummaryCRUDRepository = Depends(
        get_repository(CorrectionSummaryCRUDRepository)
    ),
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> PreSplitPipelineService:
    return PreSplitPipelineService(
        ddr_repository=ddr_repository,
        ddr_date_repository=ddr_date_repository,
        occurrence_repository=occurrence_repository,
        correction_repository=correction_repository,
        correction_summary_repository=correction_summary_repository,
        storage_service=storage_service,
        status_stream_service=status_stream_service,
    )


def get_ddr_reprocess_service(
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
    correction_summary_repository: CorrectionSummaryCRUDRepository = Depends(
        get_repository(CorrectionSummaryCRUDRepository)
    ),
    storage_service: StorageService = Depends(get_storage_service),
) -> DDRReprocessService:
    return DDRReprocessService(
        ddr_repository,
        ddr_date_repository,
        occurrence_repository,
        storage_service,
        correction_repository,
        correction_summary_repository,
    )


def get_ddr_reprocess_task(
    storage_service: StorageService = Depends(get_storage_service),
    status_stream_service: ProcessingStatusStreamService = Depends(get_processing_status_stream_service),
) -> DDRReprocessTask:
    return DDRReprocessTask(status_stream_service=status_stream_service, storage_service=storage_service)


def get_occurrence_correction_service(
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    ddr_date_repository: DDRDateCRUDRepository = Depends(get_repository(DDRDateCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
    correction_summary_repository: CorrectionSummaryCRUDRepository = Depends(
        get_repository(CorrectionSummaryCRUDRepository)
    ),
) -> OccurrenceCorrectionService:
    return OccurrenceCorrectionService(
        ddr_repository,
        occurrence_repository,
        correction_repository,
        ddr_date_repository,
        CorrectionSummaryService(correction_summary_repository),
    )


def get_correction_review_service(
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
    correction_summary_repository: CorrectionSummaryCRUDRepository = Depends(
        get_repository(CorrectionSummaryCRUDRepository)
    ),
) -> CorrectionReviewService:
    return CorrectionReviewService(correction_repository, correction_summary_repository)
