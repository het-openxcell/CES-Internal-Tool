import asyncio
import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import IO, Union

import pdfplumber
import pypdf

from src.constants.pipeline import DATE_SERIAL_PATTERN, RAW_TEXT_PREVIEW_CHARS, TRUNCATED_DATE_SERIAL_PATTERN
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

    async def split_async(self, source: PDFSource) -> PreSplitResult:
        return await asyncio.to_thread(self.split, source)

    def _extract_page_texts(self, source: PDFSource) -> tuple[list[str], list[PreSplitWarning]]:
        page_texts: list[str] = []
        warnings: list[PreSplitWarning] = []
        with pdfplumber.open(self._as_pdfplumber_input(source)) as pdf:
            for index, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    page_number = index + 1
                    warnings.append(PreSplitWarning(page_number=page_number, reason="empty_text_layer"))
                    logger.warning(f"PDF page {page_number} has no extractable text layer")
                page_texts.append(text)
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
                and active_date in text
            ):
                assigned.append(active_date)
            for date in unique_on_page:
                if date not in assigned:
                    assigned.append(date)
            page_dates[page_number] = assigned
            active_date = unique_on_page[-1]

        return page_dates

    def _extract_dates(self, text: str) -> list[str]:
        matches: list[tuple[int, str]] = []
        for match in re.finditer(DATE_SERIAL_PATTERN, text):
            matches.append((match.start(), match.group(1)))
        for match in re.finditer(TRUNCATED_DATE_SERIAL_PATTERN, text):
            matches.append((match.start(), f"2{match.group(1)}"))
        return [date for _, date in sorted(matches)]

    def _build_chunks(self, source: PDFSource, page_dates: dict[int, list[str]]) -> dict[str, bytes]:
        reader = pypdf.PdfReader(self._as_pypdf_input(source))
        date_to_pages: dict[str, list[int]] = {}
        for page_number, dates in page_dates.items():
            for date in dates:
                date_to_pages.setdefault(date, []).append(page_number)

        result: dict[str, bytes] = {}
        for date, pages in date_to_pages.items():
            writer = pypdf.PdfWriter()
            for page_number in sorted(set(pages)):
                writer.add_page(reader.pages[page_number - 1])
            buffer = BytesIO()
            writer.write(buffer)
            result[date] = buffer.getvalue()
        return result

    def _build_preview(self, page_texts: list[str]) -> str:
        combined = "\n".join(text for text in page_texts if text)
        return combined[:RAW_TEXT_PREVIEW_CHARS]

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
