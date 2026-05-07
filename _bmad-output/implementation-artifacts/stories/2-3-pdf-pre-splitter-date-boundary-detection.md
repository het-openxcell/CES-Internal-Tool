# Story 2.3: PDF Pre-Splitter - Date Boundary Detection

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want the pipeline to split a Pason DDR PDF into per-date chunks using native text extraction,
so that each date's data can be independently extracted and validated.

## Acceptance Criteria

1. Given a Pason DDR PDF with a native text layer, when `pipeline/pre_split` processes it using `pdfplumber`, then Tour Sheet Serial Number format `XXXXXX_YYYYMMDD_XA` is detected as the date boundary signal, pages are grouped into `dict[date_string, pdf_bytes]`, and multi-date overflow is handled without losing Tour 3 text or the next date header.
2. Given a page has no detectable text layer, when `pdfplumber` reads it, then an empty text result is logged as a warning with page number, and processing continues for remaining pages.
3. Given a non-standard contractor layout where Tour Sheet Serial is missing, when the pre-splitter finds no date boundaries, then a `ddr_dates` row is created with `status: "failed"` and `error_log` containing `{ "reason": "No date boundaries detected", "raw_page_content": "<first 500 chars>" }`, and the parent DDR status is set to `"failed"`.
4. Given the 109-page and 229-page sample PDFs in `ces-backend/tests/fixtures/`, when the pre-splitter test suite runs, then 100 percent of date boundaries are correctly detected for both samples.
5. Given `pdfplumber` successfully splits a PDF into N date chunks, when the result is returned to the pipeline orchestrator, then a `ddr_dates` row is created for each detected date with `status: "queued"`, and `ddrs.status` is updated to `"processing"`.

## Tasks / Subtasks

- [ ] Add PDF processing dependencies (AC: 1, 4)
  - [ ] Add `pdfplumber` and `pypdf` to `ces-backend/pyproject.toml`.
  - [ ] Do not add OCR, Docling, LlamaExtract, PyMuPDF, Celery, Redis, or Gemini extraction dependencies in this story.
  - [ ] Keep existing FastAPI, SQLAlchemy, Alembic, pytest, and Ruff dependency ranges intact.
- [ ] Create class-based pre-splitter module (AC: 1-2, 4)
  - [ ] Create `ces-backend/src/pipeline/pre_split.py`.
  - [ ] Implement a class such as `PDFPreSplitter`; no loose module-level workflow functions.
  - [ ] Use `pdfplumber.open(...)` for native text extraction and page scanning.
  - [ ] Use `pypdf.PdfReader` and `pypdf.PdfWriter` to build per-date PDF byte chunks in memory.
  - [ ] Return a typed result that includes `date_chunks: dict[str, bytes]`, page mappings, warnings, and a raw text preview for error handling.
  - [ ] Wrap sync PDF parsing/writing work with `asyncio.to_thread()` when called from async pipeline code.
- [ ] Implement boundary detection (AC: 1)
  - [ ] Detect Tour Sheet Serial values with a strict regex for `XXXXXX_YYYYMMDD_XA`, where the date group is exactly 8 digits.
  - [ ] Normalize output date keys as `YYYYMMDD` strings, matching existing `ddr_dates.date VARCHAR(8)`.
  - [ ] Scan every page from first to last and keep 1-based page numbers in warnings and tests.
  - [ ] Preserve source page order inside each generated PDF chunk.
  - [ ] Handle boundary pages that contain content for two dates by preserving both dates' relevant content. If page-level splitting cannot isolate text safely, overlapping the shared source page into both date chunks is acceptable and safer than dropping data.
- [ ] Handle no-text and no-boundary failures (AC: 2-3)
  - [ ] For pages where `extract_text()` returns empty or whitespace, record a warning with `page_number` and continue.
  - [ ] If no serial boundary exists in the full PDF, create exactly one failed `ddr_dates` row with `status: "failed"` and `error_log.reason = "No date boundaries detected"`.
  - [ ] Store `error_log.raw_page_content` as the first 500 characters of combined extracted text, or an empty string if no text exists.
  - [ ] Set parent `ddrs.status` to `"failed"` for the no-boundary case.
- [ ] Add pipeline orchestration service (AC: 3, 5)
  - [ ] Extend `DDRProcessingTask` in `ces-backend/src/services/ddr.py` or delegate it to a class under `ces-backend/src/services/pipeline.py`.
  - [ ] Read the uploaded PDF from the existing `ddrs.file_path`.
  - [ ] On successful split, create one `DDRDate` row per detected date with `status: "queued"`, update parent DDR to `"processing"`, and leave Gemini extraction for Story 2.4.
  - [ ] On no-boundary failure, create the failed `DDRDate` row and update parent DDR to `"failed"`.
  - [ ] Keep DB writes transactional per processing outcome; do not partially create date rows and then leave the parent status unchanged.
- [ ] Extend repository classes, not ad hoc persistence (AC: 3, 5)
  - [ ] Add repository methods to `ces-backend/src/repository/crud/ddr.py` for bulk date row creation and failed boundary recording.
  - [ ] Reuse `DDRDateCRUDRepository`, `DDRCRUDRepository.update_status`, and status constants in `src/models/schemas/ddr.py`.
  - [ ] Keep all timestamps as epoch integers.
  - [ ] Do not create SQL helpers outside repository classes.
- [ ] Add focused tests (AC: 1-5)
  - [ ] Add `ces-backend/tests/pipeline/test_pre_split.py` for regex detection, page grouping, no-text warning, no-boundary failure metadata, and in-memory PDF bytes output.
  - [ ] Add service tests proving successful split creates queued `ddr_dates` rows and sets parent DDR to `"processing"`.
  - [ ] Add service tests proving no-boundary split creates failed `ddr_dates` row and sets parent DDR to `"failed"`.
  - [ ] If real 109-page and 229-page PDFs are not present in `tests/fixtures/`, add a skipped or clearly marked fixture contract test and synthetic PDFs that exercise the same boundary behavior.
  - [ ] Do not require real Gemini, Qdrant, network calls, or `.env` secrets in tests.
- [ ] Preserve non-story behavior (AC: all)
  - [ ] Do not alter auth routes, JWT contract, upload validation contract, DDR list/detail response bodies, frontend files, Gemini extraction, Pydantic extraction schema, SSE stream, occurrence generation, Qdrant, corrections, exports, or keyword management.
  - [ ] Do not add source-file comments.

## Dev Notes

### Current Sprint State

Epic 2 is in progress. Story 2.1 and Story 2.2 are in review, and their implementation files are present in the working tree but still uncommitted. Treat those files as existing project work and extend them. Do not revert or replace them. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: git status --short]

### Story 2.3 Scope

This story starts the background processing pipeline only far enough to split uploaded PDFs and create `ddr_dates` rows. It must not call Gemini, validate extracted DDR JSON, emit SSE events, generate occurrences, write pipeline cost rows, or build frontend status UI. Those belong to Stories 2.4 through 2.6. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow]

### Existing Backend State To Preserve

Backend root is `ces-ddr-platform/ces-backend/`. API routes are registered from `src/main.py` through `src/api/endpoints.py` under `settings.API_PREFIX`, currently `/api`. DDR upload/list/detail routes already exist in `src/api/routes/v1/ddr.py`; keep their contracts stable. [Source: ces-ddr-platform/ces-backend/src/main.py] [Source: ces-ddr-platform/ces-backend/src/api/endpoints.py] [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py]

Story 2.2 left `DDRProcessingTask.process()` as a no-op placeholder in `src/services/ddr.py`. Replace that placeholder with orchestration or have it delegate to a pipeline service class. The upload endpoint already schedules `service.dispatch_background(ddr.id)` with FastAPI `BackgroundTasks`; reuse that hook rather than adding a new queue broker. [Source: ces-ddr-platform/ces-backend/src/services/ddr.py] [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md#Queue And Background Processing Rules]

Existing DDR persistence is in `src/repository/crud/ddr.py`, with `DDRCRUDRepository`, `DDRDateCRUDRepository`, `ProcessingQueueCRUDRepository`, and status constants in `src/models/schemas/ddr.py`. Extend those classes. Do not duplicate DDR models, create root `db/queries`, or bypass SQLAlchemy repositories. [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py] [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py]

### Boundary Detection Requirements

Primary date boundary signal is the Pason Tour Sheet Serial Number format `XXXXXX_YYYYMMDD_XA`. The extracted date string must remain `YYYYMMDD`, because `ddr_dates.date` is `VARCHAR(8)`. Contractor format changes are expected; this story only handles the locked primary format and records a graceful failed boundary result when missing. [Source: _bmad-output/planning-artifacts/prd.md#Domain Data Formats] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]

Pason DDR PDFs are native text, not scanned images. The pre-splitter must use native text extraction, not OCR or image conversion. Empty text on an individual page is warning-level and must not stop remaining page scans. A full document with no detected boundary is a controlled pipeline failure, not an exception-only crash. [Source: _bmad-output/planning-artifacts/prd.md#Innovation & Novel Patterns] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]

Multi-date overflow is a known risk: Tour 3 for date X can spill onto a page containing date Y's header. The implementation must prove it does not drop either date's content. Prefer text-coordinate or page-content analysis if practical. If safe intra-page separation is not practical with `pypdf`, duplicate the shared page into both affected date chunks and let Story 2.4 extraction ignore irrelevant rows. Data preservation beats overly clever page assignment. [Source: _bmad-output/planning-artifacts/prd.md#Risk Mitigations]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-backend/pyproject.toml
ces-ddr-platform/ces-backend/src/pipeline/__init__.py
ces-ddr-platform/ces-backend/src/pipeline/pre_split.py
ces-ddr-platform/ces-backend/src/services/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/tests/pipeline/test_pre_split.py
ces-ddr-platform/ces-backend/tests/test_ddr_processing_task.py
```

If the dev agent chooses `src/services/pipeline.py` for orchestration, keep PDF parsing itself under `src/pipeline/pre_split.py`, matching the architecture's `pipeline/` boundary. [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization] [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]

### Library And Framework Requirements

Use `pdfplumber` for text extraction. Its documented API supports `pdfplumber.open(...)` with a path, bytes-loaded file object, or file-like object, and exposes `pdf.pages` for page-by-page extraction. Use that instead of OCR libraries. [Source: https://pypi.org/project/pdfplumber/]

Use `pypdf` for in-memory PDF chunk construction. Current pypdf documentation shows `PdfReader(BytesIO(...))`, `PdfWriter.add_page(...)`, and `PdfWriter.write(...)` to a file-like object. Use `BytesIO` outputs for `dict[str, bytes]`. [Source: https://pypdf.readthedocs.io/en/latest/user/streaming-data.html] [Source: https://pypdf.readthedocs.io/en/stable/modules/PdfWriter.html]

The project currently does not include `pdfplumber` or `pypdf` in `pyproject.toml`; adding them is part of this story. Existing locked backend dependencies include FastAPI `>=0.135.1,<0.136.0`, SQLAlchemy `>=2.0.0,<3.0.0`, Alembic `>=1.18.4,<2.0.0`, and Python `>=3.12`. [Source: ces-ddr-platform/ces-backend/pyproject.toml]

### Async Correctness

`pdfplumber` and `pypdf` are synchronous libraries. Any PDF read, page text extraction, or PDF writing called from the background task must run through `asyncio.to_thread()`. Do not block the event loop. All repository calls must remain awaited. [Source: AGENTS.md#Backend Guidelines] [Source: _bmad-output/planning-artifacts/architecture.md#Component Boundaries]

### Error And Status Contracts

Successful split:

```text
ddrs.status = "processing"
ddr_dates.status = "queued" for each detected date
```

No-boundary failure:

```json
{
  "reason": "No date boundaries detected",
  "raw_page_content": "<first 500 chars>"
}
```

```text
ddrs.status = "failed"
ddr_dates.status = "failed"
```

Do not use `warning` for no-boundary failure. `warning` is reserved for per-date partial issues such as later Gemini rate-limit exhaustion. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4]

### Previous Story Intelligence

Story 2.1 resolved the timestamp conflict in older planning docs: use epoch `BIGINT`, not `TIMESTAMPTZ` or Python `datetime`. It also added `queued` to `DDRDateStatus` because Story 2.3 creates rows before extraction. Reuse that status constant. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

Story 2.2 added async upload storage, exact upload error responses, DB-backed queue insertion, and placeholder background dispatch. Story 2.3 must replace the placeholder with pre-splitting only; keep upload response time and route behavior stable. [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

### Git Intelligence

Recent commits:

```text
42309be Implement unified exception handling system with strategies and registry
8c0988b remove go
6617c4d feat: implement authentication and protected routes
25f66e9 Implement JWT authentication and user management in Go and Python backends
2932cd9 migration setup
```

Python backend is canonical. Do not restore Go code or create a second backend path. Exception handling is recent project work; avoid broad changes to it unless a focused test proves this story needs one. [Source: git log -5 --oneline]

### Testing Requirements

Run backend checks from `ces-ddr-platform/ces-backend/` with the UV virtualenv activated:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Existing tests use `TestClient`, direct service tests, and repository contract checks. Follow those patterns. PDF splitter tests should use small generated PDFs or fixture PDFs and must not call Gemini, Qdrant, external services, or real `.env` secrets. [Source: ces-ddr-platform/ces-backend/tests/test_ddr_upload_contract.py] [Source: ces-ddr-platform/ces-backend/tests/test_ddr_schema.py]

### Project Structure Notes

No `project-context.md` file exists even though workflow persistent facts requested it. Local project authority remains AGENTS rules: `decouple + BackendBaseSettings`, class/service encapsulation, no comments in source files, async correctness, epoch timestamps, and UV virtualenv activation for tests. [Source: AGENTS.md]

The repo currently has no `ces-backend/tests/fixtures/` sample PDFs. The story still requires fixture coverage when those PDFs are provided. Until then, synthetic tests must cover primary serial detection, multiple detected dates, no-text pages, no-boundary failure, and shared boundary page preservation. [Source: ces-ddr-platform/ces-backend/tests] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]
- [Source: _bmad-output/planning-artifacts/prd.md#Domain Data Formats]
- [Source: _bmad-output/planning-artifacts/prd.md#Risk Mitigations]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]
- [Source: ces-ddr-platform/ces-backend/src/services/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py]
- [Source: ces-ddr-platform/ces-backend/pyproject.toml]
- [Source: https://pypi.org/project/pdfplumber/]
- [Source: https://pypdf.readthedocs.io/en/latest/user/streaming-data.html]
- [Source: https://pypdf.readthedocs.io/en/stable/modules/PdfWriter.html]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
