import asyncio
import logging
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

from src.config.manager import settings
from src.models.db.ddr import DDRDate
from src.models.schemas.ddr import DDRDateStatus, DDRStatus
from src.repository.crud.ddr import PipelineRunCRUDRepository
from src.services.occurrence.llm_generate import LLMOccurrenceGenerationService
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
from src.services.storage_service import StorageService
from src.utilities.exceptions import BadRequestException, EntityDoesNotExist

logger = logging.getLogger(__name__)


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
        storage_service: StorageService | None = None,
    ) -> None:
        self.ddr_repository = ddr_repository
        self.ddr_date_repository = ddr_date_repository
        self.occurrence_repository = occurrence_repository
        self.pre_splitter = pre_splitter or PDFPreSplitter()
        self.storage_service = storage_service or StorageService()
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
        pdf_bytes = await self.pdf_loader(ddr_id)
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

        for date, chunk_bytes in result.date_chunks.items():
            await self.storage_service.upload_chunk(ddr_id, date, chunk_bytes)

        if self.extract_after_split:
            await self._extract_all_dates(
                ddr_id=ddr_id,
                ddr=ddr,
                date_chunks=result.date_chunks,
                date_page_numbers=self._date_page_numbers_from_split(getattr(result, "page_dates", {})),
            )
        return result

    async def retry_date(self, ddr_id: str, date: str) -> DDRDate:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)

        row = await self.ddr_date_repository.read_date_for_update(ddr_id, date)
        if row is None:
            raise EntityDoesNotExist("date_not_found")
        if row.status not in (DDRDateStatus.FAILED, DDRDateStatus.WARNING):
            raise BadRequestException("date_not_retryable")
        await self.ddr_date_repository.update_status(row, DDRDateStatus.QUEUED)

        chunk_bytes = await self.storage_service.download_chunk(ddr_id, date)
        date_page_numbers = await self._original_page_numbers_for_ddr(ddr_id)
        extractor = self.extractor or GeminiDDRExtractor()
        await self._process_one_date(
            extractor,
            row,
            date,
            chunk_bytes,
            original_page_numbers=date_page_numbers.get(date),
        )

        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = self._metadata_from_rows(rows)
        await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)

        refreshed = next((r for r in rows if r.date == date), row)
        if self._has_queued_dates(rows):
            await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)
            return refreshed

        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        await self.ddr_repository.finalize_status_from_dates(ddr, [r.status for r in rows])

        try:
            total_occurrences = await self._generate_occurrences(
                ddr_id=ddr_id, well_name=well_name, surface_location=surface_location
            )
        except Exception:
            logger.warning("Occurrence generation failed during retry for DDR %s", ddr_id)
            total_occurrences = 0

        await self._publish_processing_complete(ddr_id, total_occurrences=total_occurrences)
        return refreshed

    async def regenerate_occurrences(self, ddr_id: str) -> int:
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = self._metadata_from_rows(rows)
        return await self._generate_occurrences(
            ddr_id=ddr_id,
            well_name=well_name,
            surface_location=surface_location,
        )

    async def reprocess_dates(self, ddr_id: str, dates: list[str] | None) -> int:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)

        if not dates:
            target_set = {r.date for r in rows}
        else:
            target_set = set(dates)
        date_to_row = {r.date: r for r in rows if r.date in target_set}
        if not date_to_row:
            await self.ddr_repository.finalize_status_from_dates(ddr, [r.status for r in rows])
            await self._publish_processing_complete(ddr_id)
            return 0

        for row in date_to_row.values():
            await self.ddr_date_repository.update_status(row, DDRDateStatus.QUEUED)

        await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)

        extractor = self.extractor or GeminiDDRExtractor()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        date_page_numbers = await self._original_page_numbers_for_ddr(ddr_id)

        async def run_one(date: str) -> str:
            row = date_to_row[date]
            try:
                chunk_bytes = await self.storage_service.download_chunk(ddr_id, date)
            except Exception as exc:
                async with self._write_lock:
                    updated_row = await self.ddr_date_repository.mark_failed_preserve(
                        row,
                        error_log={"code": "CHUNK_MISSING", "detail": str(exc)},
                    )
                    await self._publish_date_failed(updated_row)
                return DDRDateStatus.FAILED
            async with semaphore:
                return await self._process_one_date_preserve(
                    extractor,
                    row,
                    date,
                    chunk_bytes,
                    original_page_numbers=date_page_numbers.get(date),
                )

        await asyncio.gather(*[run_one(d) for d in date_to_row.keys()], return_exceptions=True)

        all_rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = self._metadata_from_rows(all_rows)
        await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)
        await self.ddr_repository.finalize_status_from_dates(ddr, [r.status for r in all_rows])

        try:
            total = await self._generate_occurrences(
                ddr_id=ddr_id, well_name=well_name, surface_location=surface_location
            )
        except Exception:
            logger.warning("Occurrence generation failed during reprocess for DDR %s", ddr_id)
            total = 0
        await self._publish_processing_complete(ddr_id, total_occurrences=total)
        return total

    async def reprocess_full(self, ddr_id: str) -> int:
        ddr = await self.ddr_repository.read_ddr_by_id(ddr_id)
        pdf_bytes = await self.pdf_loader(ddr_id)
        result = await self.pre_splitter.split_async(pdf_bytes)

        if not result.has_boundaries:
            await self.ddr_repository.update_status(ddr, DDRStatus.FAILED)
            await self._publish_processing_complete(ddr_id)
            return 0

        new_dates = set(result.date_chunks.keys())
        existing_rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        existing_dates = {r.date for r in existing_rows}

        obsolete = sorted(existing_dates - new_dates)

        for row in existing_rows:
            if row.date in new_dates:
                await self.ddr_date_repository.update_status(row, DDRDateStatus.QUEUED)

        new_only = sorted(new_dates - existing_dates)
        for date in new_only:
            await self.ddr_date_repository.create_ddr_date(ddr_id, date)

        await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)

        for date, chunk_bytes in result.date_chunks.items():
            await self.storage_service.upload_chunk(ddr_id, date, chunk_bytes)

        await self._extract_all_dates_preserve(
            ddr_id=ddr_id,
            ddr=ddr,
            date_chunks=result.date_chunks,
            obsolete_dates=obsolete,
            date_page_numbers=self._date_page_numbers_from_split(result.page_dates),
        )
        rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        return sum(1 for r in rows if r.status == DDRDateStatus.SUCCESS)

    async def _extract_all_dates_preserve(
        self,
        *,
        ddr_id: str,
        ddr: Any,
        date_chunks: dict[str, bytes],
        obsolete_dates: list[str] | None = None,
        date_page_numbers: dict[str, list[int]] | None = None,
    ) -> None:
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
                return await self._process_one_date_preserve(
                    extractor,
                    row,
                    date,
                    chunk_bytes,
                    original_page_numbers=(date_page_numbers or {}).get(date),
                )

        coroutines = [run_one(date, chunk) for date, chunk in date_chunks.items() if date in date_to_row]
        await asyncio.gather(*coroutines, return_exceptions=True)

        if obsolete_dates:
            await self.ddr_date_repository.delete_by_ddr_id_and_dates(ddr_id, obsolete_dates)
        all_rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = self._metadata_from_rows(all_rows)
        await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)
        await self.ddr_repository.finalize_status_from_dates(ddr, [r.status for r in all_rows])

        try:
            total = await self._generate_occurrences(
                ddr_id=ddr_id, well_name=well_name, surface_location=surface_location
            )
        except Exception:
            logger.warning("Occurrence generation failed during full reprocess for DDR %s", ddr_id)
            total = 0
        await self._publish_processing_complete(ddr_id, total_occurrences=total)

    async def _process_one_date_preserve(
        self,
        extractor: GeminiDDRExtractor,
        row: Any,
        date: str,
        chunk_bytes: bytes,
        original_page_numbers: list[int] | None = None,
    ) -> str:
        await self._publish_date_started(row.ddr_id, date)
        try:
            extraction = await self._extract_with_page_context(
                extractor,
                date=date,
                pdf_bytes=chunk_bytes,
                original_page_numbers=original_page_numbers,
            )
        except RateLimitError:
            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_warning_preserve(
                    row,
                    error_log={"code": "RATE_LIMITED"},
                )
                await self._publish_date_complete(updated_row)
            return DDRDateStatus.WARNING
        except ExtractionError as exc:
            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_failed_preserve(
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
                updated_row = await self.ddr_date_repository.mark_failed_preserve(
                    row,
                    error_log={"code": "VALIDATION_FAILED", "errors": validation.errors},
                    raw_response=raw_response,
                )
                await self._publish_date_failed(updated_row)
        except Exception as exc:
            async with self._write_lock:
                updated_row = await self.ddr_date_repository.mark_failed_preserve(
                    row,
                    error_log={"code": "PROCESSING_FAILED", "detail": str(exc)},
                    raw_response=raw_response,
                )
                await self._publish_date_failed(updated_row)
        return DDRDateStatus.FAILED

    async def _extract_all_dates(
        self,
        *,
        ddr_id: str,
        ddr: Any,
        date_chunks: dict[str, bytes],
        date_page_numbers: dict[str, list[int]] | None = None,
    ) -> None:
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
                return await self._process_one_date(
                    extractor,
                    row,
                    date,
                    chunk_bytes,
                    original_page_numbers=(date_page_numbers or {}).get(date),
                )

        coroutines = [run_one(date, chunk) for date, chunk in date_chunks.items() if date in date_to_row]
        outcomes = await asyncio.gather(*coroutines, return_exceptions=True)

        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                logger.warning("Date extraction task failed for DDR %s", ddr_id)

        all_rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
        well_name, surface_location = self._metadata_from_rows(all_rows)
        await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)

        if self._has_queued_dates(all_rows):
            await self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)
            return

        await self.ddr_repository.finalize_status_from_dates(ddr, [r.status for r in all_rows])

        try:
            total_occurrences = await self._generate_occurrences(
                ddr_id=ddr_id, well_name=well_name, surface_location=surface_location
            )
        except Exception:
            logger.warning("Occurrence generation failed for DDR %s", ddr_id)
            total_occurrences = 0
        await self._publish_processing_complete(ddr_id, total_occurrences=total_occurrences)

    async def _original_page_numbers_for_ddr(self, ddr_id: str) -> dict[str, list[int]]:
        try:
            pdf_bytes = await self.pdf_loader(ddr_id)
            result = await self.pre_splitter.split_async(pdf_bytes)
            return self._date_page_numbers_from_split(result.page_dates)
        except Exception as exc:
            logger.warning("Original page number mapping failed for DDR %s: %s", ddr_id, exc)
            return {}

    def _date_page_numbers_from_split(self, page_dates: dict[int, list[str]]) -> dict[str, list[int]]:
        date_page_numbers: dict[str, list[int]] = {}
        for page_number, dates in page_dates.items():
            for date in dates:
                date_page_numbers.setdefault(date, []).append(page_number)
        return {date: sorted(set(page_numbers)) for date, page_numbers in date_page_numbers.items()}

    def _has_queued_dates(self, rows: list[Any] | Any) -> bool:
        return any(row.status == DDRDateStatus.QUEUED for row in rows)

    def metadata_from_rows(self, rows: list[Any] | Any) -> tuple[str | None, str | None]:
        return self._metadata_from_rows(rows)

    def _metadata_from_rows(self, rows: list[Any] | Any) -> tuple[str | None, str | None]:
        well_name = next(
            (r.final_json.get("well_name") for r in rows if r.final_json and r.final_json.get("well_name")),
            None,
        )
        surface_location = next(
            (
                r.final_json.get("surface_location")
                for r in rows
                if r.final_json and r.final_json.get("surface_location")
            ),
            None,
        )
        return well_name, surface_location

    async def _process_one_date(
        self,
        extractor: GeminiDDRExtractor,
        row: Any,
        date: str,
        chunk_bytes: bytes,
        original_page_numbers: list[int] | None = None,
    ) -> str:
        await self._publish_date_started(row.ddr_id, date)
        try:
            extraction = await self._extract_with_page_context(
                extractor,
                date=date,
                pdf_bytes=chunk_bytes,
                original_page_numbers=original_page_numbers,
            )
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

    async def _extract_with_page_context(
        self,
        extractor: GeminiDDRExtractor,
        *,
        date: str,
        pdf_bytes: bytes,
        original_page_numbers: list[int] | None,
    ):
        try:
            return await extractor.extract(
                date=date,
                pdf_bytes=pdf_bytes,
                original_page_numbers=original_page_numbers,
            )
        except TypeError as exc:
            if "original_page_numbers" not in str(exc):
                raise
            return await extractor.extract(date=date, pdf_bytes=pdf_bytes)

    async def _publish_date_started(self, ddr_id: str, date: str) -> None:
        if self.status_stream_service is None:
            return
        await self.status_stream_service.publish_date_started(ddr_id, date)

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

    async def _generate_occurrences(
        self, ddr_id: str, well_name: str | None = None, surface_location: str | None = None
    ) -> int:
        if self.occurrence_repository is None:
            return 0
        service = LLMOccurrenceGenerationService(
            ddr_date_repository=self.ddr_date_repository,
            occurrence_repository=self.occurrence_repository,
        )
        return await service.generate_for_ddr(
            ddr_id=ddr_id,
            ddr_well_name=well_name,
            ddr_surface_location=surface_location,
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

    async def _default_pdf_loader(self, ddr_id: str) -> bytes:
        return await self.storage_service.download_original(ddr_id)

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


__all__ = ["PreSplitPipelineService"]
