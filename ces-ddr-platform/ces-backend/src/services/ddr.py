import asyncio
import uuid
from pathlib import Path
from typing import Any, Callable

from fastapi import UploadFile

from src.config.manager import settings
from src.repository.crud.ddr import DDRCRUDRepository, DDRDateCRUDRepository
from src.services.pipeline_service import PreSplitPipelineService
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
    ) -> None:
        self._session_factory = session_factory
        self.pipeline_service_factory = pipeline_service_factory or self._default_pipeline_service_factory

    async def process(self, ddr_id: str) -> None:
        session_factory = self._session_factory or self._default_session_factory()
        async with session_factory() as session:
            try:
                service = self.pipeline_service_factory(session)
                await service.run(ddr_id)
            except Exception as exc:
                await session.rollback()
                await self._mark_failed(session, ddr_id)
                logger.error(f"DDR pre-split failed for {ddr_id}: {exc}")

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

    @staticmethod
    def _default_pipeline_service_factory(session: Any) -> PreSplitPipelineService:
        return PreSplitPipelineService(
            ddr_repository=DDRCRUDRepository(async_session=session),
            ddr_date_repository=DDRDateCRUDRepository(async_session=session),
        )


class DDRUploadService:
    accepted_content_types = frozenset({"application/pdf", "application/x-pdf"})
    pdf_header = b"%PDF-"
    chunk_size = 1024 * 1024

    def __init__(
        self,
        ddr_repository: Any,
        processing_queue_repository: Any,
        upload_dir: str | None = None,
        processing_task: DDRProcessingTask | None = None,
    ):
        self.ddr_repository = ddr_repository
        self.processing_queue_repository = processing_queue_repository
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.processing_task = processing_task or DDRProcessingTask()

    async def upload(self, file: UploadFile) -> Any:
        await self.validate_pdf(file)
        ddr_id = str(uuid.uuid4())
        file_path = self.upload_dir / f"{ddr_id}.pdf"

        try:
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await self.write_upload(file, file_path)
        except Exception:
            await self.remove_file(file_path)
            raise

        try:
            return await self.ddr_repository.create_queued_with_queue(
                ddr_id=ddr_id,
                file_path=str(file_path),
                processing_queue_repository=self.processing_queue_repository,
            )
        except Exception:
            await self.remove_file(file_path)
            raise

    async def validate_pdf(self, file: UploadFile) -> None:
        filename = file.filename or ""
        if file.content_type not in self.accepted_content_types or not filename.lower().endswith(".pdf"):
            raise DDRUploadValidationError()
        header = await file.read(len(self.pdf_header))
        await file.seek(0)
        if header != self.pdf_header:
            raise DDRUploadValidationError()

    async def write_upload(self, file: UploadFile, file_path: Path) -> None:
        await asyncio.to_thread(self.write_upload_chunks, file, file_path)

    def write_upload_chunks(self, file: UploadFile, file_path: Path) -> None:
        file.file.seek(0)
        with file_path.open("wb") as destination:
            while chunk := file.file.read(self.chunk_size):
                destination.write(chunk)

    async def remove_file(self, file_path: Path) -> None:
        if await asyncio.to_thread(file_path.exists):
            await asyncio.to_thread(file_path.unlink)

    async def dispatch_background(self, ddr_id: str) -> None:
        await self.processing_task.process(ddr_id)
