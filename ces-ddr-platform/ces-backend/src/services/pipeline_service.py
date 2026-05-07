import asyncio
from typing import Any, Awaitable, Callable

from src.config.manager import settings
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.services.pipeline.extract import (
    ExtractionError,
    GeminiDDRExtractor,
    RateLimitError,
)
from src.services.pipeline.pre_split import PDFPreSplitter, PreSplitResult
from src.services.pipeline.validate import DDRExtractionValidator


class PreSplitPipelineService:
    no_boundary_reason = "No date boundaries detected"
    no_boundary_placeholder_date = "00000000"

    def __init__(
        self,
        ddr_repository: Any,
        ddr_date_repository: Any,
        pre_splitter: PDFPreSplitter | None = None,
        pdf_loader: Callable[[str], Awaitable[bytes]] | None = None,
        extractor: GeminiDDRExtractor | None = None,
        validator: DDRExtractionValidator | None = None,
        max_concurrent: int | None = None,
        extract_after_split: bool = True,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.pre_splitter = pre_splitter or PDFPreSplitter()
        self.pdf_loader = pdf_loader or self._default_pdf_loader
        self.extractor = extractor
        self.validator = validator or DDRExtractionValidator()
        self.max_concurrent = max(1, max_concurrent or settings.GEMINI_EXTRACTION_MAX_CONCURRENT)
        self.extract_after_split = extract_after_split
        self._write_lock = asyncio.Lock()

    async def run(self, ddr_id: str) -> PreSplitResult:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        pdf_bytes = await self.pdf_loader(ddr.file_path)
        result = await self.pre_splitter.split_async(pdf_bytes)

        if not result.has_boundaries:
            await self.ddr_date_repository.create_failed_boundary(
                ddr_id=ddr_id,
                date=self.no_boundary_placeholder_date,
                reason=self.no_boundary_reason,
                raw_page_content=result.raw_text_preview,
                commit=False,
            )
            await self.ddr_repository.update_status(ddr, DDRStatus.FAILED, commit=False)
            await self._commit_outcome()
            return result

        ordered_dates = sorted(result.date_chunks.keys())
        await self.ddr_date_repository.bulk_create_queued(ddr_id=ddr_id, dates=ordered_dates, commit=False)
        await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING, commit=False)
        await self._commit_outcome()

        if self.extract_after_split:
            await self._extract_all_dates(ddr_id=ddr_id, ddr=ddr, date_chunks=result.date_chunks)
        return result

    async def _extract_all_dates(self, *, ddr_id: str, ddr: Any, date_chunks: dict[str, bytes]) -> None:
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        date_to_row = {row.date: row for row in rows if row.status == DDRDateStatus.QUEUED}
        if not date_to_row:
            await self.ddr_repository.finalize_status_from_dates(ddr, [])
            return

        extractor = self.extractor or GeminiDDRExtractor()
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_one(date: str, chunk_bytes: bytes) -> str:
            row = date_to_row.get(date)
            if row is None:
                return DDRDateStatus.FAILED
            async with semaphore:
                return await self._process_one_date(extractor, row, date, chunk_bytes)

        coroutines = [run_one(date, chunk) for date, chunk in date_chunks.items() if date in date_to_row]
        outcomes = await asyncio.gather(*coroutines, return_exceptions=True)

        final_statuses: list[str] = []
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                final_statuses.append(DDRDateStatus.FAILED)
            else:
                final_statuses.append(outcome)

        await self.ddr_repository.finalize_status_from_dates(ddr, final_statuses)

    async def _process_one_date(
        self,
        extractor: GeminiDDRExtractor,
        row: Any,
        date: str,
        chunk_bytes: bytes,
    ) -> str:
        try:
            extraction = await extractor.extract(date=date, pdf_bytes=chunk_bytes)
        except RateLimitError:
            async with self._write_lock:
                await self.ddr_date_repository.mark_warning(
                    row,
                    error_log={"code": "RATE_LIMITED"},
                )
            return DDRDateStatus.WARNING
        except ExtractionError as exc:
            async with self._write_lock:
                await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "EXTRACTION_FAILED", "detail": str(exc.detail)},
                )
            return DDRDateStatus.FAILED

        raw_response = {"text": extraction.text}
        try:
            validation = self.validator.validate(extraction.text)
            if validation.is_valid:
                async with self._write_lock:
                    await self.ddr_date_repository.mark_success(
                        row,
                        raw_response=raw_response,
                        final_json=validation.final_json,
                    )
                return DDRDateStatus.SUCCESS

            async with self._write_lock:
                await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "VALIDATION_FAILED", "errors": validation.errors},
                    raw_response=raw_response,
                )
        except Exception as exc:
            async with self._write_lock:
                await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "PROCESSING_FAILED", "detail": str(exc)},
                    raw_response=raw_response,
                )
        return DDRDateStatus.FAILED

    async def _default_pdf_loader(self, file_path: str) -> bytes:
        return await asyncio.to_thread(self._read_file_bytes, file_path)

    async def _commit_outcome(self) -> None:
        sessions = {
            id(session): session
            for session in (
                getattr(self.ddr_repository, "async_session", None),
                getattr(self.ddr_date_repository, "async_session", None),
            )
            if session is not None
        }
        for session in sessions.values():
            await session.commit()

    @staticmethod
    def _read_file_bytes(file_path: str) -> bytes:
        with open(file_path, "rb") as fh:
            return fh.read()


__all__ = ["PreSplitPipelineService"]
