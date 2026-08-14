import asyncio
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from io import BytesIO
from typing import IO, ClassVar, Union

import pdfplumber
import pypdf

from src.constants.pipeline import (
    DATE_SERIAL_PATTERN,
    LABELED_DATE_PATTERN,
    RAW_TEXT_PREVIEW_CHARS,
    TRUNCATED_DATE_SERIAL_PATTERN,
)
from src.utilities.logging.logger import logger

PDFSource = Union[str, bytes, IO[bytes]]


@dataclass(frozen=True)
class PreSplitWarning:
    page_number: int
    reason: str


@dataclass
class PreSplitResult:
    date_chunks: dict[str, bytes]
    page_dates: dict[int, list[str]]
    warnings: list[PreSplitWarning] = field(default_factory=list)
    raw_text_preview: str = ""

    @property
    def has_boundaries(self) -> bool:
        return bool(self.date_chunks)


class PDFSplitProcessPool:
    _executor: ClassVar[ProcessPoolExecutor | None] = None

    @classmethod
    def get(cls) -> ProcessPoolExecutor:
        if cls._executor is None:
            from src.config.manager import settings

            cls._executor = ProcessPoolExecutor(
                max_workers=settings.PDF_SPLIT_PROCESS_POOL_WORKERS,
                mp_context=multiprocessing.get_context("spawn"),
                max_tasks_per_child=1,
            )
        return cls._executor

    @classmethod
    def reset(cls, executor: ProcessPoolExecutor | None = None) -> None:
        if executor is not None and executor is not cls._executor:
            return
        cls.shutdown()

    @classmethod
    def shutdown(cls) -> None:
        if cls._executor is not None:
            cls._executor.shutdown(wait=False, cancel_futures=True)
            cls._executor = None


class PDFPreSplitter:
    def split(self, source: PDFSource) -> PreSplitResult:
        source = self._normalize_source(source)
        page_texts, warnings = self._extract_page_texts(source)
        page_dates = self._assign_page_dates(page_texts)
        raw_preview = self._build_preview(page_texts)

        if not page_dates:
            return PreSplitResult(
                date_chunks={},
                page_dates={},
                warnings=warnings,
                raw_text_preview=raw_preview,
            )

        date_chunks = self._build_chunks(source, page_dates)
        return PreSplitResult(
            date_chunks=date_chunks,
            page_dates=page_dates,
            warnings=warnings,
            raw_text_preview=raw_preview,
        )

    async def split_async(self, source: PDFSource, timeout: float | None = None) -> PreSplitResult:
        from concurrent.futures.process import BrokenProcessPool

        from src.config.manager import settings

        effective_timeout = timeout if timeout is not None else float(settings.PDF_SPLIT_TIMEOUT_SECONDS)
        logger.info(f"PDFPreSplitter: split_async starting with timeout={effective_timeout}s")
        normalized_source = self._normalize_source(source)
        loop = asyncio.get_running_loop()
        try:
            executor = PDFSplitProcessPool.get()
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(executor, _run_pdf_split, normalized_source),
                    timeout=effective_timeout,
                )
            except BrokenProcessPool:
                logger.warning(
                    "PDFPreSplitter: process pool worker died (likely killed by the OS for memory), "
                    "restarting pool and retrying once"
                )
                PDFSplitProcessPool.reset(executor)
                return await asyncio.wait_for(
                    loop.run_in_executor(PDFSplitProcessPool.get(), _run_pdf_split, normalized_source),
                    timeout=effective_timeout,
                )
        except asyncio.TimeoutError:
            logger.error(f"PDFPreSplitter.split_async timed out after {effective_timeout}s — PDF too large/complex")
            raise

    def _extract_page_texts(self, source: PDFSource) -> tuple[list[str], list[PreSplitWarning]]:
        page_texts: list[str] = []
        warnings: list[PreSplitWarning] = []
        with pdfplumber.open(self._as_pdfplumber_input(source)) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDFPreSplitter: opened PDF, {total_pages} pages")
            for index, page in enumerate(pdf.pages):
                page_number = index + 1
                logger.debug(f"PDFPreSplitter: extracting text from page {page_number}/{total_pages}")
                text = page.extract_text() or ""
                if not text.strip():
                    warnings.append(PreSplitWarning(page_number=page_number, reason="empty_text_layer"))
                    logger.warning(f"PDFPreSplitter: page {page_number} has no extractable text layer")
                page_texts.append(text)
                page.close()
            logger.info(f"PDFPreSplitter: text extraction complete, {total_pages} pages processed")
        return page_texts, warnings

    def _assign_page_dates(self, page_texts: list[str]) -> dict[int, list[str]]:
        page_dates: dict[int, list[str]] = {}
        active_date: str | None = None
        for index, text in enumerate(page_texts):
            page_number = index + 1
            matches = self._extract_dates(text)
            unique_on_page = list(dict.fromkeys(matches))

            if not unique_on_page:
                if active_date is not None:
                    page_dates[page_number] = [active_date]
                continue

            assigned: list[str] = []
            if (
                active_date is not None
                and active_date not in unique_on_page
                and self._mentions_date_token(text, active_date)
            ):
                assigned.append(active_date)
            for date in unique_on_page:
                if date not in assigned:
                    assigned.append(date)
            page_dates[page_number] = assigned
            active_date = unique_on_page[-1]

        total_dates = len({d for dates in page_dates.values() for d in dates})
        logger.info(
            "PDFPreSplitter: date assignment done — "
            f"{len(page_dates)} pages assigned, {total_dates} unique dates"
        )
        if not page_dates and page_texts:
            sample = (page_texts[0] or "")[:300].replace("\n", " ")
            logger.warning(f"PDFPreSplitter: no dates found — page 1 text sample: {sample!r}")
        return page_dates

    def _mentions_date_token(self, text: str, date: str) -> bool:
        return re.search(rf"(?<!\d){re.escape(date)}(?!\d)", text) is not None

    def _extract_dates(self, text: str) -> list[str]:
        matches: list[tuple[int, str]] = []
        for match in re.finditer(DATE_SERIAL_PATTERN, text):
            matches.append((match.start(), match.group(1)))
        for match in re.finditer(TRUNCATED_DATE_SERIAL_PATTERN, text):
            matches.append((match.start(), f"2{match.group(1)}"))
        for match in re.finditer(LABELED_DATE_PATTERN, text):
            matches.append((match.start(), f"{match.group(1)}{match.group(2)}{match.group(3)}"))
        return [date for _, date in sorted(matches)]

    def _build_chunks(self, source: PDFSource, page_dates: dict[int, list[str]]) -> dict[str, bytes]:
        logger.info(f"PDFPreSplitter: building chunks with pypdf for {len(page_dates)} page-date mappings")
        reader = pypdf.PdfReader(self._as_pypdf_input(source))
        logger.info(f"PDFPreSplitter: pypdf reader opened, {len(reader.pages)} pages")
        date_to_pages: dict[str, list[int]] = {}
        for page_number, dates in page_dates.items():
            for date in dates:
                date_to_pages.setdefault(date, []).append(page_number)

        logger.info(f"PDFPreSplitter: building {len(date_to_pages)} date chunks: {sorted(date_to_pages.keys())}")
        result: dict[str, bytes] = {}
        for i, (date, pages) in enumerate(date_to_pages.items()):
            sorted_pages = sorted(set(pages))
            logger.debug(f"PDFPreSplitter: chunk {i+1}/{len(date_to_pages)} date={date} pages={sorted_pages}")
            writer = pypdf.PdfWriter()
            for page_number in sorted_pages:
                writer.add_page(reader.pages[page_number - 1])
            buffer = BytesIO()
            writer.write(buffer)
            writer.close()
            chunk_bytes = buffer.getvalue()
            buffer.close()
            result[date] = chunk_bytes
            logger.debug(
                f"PDFPreSplitter: chunk {i+1}/{len(date_to_pages)} date={date} written ({len(chunk_bytes)} bytes)"
            )
        logger.info(f"PDFPreSplitter: all {len(result)} chunks built successfully")
        return result

    def _build_preview(self, page_texts: list[str]) -> str:
        collected: list[str] = []
        length = 0
        for text in page_texts:
            if not text:
                continue
            collected.append(text)
            length += len(text) + 1
            if length > RAW_TEXT_PREVIEW_CHARS:
                break
        return "\n".join(collected)[:RAW_TEXT_PREVIEW_CHARS]

    def _normalize_source(self, source: PDFSource) -> PDFSource:
        if isinstance(source, (str, bytes, bytearray)):
            return source
        try:
            source.seek(0)
        except (AttributeError, OSError):
            pass
        data = source.read()
        return data if isinstance(data, bytes) else bytes(data)

    def _as_pdfplumber_input(self, source: PDFSource):
        if isinstance(source, (bytes, bytearray)):
            return BytesIO(bytes(source))
        return source

    def _as_pypdf_input(self, source: PDFSource):
        if isinstance(source, (bytes, bytearray)):
            return BytesIO(bytes(source))
        return source


def _run_pdf_split(source: PDFSource) -> PreSplitResult:
    return PDFPreSplitter().split(source)
