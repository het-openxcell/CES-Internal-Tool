import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from src.config.manager import settings


class DDRUploadValidationError(Exception):
    def __init__(self, detail: str = "Only PDF files accepted"):
        self.detail = detail
        super().__init__(detail)


class DDRProcessingTask:
    async def process(self, ddr_id: str) -> None:
        return None


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
