# Story 2.6: Extraction Cost Tracking & Time Log Embedding

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want AI compute costs recorded per extraction and time log text indexed into Qdrant,
so that pipeline costs are trackable and natural language search has data to query.

## Acceptance Criteria

1. Given a date chunk is successfully extracted by Gemini, when the response is processed, then a `pipeline_runs` row is written with `gemini_input_tokens`, `gemini_output_tokens`, and `cost_usd`.
2. Given a successful date extraction is persisted, when `ddr_dates` is updated to `success`, then the `pipeline_runs` write is committed in the same DB transaction as that date update.
3. Given a `ddr_dates` row has `status: "success"` and populated `final_json`, when time log embedding runs after extraction persistence, then each time log row's text is embedded using Gemini API model `gemini-embedding-2` with the existing `GEMINI_API_KEY`.
4. Given time log embeddings are generated, when Qdrant upsert runs, then vectors are upserted into collection `ddr_time_logs` with metadata `{ "ddr_id", "date", "time_from", "time_to", "code" }`.
5. Given Qdrant is unreachable or embedding upsert fails, when the failure is handled, then the failure is logged as warning and extraction success is not rolled back or downgraded.
6. Given `GET /api/pipeline/cost` is called with valid JWT, when the request succeeds, then HTTP 200 returns `{ "total_cost_usd": N, "total_runs": N, "period": "all_time" }` from `pipeline_runs`.
7. Given all Epic 1 and Epic 2 migrations have run, when Alembic migrations are reviewed, then users, ddrs, ddr_dates, processing_queue, and pipeline_runs remain the canonical schema, with no app-startup schema creation fallback.

## Tasks / Subtasks

- [ ] Add cost calculation and pipeline run persistence (AC: 1-2)
  - [ ] Extend `PipelineRunCRUDRepository` with an aggregate method for all-time cost and run count.
  - [ ] Add a class-owned service such as `ExtractionCostService` under `src/services/` or `src/services/pipeline/`.
  - [ ] Use `ExtractionResult.input_tokens` and `ExtractionResult.output_tokens`; do not re-count tokens after Gemini if `usage_metadata` already supplied them.
  - [ ] Calculate `cost_usd` with `Decimal`, quantized to six decimal places for `NUMERIC(10,6)`.
  - [ ] Use model-specific configured prices loaded through `BackendBaseSettings`; no loose constants scattered through pipeline code.
  - [ ] Persist the pipeline run with `commit=False` or equivalent transaction control so date success and run row commit together.
- [ ] Make DDR date success update transaction-aware (AC: 1-2)
  - [ ] Update `DDRDateCRUDRepository.mark_success()` so Story 2.6 can write `ddr_dates` and `pipeline_runs` in one session transaction.
  - [ ] Preserve current call sites by keeping default behavior compatible.
  - [ ] Keep `raw_response`, `final_json`, `error_log`, `status`, and epoch `updated_at` update semantics unchanged.
  - [ ] Do not bypass repositories with raw SQL.
- [ ] Add Google embedding client and Qdrant service (AC: 3-5)
  - [ ] Add `qdrant-client` to `ces-ddr-platform/ces-backend/pyproject.toml`; use async client APIs.
  - [ ] Add settings for `QDRANT_URL`, optional `QDRANT_API_KEY`, `QDRANT_COLLECTION_DDR_TIME_LOGS`, `GEMINI_EMBEDDING_MODEL`, embedding dimension, and cost pricing through `BackendBaseSettings`.
  - [ ] Implement class-owned `TimeLogEmbeddingService` or equivalent; no loose utility functions.
  - [ ] Use `client.aio.models.embed_content(model="gemini-embedding-2", contents=[...])` through an injectable Gemini API wrapper for tests.
  - [ ] Use Qdrant `AsyncQdrantClient` and `await client.upsert(...)`; do not block async routes or pipeline tasks with sync Qdrant calls.
  - [ ] Ensure collection exists before upsert with vector size `3072` unless settings deliberately override it.
  - [ ] Use stable point ids derived from `ddr_date.id` plus row index so retries overwrite rather than duplicate vectors.
- [ ] Extract time log rows from validated DDR JSON (AC: 3-4)
  - [ ] Parse `final_json["time_logs"]` using current schema fields from `DDRExtractionTimeLog`.
  - [ ] Build embedding text from the row's operational description. Current schema uses `activity` plus optional `comment`; if real Gemini output uses `details`, support it without breaking `activity`.
  - [ ] Skip empty text rows without failing the date.
  - [ ] Map metadata exactly to `ddr_id`, `date`, `time_from`, `time_to`, and `code`; derive `time_from/time_to` from `start_time/end_time` if needed.
  - [ ] Include useful payload text in Qdrant if needed for Story 6 retrieval, but do not change required metadata keys.
- [ ] Integrate embedding after successful extraction (AC: 3-5)
  - [ ] Wire embedding from `PreSplitPipelineService._process_one_date()` only after `mark_success` and pipeline run writes commit.
  - [ ] If embedding fails, catch inside embedding service boundary, log warning with `ddr_id`, `ddr_date_id`, and `date`, and keep extraction success intact.
  - [ ] Do not emit failed SSE events for embedding failures; extraction is still successful.
  - [ ] Do not make Qdrant availability a prerequisite for PDF ingestion.
- [ ] Add authenticated pipeline cost API (AC: 6)
  - [ ] Create or extend route module for `GET /api/pipeline/cost`; architecture places pipeline operations under `api/pipeline`.
  - [ ] Register the route in `src/api/endpoints.py`.
  - [ ] Protect it with existing `jwt_authentication`.
  - [ ] Return direct JSON response with `total_cost_usd`, `total_runs`, and `period`.
  - [ ] Keep values serializable; if using `Decimal`, serialize as JSON number or string consistently with tests.
- [ ] Validate migration authority and dependency wiring (AC: 7)
  - [ ] Confirm no new migration is needed for `pipeline_runs`; if schema drift exists, repair Alembic, not `Base.metadata.create_all()`.
  - [ ] Remove or block any startup `create_all` fallback if still active before claiming AC 7.
  - [ ] Do not add database tables for embeddings in this story; Qdrant owns vectors, PostgreSQL owns extraction audit/cost.
- [ ] Add focused backend tests (AC: 1-7)
  - [ ] Unit test cost calculation from input/output token counts with `Decimal` precision.
  - [ ] Repository/service test proves date success and `pipeline_runs` write share a transaction.
  - [ ] Embedding service tests use fake Google and fake Qdrant clients; no network, real Gemini, real Qdrant, or secrets.
  - [ ] Test Qdrant failure logs warning and leaves date success/final JSON intact.
  - [ ] Route test proves `/api/pipeline/cost` requires auth and returns all-time aggregate shape.
  - [ ] Static/migration test proves canonical Alembic schema still includes `pipeline_runs` and startup does not create schemas outside Alembic.
  - [ ] Run `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/`.
- [ ] Preserve non-story behavior (AC: all)
  - [ ] Do not change login/JWT contracts, upload response body, DDR list/detail response body, SSE event names/payloads, PDF splitting, Gemini extraction schema, occurrence generation, frontend pages, corrections, exports, or keyword management except where directly required by cost/embedding.
  - [ ] Do not add source-file comments.

## Dev Notes

### Current Sprint State

Epic 2 is in progress. Story 2.5 is in review and the working tree contains its uncommitted backend and frontend changes. Treat those files as existing sprint work; extend the backend pipeline carefully and do not revert or rewrite the Story 2.5 SSE/status implementation. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: git status --short]

### Existing Backend State To Preserve

Backend root is `ces-ddr-platform/ces-backend/`. DDR route registration currently runs through `src/main.py` to `src/api/endpoints.py`, which includes `src/api/routes/v1/ddr.py` under `/api`. New pipeline cost route should follow the same route registration style and not add `/v1`. [Source: ces-ddr-platform/ces-backend/src/main.py] [Source: ces-ddr-platform/ces-backend/src/api/endpoints.py] [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py]

Current extraction flow is `DDRUploadService` -> `DDRProcessingTask.process()` -> `PreSplitPipelineService.run()` -> `_process_one_date()`. `_process_one_date()` calls `GeminiDDRExtractor.extract()`, validates text, then updates `DDRDateCRUDRepository.mark_success/mark_failed/mark_warning` and publishes SSE status events. Add cost tracking and embedding inside this existing path; do not create a second pipeline runner. [Source: ces-ddr-platform/ces-backend/src/services/ddr.py] [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]

`ExtractionResult` already exposes `input_tokens` and `output_tokens` from Google `usage_metadata.prompt_token_count` and `usage_metadata.candidates_token_count`. Story 2.6 should consume those fields directly for pipeline run cost. [Source: ces-ddr-platform/ces-backend/src/services/pipeline/extract.py]

The `pipeline_runs` table, ORM model, schema, and repository already exist from Story 2.1. Current repository only has `create_pipeline_run()` and commits immediately through `BaseCRUDRepository.create()`. This story must add transaction control for same-transaction date success plus pipeline run persistence. [Source: ces-ddr-platform/ces-backend/src/models/db/ddr.py] [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py]

### Architecture Compliance

Use Python-only FastAPI backend. No Go backend, Celery, Redis, third-party analytics, or frontend work for this story. Route/dependency code must delegate to service classes, service classes to repository classes, and repositories to SQLAlchemy ORM models. [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md] [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]

All config must be read through `decouple + BackendBaseSettings`. Do not use `os.getenv`, `os.environ.get`, module-level pricing constants, or local `.env` parsing. [Source: AGENTS.md] [Source: ces-ddr-platform/ces-backend/src/config/settings/base.py]

All timestamps remain epoch integers. Do not introduce `datetime`, `DateTime`, or ISO timestamp columns for cost or embedding work. [Source: AGENTS.md] [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

### Cost Tracking Requirements

Gemini extraction currently uses `google-genai` and async `client.aio.models.generate_content()`. Google Gen AI docs expose `usage_metadata` with prompt/input token count, candidates/output token count, and total token count after generation. Use the already captured `ExtractionResult.input_tokens` and `ExtractionResult.output_tokens`; do not parse raw response text for token accounting. [Source: ces-ddr-platform/ces-backend/src/services/pipeline/extract.py] [Source: https://ai.google.dev/gemini-api/docs/tokens?lang=python]

Use `Decimal` for money. `pipeline_runs.cost_usd` is `NUMERIC(10,6)`, and previous tests explicitly protect Decimal use. Do not use float for persisted cost. [Source: ces-ddr-platform/ces-backend/src/models/db/ddr.py] [Source: ces-ddr-platform/ces-backend/tests/test_ddr_schema.py]

Pricing should be configurable because Gemini prices can change. Use settings such as `GEMINI_FLASH_LITE_INPUT_COST_PER_1M_TOKENS` and `GEMINI_FLASH_LITE_OUTPUT_COST_PER_1M_TOKENS` with defaults matching planning research: input `$0.10/1M`, output `$0.40/1M`. [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Cost Model]

### Embedding And Qdrant Requirements

Architecture locks vector search to Qdrant and names the collection `ddr_time_logs`. Current `pyproject.toml` does not include `qdrant-client`; add it in the backend dependency list and keep tests fake-only. [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] [Source: ces-ddr-platform/ces-backend/pyproject.toml]

Use Gemini Embedding 2 model id `gemini-embedding-2` through the Gemini API with the existing `GEMINI_API_KEY`, not through Vertex AI project/location configuration. The Google Cloud model page is useful for model capabilities: multimodal inputs, maximum input tokens `8,192`, default output vector dimension `3,072`, adjustable output dimensionality, and MRL support. Use dimension `3072` unless `BackendBaseSettings` deliberately overrides it. [Source: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2]

Google embedding API supports `models.embedContent`; Python Gen AI SDK docs show async `client.aio.models.embed_content(...)`. Initialize `genai.Client(api_key=settings.GEMINI_API_KEY)` as the existing extraction client does; do not enable Vertex mode, do not require ADC, and do not add `GEMINI_VERTEX_PROJECT` or `GEMINI_VERTEX_LOCATION`. Wrap the SDK in an injectable class so tests do not import network clients or require real API keys. [Source: https://googleapis.github.io/python-genai/genai.html] [Source: ces-ddr-platform/ces-backend/src/services/pipeline/extract.py]

Qdrant Python docs expose `AsyncQdrantClient` and async `upsert(collection_name, points, wait=True, ...)`. Use async APIs directly. If a sync SDK call is ever used, wrap it in `asyncio.to_thread()`, but preferred implementation is async. [Source: https://python-client.qdrant.tech/qdrant_client.async_qdrant_client] [Source: https://qdrant.tech/documentation/tutorials/async-api/]

Qdrant upsert overwrites existing points with the same id. Stable point ids prevent duplicate vectors on pipeline retry or resume. Use a deterministic id based on `ddr_date.id` and row index or a UUID v5 generated from those fields. [Source: https://python-client.qdrant.tech/qdrant_client.async_qdrant_client]

### Time Log Mapping

Current validated schema uses `DDRExtractionTimeLog` fields: `start_time`, `end_time`, `duration_hours`, `activity`, `depth_md`, and `comment`. The epic names row text as `details`, so implementation should support both `details` if present in real output and current `activity/comment` fields in schema. Do not change the extraction schema just for embedding unless tests prove actual fixture mismatch. [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6]

Required Qdrant metadata keys are exact: `ddr_id`, `date`, `time_from`, `time_to`, and `code`. Current schema has `start_time/end_time` and no `code`; map `start_time` to `time_from`, `end_time` to `time_to`, and use `code` from row data if present, otherwise `null` or empty string consistently. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6]

Embedding failure is degraded search readiness, not extraction failure. Do not rollback `ddr_dates.status = "success"` or `pipeline_runs` when Qdrant is unreachable. Log warning and continue. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] [Source: _bmad-output/planning-artifacts/architecture.md#Processing/Date Status Values]

### API Contract

Add `GET /api/pipeline/cost`, authenticated by `jwt_authentication`. Success response is direct object:

```json
{ "total_cost_usd": 0.123456, "total_runs": 12, "period": "all_time" }
```

Use the existing standard error behavior for unauthenticated requests. Do not add pagination or date filters unless a later story asks for them. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

### Previous Story Intelligence

Story 2.1 established DDR tables, status constants, pipeline run schema, `Decimal` cost type, and epoch timestamp rules. It also left a review finding that startup `Base.metadata.create_all()` could bypass Alembic; AC 7 requires this to be addressed before Story 2.6 is complete if still present. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md] [Source: ces-ddr-platform/ces-backend/src/repository/events.py]

Story 2.2 established upload/queue flow and concurrency-safe queue position handling. Do not move AI work into upload request path; cost and embeddings happen in the background pipeline after extraction. [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

Story 2.3 established `src/services/pipeline/pre_split.py` and `src/services/pipeline_service.py` instead of the earlier `src/pipeline/` path. Continue this implemented layout. [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]

Story 2.4 established `GeminiDDRExtractor`, `DDRExtractionValidator`, `ExtractionResult`, success/warning/failure repository methods, and bounded async date extraction. Add cost/embedding to these classes rather than replacing them. Review patches fixed shared AsyncSession concurrency hazards; preserve `_write_lock` behavior around DB writes. [Source: _bmad-output/implementation-artifacts/stories/2-4-per-date-gemini-extraction-pydantic-validation.md] [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]

Story 2.5 established `ProcessingStatusStreamService`, SSE event publishing, startup resume, and frontend processing status. Do not change SSE payloads to report embedding status; downstream UI expects extraction status only. [Source: _bmad-output/implementation-artifacts/stories/2-5-sse-processing-status-stream-frontend-status-hook.md]

### Git Intelligence

Recent commits show extraction validation and DDR upload/schema work:

```text
ac129b2 feat: Implement DDR extraction validation and pipeline service
936b28f feat: implement DDR schema, CRUD operations, and upload service
42309be Implement unified exception handling system with strategies and registry
8c0988b remove go
6617c4d feat: implement authentication and protected routes
```

Current uncommitted changes are substantial and include Story 2.5. Do not revert unrelated modified files. [Source: git log --oneline -5] [Source: git status --short]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-backend/pyproject.toml
ces-ddr-platform/ces-backend/src/api/endpoints.py
ces-ddr-platform/ces-backend/src/api/routes/v1/pipeline.py
ces-ddr-platform/ces-backend/src/config/settings/base.py
ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/src/services/pipeline/extract.py
ces-ddr-platform/ces-backend/src/services/pipeline/embedding.py
ces-ddr-platform/ces-backend/src/services/pipeline/cost.py
ces-ddr-platform/ces-backend/src/services/pipeline_service.py
ces-ddr-platform/ces-backend/tests/test_pipeline_cost.py
ces-ddr-platform/ces-backend/tests/test_time_log_embedding.py
ces-ddr-platform/ces-backend/tests/test_pipeline_cost_route.py
ces-ddr-platform/ces-backend/tests/test_ddr_extraction_pipeline.py
ces-ddr-platform/ces-backend/tests/test_ddr_schema.py
```

Adjust names only to fit local patterns. Do not create frontend files for this backend story. Do not modify `src/components/ui/` primitives. [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]

### Testing Requirements

Run backend validation from `ces-ddr-platform/ces-backend/`:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Tests must not require real Gemini, Qdrant, uploaded PDFs, network calls, or real `.env` secrets. Use fake Google embedding clients, fake Qdrant clients, and fake repositories/sessions where DB transaction behavior is the subject. [Source: AGENTS.md] [Source: ces-ddr-platform/ces-backend/tests/test_ddr_extraction_pipeline.py]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Processing/Date Status Values]
- [Source: _bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md#Cost Model]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-4-per-date-gemini-extraction-pydantic-validation.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-5-sse-processing-status-stream-frontend-status-hook.md]
- [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]
- [Source: ces-ddr-platform/ces-backend/src/services/pipeline/extract.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/models/schemas/ddr.py]
- [Source: https://ai.google.dev/gemini-api/docs/tokens?lang=python]
- [Source: https://ai.google.dev/gemini-api/docs/models/gemini]
- [Source: https://googleapis.github.io/python-genai/genai.html]
- [Source: https://python-client.qdrant.tech/qdrant_client.async_qdrant_client]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
