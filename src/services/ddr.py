import asyncio
import time
import uuid
from typing import Any, Callable

from fastapi import HTTPException, UploadFile

from src.constants.storage import PDF_CONTENT_TYPES, PDF_HEADER, UPLOAD_CHUNK_SIZE_BYTES
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository, ProcessingQueueCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository
from src.services.pipeline_service import PreSplitPipelineService
from src.services.processing_status import ProcessingStatusStreamService
from src.services.storage_service import StorageService
from src.utilities.exceptions import BadRequestException, EntityDoesNotExist
from src.utilities.logging.logger import logger


class DDRUploadValidationError(BadRequestException):
    def __init__(self, detail: str = "only_pdf_files_accepted"):
        super().__init__(detail=detail)


class DDRPipelineTaskBase:
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

    def session_factory(self) -> Callable[[], Any]:
        return self._session_factory or self._default_session_factory()

    def pipeline_service(self, session: Any) -> PreSplitPipelineService:
        service = self.pipeline_service_factory(session)
        if self.status_stream_service is not None:
            service.status_stream_service = self.status_stream_service
        return service

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


class DDRProcessingTask(DDRPipelineTaskBase):
    async def process(self, ddr_id: str) -> None:
        session_factory = self.session_factory()
        async with session_factory() as session:
            processing_finished = False
            try:
                await self.pipeline_service(session).run(ddr_id)
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


class DDRReprocessTask(DDRPipelineTaskBase):
    async def full(self, ddr_id: str) -> None:
        await self._run(ddr_id, "full")

    async def dates(self, ddr_id: str, dates: list[str] | None) -> None:
        await self._run(ddr_id, "dates", dates)

    async def _run(self, ddr_id: str, mode: str, dates: list[str] | None = None) -> None:
        session_factory = self.session_factory()
        async with session_factory() as session:
            try:
                service = self.pipeline_service(session)
                if mode == "full":
                    await service.reprocess_full(ddr_id)
                else:
                    await service.reprocess_dates(ddr_id, dates)
            except Exception as exc:
                await session.rollback()
                await self._mark_failed(session, ddr_id)
                logger.error(f"DDR reprocess failed for {ddr_id}: {exc}")

    async def _mark_failed(self, session: Any, ddr_id: str) -> None:
        try:
            repository = DDRCRUDRepository(async_session=session)
            ddr = await repository.read_ddr_by_id(ddr_id)
            await repository.update_status(ddr, DDRStatus.FAILED)
        except Exception as exc:
            await session.rollback()
            logger.error(f"DDR reprocess failure finalization failed for {ddr_id}: {exc}")


class DDRReprocessService:
    def __init__(
        self,
        ddr_repository: Any,
        ddr_date_repository: Any,
        occurrence_repository: Any,
        storage_service: StorageService | None = None,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository
        self.storage_service = storage_service or StorageService()

    async def prepare_full(self, ddr_id: str) -> None:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)

    async def prepare_dates(self, ddr_id: str, dates: list[str] | None) -> None:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        target_dates = {row.date for row in rows} if dates is None else set(dates)
        target_rows = [row for row in rows if row.date in target_dates]
        if not target_rows:
            raise BadRequestException("date_not_found")
        for row in target_rows:
            await self.ddr_date_repository.update_status(row, DDRDateStatus.QUEUED)
        await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)

    async def regenerate_occurrences(self, ddr_id: str) -> int:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        service = PreSplitPipelineService(
            ddr_repository=self.ddr_repository,
            ddr_date_repository=self.ddr_date_repository,
            occurrence_repository=self.occurrence_repository,
            storage_service=self.storage_service,
            status_stream_service=None,
        )
        total = await service.regenerate_occurrences(ddr_id)
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = service.metadata_from_rows(rows)
        await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)
        return total


class OccurrenceCorrectionService:
    def __init__(
        self,
        ddr_repository: DDRCRUDRepository,
        occurrence_repository: OccurrenceCRUDRepository,
        edit_repository: OccurrenceEditCRUDRepository,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.occurrence_repository = occurrence_repository
        self.edit_repository = edit_repository
        self.allowed_fields = {"type", "section", "mmd", "notes", "density"}

    async def patch_occurrence(
        self,
        ddr_id: str,
        occurrence_id: str,
        field: str,
        value: str | None,
        reason: str | None,
        current_user: Any,
    ) -> Any:
        ddr = await self.ddr_repository.read_by_id(ddr_id)
        if ddr is None:
            raise EntityDoesNotExist("ddr_not_found")

        occurrence = await self.occurrence_repository.read_by_id(occurrence_id)
        if occurrence is None or occurrence.ddr_id != ddr_id:
            raise EntityDoesNotExist("occurrence_not_found")

        if field not in self.allowed_fields:
            raise HTTPException(status_code=422, detail=f"field must be one of {sorted(self.allowed_fields)}")

        original_value = str(getattr(occurrence, field, None) or "") or None
        await self.occurrence_repository.update(
            occurrence,
            {field: value, "updated_at": int(time.time())},
        )
        username = getattr(current_user, "username", None) or getattr(current_user, "email", None)
        return await self.edit_repository.create_edit(
            occurrence_id=occurrence_id,
            ddr_id=ddr_id,
            field=field,
            original_value=original_value,
            corrected_value=value,
            reason=reason,
            created_by=username,
        )


class DDRUploadService:
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

    async def upload(
        self,
        file: UploadFile,
        operator: str | None = None,
        area: str | None = None,
        user_id: str | None = None,
    ) -> Any:
        await self.validate_pdf(file)
        ddr_id = str(uuid.uuid4())
        data = await self.read_upload(file)
        await self.storage_service.upload_pdf(ddr_id, data)

        try:
            return await self.ddr_repository.create_queued_with_queue(
                ddr_id=ddr_id,
                file_path=file.filename or f"{ddr_id}.pdf",
                processing_queue_repository=self.processing_queue_repository,
                operator=operator,
                area=area,
                user_id=user_id,
            )
        except Exception:
            await self.storage_service.delete_ddr(ddr_id)
            raise

    async def validate_pdf(self, file: UploadFile) -> None:
        filename = file.filename or ""
        if file.content_type not in PDF_CONTENT_TYPES or not filename.lower().endswith(".pdf"):
            raise DDRUploadValidationError()
        header = await file.read(len(PDF_HEADER))
        await file.seek(0)
        if header != PDF_HEADER:
            raise DDRUploadValidationError()

    async def read_upload(self, file: UploadFile) -> bytes:
        return await asyncio.to_thread(self._read_upload_bytes, file)

    def _read_upload_bytes(self, file: UploadFile) -> bytes:
        file.file.seek(0)
        chunks: list[bytes] = []
        while chunk := file.file.read(UPLOAD_CHUNK_SIZE_BYTES):
            chunks.append(chunk)
        return b"".join(chunks)

    async def dispatch_background(self, ddr_id: str) -> None:
        await self.processing_task.process(ddr_id)
