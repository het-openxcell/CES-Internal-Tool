import asyncio
from io import BytesIO
from pathlib import Path

import pypdf
from reportlab.pdfgen import canvas

from src.services.pipeline.pre_split import PDFPreSplitter


def _build_text_pdf(pages_text: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792))
    for text in pages_text:
        if text:
            y = 750
            for line in text.split("\n"):
                pdf.drawString(50, y, line)
                y -= 14
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _read_pdf_text(pdf_bytes: bytes) -> list[str]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return [page.extract_text() or "" for page in reader.pages]


def test_serial_pattern_groups_pages_by_date() -> None:
    pages = [
        "Tour Sheet Serial: 123456_20240115_1A\nDaily summary",
        "continued tour 1 content",
        "Tour Sheet Serial: 123456_20240116_2A\nDaily summary",
    ]
    pdf_bytes = _build_text_pdf(pages)

    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert set(result.date_chunks.keys()) == {"20240115", "20240116"}
    assert result.warnings == []
    pages_a = _read_pdf_text(result.date_chunks["20240115"])
    pages_b = _read_pdf_text(result.date_chunks["20240116"])
    assert len(pages_a) == 2
    assert len(pages_b) == 1


def test_overflow_page_with_two_dates_is_shared() -> None:
    pages = [
        "Tour Sheet Serial: 123456_20240115_1A header",
        "Tour 3 spillover for 20240115\nNew header Tour Sheet Serial: 123456_20240116_1A",
        "next day content",
    ]
    pdf_bytes = _build_text_pdf(pages)

    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert set(result.date_chunks.keys()) == {"20240115", "20240116"}
    assert result.page_dates[2] == ["20240115", "20240116"]
    assert len(_read_pdf_text(result.date_chunks["20240115"])) == 2
    assert len(_read_pdf_text(result.date_chunks["20240116"])) == 2


def test_no_text_page_emits_warning_and_continues() -> None:
    pages = [
        "Tour Sheet Serial: 123456_20240115_1A",
        "",
        "Tour Sheet Serial: 123456_20240116_1A",
    ]
    pdf_bytes = _build_text_pdf(pages)

    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert any(w.page_number == 2 and w.reason == "empty_text_layer" for w in result.warnings)
    assert set(result.date_chunks.keys()) == {"20240115", "20240116"}
    pages_a = _read_pdf_text(result.date_chunks["20240115"])
    assert len(pages_a) == 2


def test_no_boundary_returns_failure_metadata() -> None:
    pages = [
        "Some unrelated header without serial",
        "More content from a non-standard contractor",
    ]
    pdf_bytes = _build_text_pdf(pages)

    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert result.date_chunks == {}
    assert result.has_boundaries is False
    assert "Some unrelated header" in result.raw_text_preview


def test_split_async_returns_same_result() -> None:
    pages = ["Tour Sheet Serial: 123456_20240115_1A\nbody"]
    pdf_bytes = _build_text_pdf(pages)
    splitter = PDFPreSplitter()

    sync_result = splitter.split(pdf_bytes)
    async_result = asyncio.run(splitter.split_async(pdf_bytes))

    assert sync_result.date_chunks.keys() == async_result.date_chunks.keys()


def test_chunks_are_valid_pdf_bytes() -> None:
    pages = ["Tour Sheet Serial: 123456_20240115_1A"]
    pdf_bytes = _build_text_pdf(pages)
    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    chunk = result.date_chunks["20240115"]
    assert chunk.startswith(b"%PDF-")
    pypdf.PdfReader(BytesIO(chunk))


def test_strict_regex_rejects_nonstandard_serial_lengths() -> None:
    pages = ["serial like 123456_2024011_1A - does not match"]
    pdf_bytes = _build_text_pdf(pages)
    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert result.date_chunks == {}


def test_real_pason_serial_prefixes_are_detected() -> None:
    pages = [
        "FRONT PAGE SUMMARY UNKN1_20210728_2C Pason 2021 07 28",
        "FRONT PAGE SUMMARY 0Y52466_20241030_2A Pason 2024 10 30",
        "Tour Sheet Serial Number 144_20240714_2B Vendor Pason",
    ]
    pdf_bytes = _build_text_pdf(pages)
    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert set(result.date_chunks.keys()) == {"20210728", "20241030", "20240714"}


def test_truncated_pason_serial_date_is_restored() -> None:
    pages = ["Serial text extraction artifact 0221014_2C Vendor Pason 2022 10 14"]
    pdf_bytes = _build_text_pdf(pages)
    splitter = PDFPreSplitter()
    result = splitter.split(pdf_bytes)

    assert set(result.date_chunks.keys()) == {"20221014"}


def test_real_fixture_pdfs_when_present() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    if not fixtures_dir.exists():
        return
    candidates = [p for p in fixtures_dir.glob("*.pdf")]
    if not candidates:
        return
    splitter = PDFPreSplitter()
    for pdf_path in candidates:
        with pdf_path.open("rb") as fh:
            pdf_bytes = fh.read()
        result = splitter.split(pdf_bytes)
        assert result.has_boundaries, f"no boundaries detected in {pdf_path.name}"
