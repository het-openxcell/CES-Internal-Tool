import asyncio
import uuid
from typing import Any, Callable

from fastapi import UploadFile

from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository, ProcessingQueueCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService
from src.services.storage_service import StorageService
from src.utilities.exceptions import BadRequestException
from src.utilities.logging.logger import logger


class DDRUploadValidationError(BadRequestException):
    def __init__(self, detail: str = "only_pdf_files_accepted"):
        super().__init__(detail=detail)


class DDRProcessingTask:
    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        pipeline_service_factory: Callable[[Any], PreSplitPipelineService] | None = None,
        status_stream_service: ProcessingStatusStreamService | None = None,
        storage_service: StorageService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self.status_stream_service = status_stream_service
        self.storage_service = storage_service or StorageService()
        self.pipeline_service_factory = pipeline_service_factory or self._default_pipeline_service_factory

    async def process(self, ddr_id: str) -> None:
        session_factory = self._session_factory or self._default_session_factory()
        async with session_factory() as session:
            processing_finished = False
            try:
                service = self.pipeline_service_factory(session)
                if self.status_stream_service is not None:
                    service.status_stream_service = self.status_stream_service
                await service.run(ddr_id)
                processing_finished = True
            except Exception as exc:
                await session.rollback()
                await self._mark_failed(session, ddr_id)
                processing_finished = True
                logger.error(f"DDR pre-split failed for {ddr_id}: {exc}")
            if processing_finished:
                await ProcessingQueueCRUDRepository(async_session=session).delete_by_ddr_id(ddr_id)

    async def _mark_failed(self, session: Any, ddr_id: str) -> None:
        try:
            repository = DDRCRUDRepository(async_session=session)
            ddr = await repository.read_ddr_by_id(ddr_id)
            await repository.update_status(ddr, "failed")
        except Exception as exc:
            await session.rollback()
            logger.error(f"DDR failure finalization failed for {ddr_id}: {exc}")

    @staticmethod
    def _default_session_factory() -> Callable[[], Any]:
        from src.repository.database import async_db

        return async_db.async_session_factory

    def _default_pipeline_service_factory(self, session: Any) -> PreSplitPipelineService:
        return PreSplitPipelineService(
            ddr_repository=DDRCRUDRepository(async_session=session),
            ddr_date_repository=DDRDateCRUDRepository(async_session=session),
            occurrence_repository=OccurrenceCRUDRepository(async_session=session),
            storage_service=self.storage_service,
        )


class DDRUploadService:
    accepted_content_types = frozenset({"application/pdf", "application/x-pdf"})
    pdf_header = b"%PDF-"
    chunk_size = 1024 * 1024

    def __init__(
        self,
        ddr_repository: Any,
        processing_queue_repository: Any,
        storage_service: StorageService | None = None,
        processing_task: DDRProcessingTask | None = None,
    ):
        self.ddr_repository = ddr_repository
        self.processing_queue_repository = processing_queue_repository
        self.storage_service = storage_service or StorageService()
        self.processing_task = processing_task or DDRProcessingTask(storage_service=self.storage_service)

    async def upload(self, file: UploadFile) -> Any:
        await self.validate_pdf(file)
        ddr_id = str(uuid.uuid4())
        data = await self.read_upload(file)
        await self.storage_service.upload_pdf(ddr_id, data)

        try:
            return await self.ddr_repository.create_queued_with_queue(
                ddr_id=ddr_id,
                file_path=file.filename or f"{ddr_id}.pdf",
                processing_queue_repository=self.processing_queue_repository,
            )
        except Exception:
            await self.storage_service.delete_ddr(ddr_id)
            raise

    async def validate_pdf(self, file: UploadFile) -> None:
        filename = file.filename or ""
        if file.content_type not in self.accepted_content_types or not filename.lower().endswith(".pdf"):
            raise DDRUploadValidationError()
        header = await file.read(len(self.pdf_header))
        await file.seek(0)
        if header != self.pdf_header:
            raise DDRUploadValidationError()

    async def read_upload(self, file: UploadFile) -> bytes:
        return await asyncio.to_thread(self._read_upload_bytes, file)

    def _read_upload_bytes(self, file: UploadFile) -> bytes:
        file.file.seek(0)
        chunks: list[bytes] = []
        while chunk := file.file.read(self.chunk_size):
            chunks.append(chunk)
        return b"".join(chunks)

    async def dispatch_background(self, ddr_id: str) -> None:
        await self.processing_task.process(ddr_id)
