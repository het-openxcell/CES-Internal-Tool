import asyncio
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

from src.config.manager import settings
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.repository.crud.ddr import PipelineRunCRUDRepository
from src.services.occurrence.generate import OccurrenceGenerationService
from src.services.pipeline.cost import ExtractionCostService
from src.services.pipeline.embedding import TimeLogEmbeddingService
from src.services.pipeline.extract import (
    ExtractionError,
    GeminiDDRExtractor,
    RateLimitError,
)
from src.services.pipeline.pre_split import PDFPreSplitter, PreSplitResult
from src.services.pipeline.validate import DDRExtractionValidator
from src.services.processing_status import ProcessingStatusStreamService


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
        status_stream_service: ProcessingStatusStreamService | None = None,
        cost_service: ExtractionCostService | None = None,
        embedding_service: TimeLogEmbeddingService | None = None,
        occurrence_repository: Any | None = None,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository
        self.pre_splitter = pre_splitter or PDFPreSplitter()
        self.pdf_loader = pdf_loader or self._default_pdf_loader
        self.extractor = extractor
        self.validator = validator or DDRExtractionValidator()
        self.max_concurrent = max(1, max_concurrent or settings.GEMINI_EXTRACTION_MAX_CONCURRENT)
        self.extract_after_split = extract_after_split
        self.status_stream_service = status_stream_service
        self.cost_service = cost_service
        self.embedding_service = embedding_service
        self._write_lock = asyncio.Lock()

    async def run(self, ddr_id: str) -> PreSplitResult:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        pdf_bytes = await self.pdf_loader(ddr.file_path)
        result = await self.pre_splitter.split_async(pdf_bytes)

        if not result.has_boundaries:
            failed_row = await self.ddr_date_repository.create_failed_boundary(
                ddr_id=ddr_id,
                date=self.no_boundary_placeholder_date,
                reason=self.no_boundary_reason,
                raw_page_content=result.raw_text_preview,
                commit=False,
            )
            await self.ddr_repository.update_status(ddr, DDRStatus.FAILED, commit=False)
            await self._commit_outcome()
            await self._publish_date_failed(failed_row)
            await self._publish_processing_complete(ddr_id)
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
            await self._publish_processing_complete(ddr_id)
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

        try:
            total_occurrences = await self._generate_occurrences(ddr_id=ddr_id, ddr=ddr)
        except Exception:  # noqa: BLE001
            total_occurrences = 0
        await self.ddr_repository.finalize_status_from_dates(ddr, final_statuses)
        await self._publish_processing_complete(ddr_id, total_occurrences=total_occurrences)

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
                updated_row = await self.ddr_date_repository.mark_warning(
                    row,
                    error_log={"code": "RATE_LIMITED"},
                )
                await self._publish_date_complete(updated_row)
            return DDRDateStatus.WARNING
        except ExtractionError as exc:
            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "EXTRACTION_FAILED", "detail": str(exc.detail)},
                )
                await self._publish_date_failed(updated_row)
            return DDRDateStatus.FAILED

        raw_response = {"text": extraction.text}
        try:
            validation = self.validator.validate(extraction.text)
            if validation.is_valid:
                async with self._write_lock:
                    cost_service = self._resolve_cost_service()
                    updated_row = await self.ddr_date_repository.mark_success(
                        row,
                        raw_response=raw_response,
                        final_json=validation.final_json,
                        commit=False,
                    )
                    await cost_service.record_extraction_run(
                        ddr_date_id=updated_row.id,
                        input_tokens=extraction.input_tokens,
                        output_tokens=extraction.output_tokens,
                        commit=False,
                    )
                    snapshot = SimpleNamespace(
                        id=updated_row.id,
                        ddr_id=updated_row.ddr_id,
                        date=updated_row.date,
                        status=updated_row.status,
                        final_json=updated_row.final_json,
                    )
                    await self._commit_outcome()
                    await self._publish_date_complete(snapshot)
                await self._resolve_embedding_service().embed_successful_date(snapshot)
                return DDRDateStatus.SUCCESS

            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "VALIDATION_FAILED", "errors": validation.errors},
                    raw_response=raw_response,
                )
                await self._publish_date_failed(updated_row)
        except Exception as exc:
            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_failed(
                    row,
                    error_log={"code": "PROCESSING_FAILED", "detail": str(exc)},
                    raw_response=raw_response,
                )
                await self._publish_date_failed(updated_row)
        return DDRDateStatus.FAILED

    async def _publish_date_complete(self, row: Any) -> None:
        if self.status_stream_service is None:
            return
        await self.status_stream_service.publish_date_complete(
            row.ddr_id,
            date=row.date,
            status=row.status,
            occurrences_count=0,
        )

    async def _publish_date_failed(self, row: Any) -> None:
        if self.status_stream_service is None:
            return
        await self.status_stream_service.publish_date_failed(
            row.ddr_id,
            date=row.date,
            error=self._error_message(row),
            raw_response_id=self._raw_response_id(row),
        )

    async def _generate_occurrences(self, ddr_id: str, ddr: Any) -> int:
        if self.occurrence_repository is None:
            return 0
        service = OccurrenceGenerationService(
            ddr_date_repository=self.ddr_date_repository,
            occurrence_repository=self.occurrence_repository,
        )
        return await service.generate_for_ddr(
            ddr_id=ddr_id,
            ddr_well_name=getattr(ddr, "well_name", None),
        )

    async def _publish_processing_complete(self, ddr_id: str, total_occurrences: int = 0) -> None:
        if self.status_stream_service is None:
            return
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        await self.status_stream_service.publish_processing_complete(
            ddr_id,
            total_dates=len(rows),
            failed_dates=sum(1 for row in rows if row.status == DDRDateStatus.FAILED),
            warning_dates=sum(1 for row in rows if row.status == DDRDateStatus.WARNING),
            total_occurrences=total_occurrences,
        )

    def _error_message(self, row: Any) -> str:
        error_log = getattr(row, "error_log", None)
        if isinstance(error_log, dict):
            for key in ("detail", "reason", "error"):
                if error_log.get(key):
                    return str(error_log[key])
            if error_log.get("errors"):
                return str(error_log["errors"])
            if error_log.get("code"):
                return str(error_log["code"])
        return "processing_failed"

    def _raw_response_id(self, row: Any) -> str:
        raw_response = getattr(row, "raw_response", None)
        if isinstance(raw_response, dict):
            for key in ("id", "raw_response_id", "response_id"):
                if raw_response.get(key):
                    return str(raw_response[key])
        return str(row.id)

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

    def _resolve_cost_service(self) -> ExtractionCostService:
        if self.cost_service is None:
            self.cost_service = ExtractionCostService(
                pipeline_run_repository=PipelineRunCRUDRepository(
                    async_session=self.ddr_date_repository.async_session,
                )
            )
        return self.cost_service

    def _resolve_embedding_service(self) -> TimeLogEmbeddingService:
        if self.embedding_service is None:
            self.embedding_service = TimeLogEmbeddingService()
        return self.embedding_service

    @staticmethod
    def _read_file_bytes(file_path: str) -> bytes:
        with open(file_path, "rb") as fh:
            return fh.read()


__all__ = ["PreSplitPipelineService"]
