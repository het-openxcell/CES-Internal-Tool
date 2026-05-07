# Story 2.4: Per-Date Gemini Extraction & Pydantic Validation

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want each date chunk sent to Gemini 2.5 Flash-Lite for structured extraction and validated against the DDR schema,
so that structured drilling data is available for occurrence generation with full audit trail and no silent failures.

## Acceptance Criteria

1. Given a date chunk `pdf_bytes` is ready for extraction, when `pipeline/extract` calls Gemini 2.5 Flash-Lite with structured JSON output using `ces-backend/src/resources/ddr_schema.json` or an equivalent resource module, then Gemini returns JSON matching the extraction schema sections needed for occurrence generation, including `time_logs`, `mud_records`, `deviation_surveys`, and `bit_records`.
2. Given Gemini extraction runs, when credentials are loaded, then `GEMINI_API_KEY` is loaded through `decouple + BackendBaseSettings`, never through `os.getenv` or `os.environ.get`, and the key never appears in logs, error payloads, raw responses, or test output.
3. Given Gemini API returns HTTP 429, when extraction handles the rate limit, then exponential backoff is applied with waits `1s`, `2s`, `4s`, and `8s`, with max 3 retries before final handling, `ddr_dates.status` becomes `"warning"`, and `ddr_dates.error_log` contains `{ "code": "RATE_LIMITED" }`.
4. Given Gemini returns a response, when `pipeline/validate` runs Pydantic v2 validation against the extraction model, then success stores `raw_response`, stores validated `final_json`, and sets `ddr_dates.status` to `"success"` in one transaction.
5. Given Gemini returns malformed or schema-invalid JSON, when validation fails, then `raw_response` is retained, `ddr_dates.error_log` stores Pydantic error details, and `ddr_dates.status` becomes `"failed"` in one transaction.
6. Given extraction fails for one date, when the same DDR has other dates, then other dates continue processing independently; the parent `ddrs.status` becomes `"complete"` if any date succeeds and `"failed"` if all dates fail.
7. Given tests run with fixtures under `ces-backend/tests/fixtures/expected_timelogs.json` or synthetic equivalents until real fixtures exist, when the extraction and validation suite executes, then it proves prompt/schema mapping, success persistence, validation failure persistence, rate-limit warning handling, and per-date failure isolation without real Gemini, Qdrant, network calls, or `.env` secrets.

## Tasks / Subtasks

- [ ] Add Gemini SDK and resource configuration (AC: 1-2)
  - [ ] Add `google-genai` to `ces-ddr-platform/ces-backend/pyproject.toml`; do not add deprecated `google-generativeai`.
  - [ ] Add `GEMINI_API_KEY`, `GEMINI_MODEL`, and an extraction concurrency/rate setting to `BackendBaseSettings` using existing `decouple.AutoConfig`.
  - [ ] Add safe defaults for non-secret settings; do not provide a real API key in `.env.example`.
  - [ ] Keep settings encapsulated in settings classes; no loose env reads.
- [ ] Create extraction resource and Pydantic model (AC: 1, 4-5)
  - [ ] Create `ces-ddr-platform/ces-backend/src/resources/ddr_schema.json` or a resource class/module that can produce Gemini-compatible JSON Schema.
  - [ ] Create extraction Pydantic models under `src/models/schemas/` for the validated Gemini payload; do not confuse this with the existing `DDRDate` DB row schema.
  - [ ] Include the sections named by the epic: `time_logs`, `mud_records`, `deviation_surveys`, and `bit_records`.
  - [ ] Use Pydantic v2 `model_validate()` and `model_json_schema()` patterns.
  - [ ] If the full schema triggers Gemini complexity issues, implement a converter/fallback path to `response_json_schema` while preserving one validated internal payload model.
- [ ] Implement class-based Gemini extraction (AC: 1-3)
  - [ ] Create `ces-ddr-platform/ces-backend/src/pipeline/extract.py`.
  - [ ] Implement a class such as `GeminiDDRExtractor`; no loose workflow functions.
  - [ ] Use `from google import genai` and `google.genai.types`.
  - [ ] Call `await client.aio.models.generate_content(...)` with model `gemini-2.5-flash-lite` by default.
  - [ ] Send PDF chunks inline with `types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")`; do not use Files API for normal per-date chunks.
  - [ ] Configure JSON output with `response_mime_type="application/json"` plus `response_schema` or `response_json_schema`.
  - [ ] Prompt TIME LOG extraction in the same field order as the schema to protect row ordering.
  - [ ] Raise typed service exceptions such as `ExtractionError`, `RateLimitError`, and `ExtractionValidationError`; never expose raw SDK exceptions to clients.
- [ ] Implement validation layer (AC: 4-5)
  - [ ] Create `ces-ddr-platform/ces-backend/src/pipeline/validate.py`.
  - [ ] Implement a class such as `DDRExtractionValidator` that parses Gemini text as JSON and validates with the extraction Pydantic model.
  - [ ] Return structured validation results containing raw JSON, validated JSON, and serializable Pydantic errors.
  - [ ] Keep raw response retention explicit even on validation failure.
- [ ] Extend repository persistence atomically (AC: 3-6)
  - [ ] Add repository methods to `DDRDateCRUDRepository` for success, warning, and failed extraction updates.
  - [ ] Each update must set status, `raw_response`, `final_json`, `error_log`, and epoch `updated_at` consistently in one commit.
  - [ ] Add parent status finalization logic to `DDRCRUDRepository` or a service class: `"complete"` if at least one date succeeded, `"failed"` if all dates failed.
  - [ ] Do not bypass repositories with ad hoc SQL.
- [ ] Integrate with pipeline orchestration (AC: 3, 6)
  - [ ] Extend `DDRProcessingTask.process()` in `src/services/ddr.py` or delegate to `src/services/pipeline.py`.
  - [ ] Reuse Story 2.3 `PDFPreSplitter` output; if Story 2.3 code is absent, implement against its expected contract rather than inventing another splitter.
  - [ ] Process each date independently with bounded async concurrency.
  - [ ] Use `asyncio.gather(..., return_exceptions=True)` or equivalent isolation so one failed date does not abort the DDR.
  - [ ] Do not emit SSE events, write cost rows, generate occurrences, call Qdrant, or build frontend UI in this story.
- [ ] Add focused tests (AC: 1-7)
  - [ ] Add unit tests for schema loading and Pydantic validation success/failure.
  - [ ] Add extractor tests with a fake Gemini client; never call real Gemini.
  - [ ] Add rate-limit tests proving retry waits are invoked and final status is `"warning"` with code `RATE_LIMITED`.
  - [ ] Add service tests proving one date failure does not stop other dates.
  - [ ] Add repository tests for atomic success/failed/warning update payloads using existing test patterns.
  - [ ] Add fixture contract test for `tests/fixtures/expected_timelogs.json`; if the real fixture is missing, create a synthetic expected timelog file that preserves row order semantics.
  - [ ] Run `source .venv/bin/activate && ruff check .` and `source .venv/bin/activate && pytest` from `ces-ddr-platform/ces-backend/`.
- [ ] Preserve non-story behavior (AC: all)
  - [ ] Do not change auth routes, JWT contract, upload response contract, DDR list/detail response bodies, frontend files, SSE stream, occurrence generation, Qdrant, corrections, exports, or keyword management.
  - [ ] Do not add source-file comments.

## Dev Notes

### Current Sprint State

Epic 2 is in progress. Stories 2.1 and 2.2 are in review and Story 2.3 is `ready-for-dev`, not done. The working tree already contains uncommitted backend schema/upload work. Treat it as project work, extend it carefully, and do not revert it. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: git status --short]

### Hard Dependency On Story 2.3

This story assumes Story 2.3 provides `src/pipeline/pre_split.py` and returns `dict[str, bytes]` keyed by `YYYYMMDD`, with one queued `ddr_dates` row per detected date. The current code tree does not yet contain `src/pipeline/`, so the dev agent must either implement after 2.3 lands or adapt to the exact Story 2.3 contract. Do not create a second PDF splitter inside `extract.py`. [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]

`ddr_dates` does not currently store PDF chunk bytes. Normal processing should split the original `ddrs.file_path` in memory, extract each date chunk, and persist only `raw_response`, `final_json`, `error_log`, and status. Re-run storage/override behavior belongs to later monitoring stories unless needed for this AC. [Source: ces-ddr-platform/ces-backend/src/models/db/ddr.py] [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow]

### Existing Backend State To Preserve

Backend root is `ces-ddr-platform/ces-backend/`. Current upload orchestration lives in `src/services/ddr.py`; `DDRProcessingTask.process()` is still a no-op placeholder. DDR persistence lives in `src/repository/crud/ddr.py`, and status constants live in `src/models/schemas/ddr.py`. Extend these classes instead of adding standalone helpers. [Source: ces-ddr-platform/ces-backend/src/services/ddr.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py] [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py]

Existing route contracts from Story 2.2 must stay stable: `POST /api/ddrs/upload`, `GET /api/ddrs`, and `GET /api/ddrs/{ddr_id}`. This story is backend pipeline work, not an API contract expansion story. [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py] [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

### Architecture Compliance

Use the project flow: route/dependency to service class to repository class to SQLAlchemy ORM model. Gemini calls belong only in `src/pipeline/extract.py`; validation belongs in `src/pipeline/validate.py`; persistence stays in repositories. [Source: _bmad-output/planning-artifacts/architecture.md#Component Boundaries] [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]

Use Python-only backend files. Do not restore Go code, create parallel backend paths, or add Celery/Redis/message brokers. Current scale is 10-15 DDRs/day, so single-process FastAPI background processing remains acceptable for this story. [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md] [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Architectural Patterns and Design]

### Gemini Integration Requirements

Use `google-genai`, not deprecated `google-generativeai`. The project research and architecture both lock the SDK call pattern to `await client.aio.models.generate_content()`. Current Google Gemini docs confirm structured output supports JSON Schema/Pydantic-style schemas and Gemini 2.5 Flash-Lite supports structured output. [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Gemini API: SDK Version] [Source: https://ai.google.dev/gemini-api/docs/structured-output]

Use inline PDF parts for per-date chunks. Current Gemini document-processing docs state PDFs are supported up to 50MB or 1000 pages; per-date chunks are expected to be far smaller, so the Files API is not needed for the normal path. [Source: https://ai.google.dev/gemini-api/docs/document-processing] [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Gemini API Call Pattern]

Rate limits vary by quota tier and active limits should be checked in AI Studio. Story behavior is still fixed: handle 429 with backoff and then mark only that date as warning after retry exhaustion. [Source: https://ai.google.dev/gemini-api/docs/rate-limits] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4]

### Schema And Validation Guardrails

Gemini structured-output schemas can fail when too complex. Start with the required extraction shape and keep property names/order stable. If `response_schema` rejects the resource schema, add a targeted fallback to `response_json_schema`; do not remove Pydantic post-validation. [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Schema Architecture: Critical Risk]

`time_logs` row order is business-critical for occurrence generation. Preserve array order from Gemini output through Pydantic validation and JSONB storage. Tests must assert row order is unchanged for representative timelog rows. [Source: _bmad-output/planning-artifacts/prd.md#Risk Mitigations] [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Technical Recommendations]

Use epoch integers for all timestamps. Do not introduce `datetime`, ISO strings, or TIMESTAMPTZ in new models or update logic. [Source: AGENTS.md] [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md#Timestamp Conflict Resolution]

### Security And Error Handling

Add `GEMINI_API_KEY` only through `BackendBaseSettings`. Never log the key, include it in exception detail, or store it in DB. Raw Gemini response can be retained, but request config and headers must not be retained. [Source: AGENTS.md] [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Records]

Use typed exceptions from `src/utilities/exceptions/` or service-specific pipeline exceptions. The existing exception system is noisy and has recent user changes, so keep pipeline exceptions narrow and do not broad-refactor exception handling to satisfy this story. [Source: ces-ddr-platform/ces-backend/src/utilities/exceptions/exceptions.py] [Source: git log -5 --oneline]

### Previous Story Intelligence

Story 2.1 established DDR tables, JSONB fields, status constants, repository classes, and epoch timestamp rules. Reuse `DDRDateStatus.SUCCESS`, `DDRDateStatus.WARNING`, and `DDRDateStatus.FAILED`; do not scatter raw status strings across pipeline code. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

Story 2.2 added upload storage, queue insertion, route contracts, and `DDRProcessingTask.process()` as the background hook. Keep upload response fast and do not move Gemini work into the request path. Review findings on Story 2.2 flagged spoofed PDF validation, size guard gaps, and queue concurrency risks; avoid widening those areas while implementing extraction. [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

Story 2.3 says synchronous PDF libraries must run through `asyncio.to_thread()`. For this story, Gemini uses async SDK calls directly; any sync JSON/schema file loading on the hot path should be done once through a class-owned loader or wrapped when needed. [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-backend/pyproject.toml
ces-ddr-platform/ces-backend/.env.example
ces-ddr-platform/ces-backend/src/config/settings/base.py
ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/src/services/ddr.py
ces-ddr-platform/ces-backend/src/pipeline/__init__.py
ces-ddr-platform/ces-backend/src/pipeline/extract.py
ces-ddr-platform/ces-backend/src/pipeline/validate.py
ces-ddr-platform/ces-backend/src/resources/ddr_schema.json
ces-ddr-platform/ces-backend/tests/test_ddr_extraction_schema.py
ces-ddr-platform/ces-backend/tests/test_ddr_extraction_pipeline.py
ces-ddr-platform/ces-backend/tests/fixtures/expected_timelogs.json
```

If Story 2.3 already created `src/pipeline/__init__.py`, reuse it. If the schema is implemented as a Python resource class instead of JSON, keep it under `src/resources/` and ensure tests prove Gemini-compatible schema output. [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]

### Testing Requirements

Run backend validation from `ces-ddr-platform/ces-backend/` with UV venv activated:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Tests must fake Gemini and must not require `GEMINI_API_KEY`, network, Qdrant, real uploaded PDFs, or real `.env` secrets. Use synthetic minimal PDFs/chunk bytes for extractor unit tests and fixture JSON for validator tests. [Source: AGENTS.md] [Source: ces-ddr-platform/ces-backend/tests/test_ddr_upload_contract.py]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements]
- [Source: _bmad-output/planning-artifacts/prd.md#Risk Mitigations]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow]
- [Source: _bmad-output/planning-artifacts/architecture.md#Component Boundaries]
- [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Gemini API Call Pattern]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]
- [Source: ces-ddr-platform/ces-backend/src/services/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py]
- [Source: https://ai.google.dev/gemini-api/docs/structured-output]
- [Source: https://ai.google.dev/gemini-api/docs/document-processing]
- [Source: https://ai.google.dev/gemini-api/docs/rate-limits]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

### Completion Notes List

### File List
