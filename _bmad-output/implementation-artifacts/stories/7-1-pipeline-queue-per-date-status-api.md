# Story 7.1: Pipeline Queue & Per-Date Status API

Status: ready-for-dev

## Story

As a CES staff member,
I want to view the processing queue showing all DDR jobs and per-date extraction status for any DDR,
so that I can track what's running, what completed, and what needs attention at a glance.

## Acceptance Criteria

1. Given `GET /api/pipeline/queue` is called with a valid JWT, when DDR jobs exist, then HTTP 200 returns a JSON array sorted by `created_at` descending. Each item includes `id`, `file_path`, `status`, `well_name`, `created_at`, and `date_counts` with `{ success, warning, failed, total }`.
2. Given `GET /api/pipeline/queue` is called, `date_counts` is derived from related `ddr_dates.status` rows per DDR. `total` counts all date rows, including `queued`; `success`, `warning`, and `failed` count exact matching statuses only.
3. Given no DDRs exist, when `GET /api/pipeline/queue` is called with a valid JWT, then HTTP 200 returns `[]`.
4. Given `GET /api/ddrs/{ddr_id}/dates` is called with a valid JWT and the DDR exists, when `ddr_dates` rows exist for that DDR, then HTTP 200 returns a JSON array sorted by `date` ascending. Each item includes only `date`, `status`, and `created_at`.
5. Given `GET /api/ddrs/{ddr_id}/dates` is called with a valid JWT and the DDR does not exist, then HTTP 404 returns `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`.
6. Given either new endpoint is called without authentication, then HTTP 401 is returned by existing JWT authentication.
7. Given OpenAPI is generated, then `/api/pipeline/queue` and `/api/ddrs/{ddr_id}/dates` appear in `/openapi.json`.
8. Existing endpoints and frontend contracts remain intact: `/api/pipeline/cost`, `/api/monitor/queue`, `/api/ddrs`, `/api/ddrs/{ddr_id}`, and `/api/ddrs/{ddr_id}/status/stream` must not regress.

## Tasks / Subtasks

- [ ] Add backend response schemas for Story 7.1 contracts (AC: 1, 4)
  - [ ] Add `PipelineDateCounts` and `PipelineQueueItemResponse` schemas in a backend schema module that matches existing organization.
  - [ ] Add a lean `DDRDateStatusResponse` schema with only `date`, `status`, and `created_at`.
  - [ ] Keep existing `QueueItemResponse` unchanged because `/api/monitor/queue` and frontend monitor code use its flat `date_total/date_success/date_failed/date_warning` fields.
- [ ] Add reusable queue/status service logic (AC: 1, 2, 3)
  - [ ] Create or extend a service class, preferably `src/services/pipeline/queue.py` with `PipelineQueueStatusService`.
  - [ ] Reuse `DDRCRUDRepository.read_all_descending()` for DDR ordering.
  - [ ] Reuse `DDRDateCRUDRepository.read_dates_by_ddr_id()` for date rows; do not add raw SQL in routes.
  - [ ] Return `date_counts.total = len(rows)`; `queued` affects only total.
- [ ] Implement `GET /api/pipeline/queue` (AC: 1, 2, 3, 6, 7)
  - [ ] Update `src/api/routes/v1/pipeline.py`.
  - [ ] Keep existing `/pipeline/cost` logic untouched.
  - [ ] Use `Depends(jwt_authentication)` and repository dependencies.
  - [ ] Return direct array, not `{ items, total }`.
- [ ] Implement `GET /api/ddrs/{ddr_id}/dates` (AC: 4, 5, 6, 7)
  - [ ] Update `src/api/routes/v1/ddr.py`.
  - [ ] Verify DDR exists with `DDRCRUDRepository.read_by_id()` before returning dates.
  - [ ] Return exact 404 shape with `JSONResponse` or the project exception path if it already produces the exact shape.
  - [ ] Do not expose `raw_response`, `final_json`, `error_log`, `source_page_numbers`, `updated_at`, or `ddr_id` on this list endpoint.
- [ ] Add backend tests (AC: 1-8)
  - [ ] Create `tests/test_pipeline_queue_route.py` following existing `TestClient` + dependency override style.
  - [ ] Test auth required for both endpoints.
  - [ ] Test queue empty array.
  - [ ] Test queue response shape and ordering by `created_at` descending.
  - [ ] Test `date_counts` aggregation with `success`, `warning`, `failed`, and `queued` rows.
  - [ ] Test date list response shape, ascending `date` ordering, and no raw/error payload fields.
  - [ ] Test missing DDR returns exact standard 404 shape.
  - [ ] Test OpenAPI includes both new paths.
- [ ] Run backend quality gates from activated UV virtualenv (AC: 8)
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && pytest`
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && ruff check src tests`

## Dev Notes

### Critical Context

- This is backend API story only. Do not change frontend monitor UI in this story.
- The repo already has a monitor queue endpoint at `/api/monitor/queue`. Story 7.1 requires a new API contract at `/api/pipeline/queue`; do not repurpose or break `/api/monitor/queue`.
- Current frontend calls `/monitor/queue` and expects flat fields. Preserve that contract until Story 7.4 changes UI.
- No database migration needed. Required data already exists in `ddrs` and `ddr_dates`.
- All timestamps are epoch integers. Do not introduce datetime objects in API responses.
- All endpoints are protected. Use existing `jwt_authentication` dependency.
- Keep route handlers thin: dependency/session/auth in route, business aggregation in service, persistence in repositories.

### Existing Code to Reuse

- `ces-ddr-platform/ces-backend/src/api/routes/v1/pipeline.py`
  - Current state: `APIRouter(prefix="/pipeline")` with `GET /cost` only.
  - Change: add `GET /queue` beside `/cost`.
  - Preserve: `/pipeline/cost` response shape `{ total_cost_usd, total_runs, period }` and tests.
- `ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py`
  - Current state: DDR list/detail/status stream/upload/reprocess routes. `GET /{ddr_id}` embeds full `dates` list using `DDRDateInResponse`.
  - Change: add dedicated `GET /{ddr_id}/dates` returning lean date status list.
  - Preserve: upload, list, detail, occurrences, SSE stream, retry/reprocess routes.
- `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py`
  - `DDRCRUDRepository.read_all_descending()` already sorts DDRs by `created_at.desc()`.
  - `DDRDateCRUDRepository.read_dates_by_ddr_id()` already sorts date rows by `date.asc()`.
  - Use these methods before adding new repository methods.
- `ces-ddr-platform/ces-backend/src/models/db/ddr.py`
  - `DDR` fields available: `id`, `file_path`, `status`, `well_name`, `created_at`, `updated_at`, plus optional metadata.
  - `DDRDate` fields available: `date`, `status`, `raw_response`, `final_json`, `error_log`, `source_page_numbers`, `created_at`, `updated_at`.
  - Do not expose raw/error JSON on Story 7.1 date list. Story 7.2 owns error-log detail.
- `ces-ddr-platform/ces-backend/src/services/monitor.py`
  - Current `MonitorService.queue()` already aggregates queue counts but returns flat monitor schema and depends on correction repository through constructor.
  - Prefer new pipeline queue service or a clean shared method over coupling `/pipeline` to monitor/corrections concerns.
- `ces-ddr-platform/ces-backend/src/models/schemas/monitor.py`
  - `QueueItemResponse` is flat and used by `/monitor/queue`; do not modify in a breaking way.
- `ces-ddr-platform/ces-backend/tests/test_pipeline_cost_route.py`
  - Reuse its dependency override pattern for pipeline route tests.
- `ces-ddr-platform/ces-backend/tests/test_ddr_status_stream.py`
  - Reuse its DDR/DDRDate stub style and exact 404 shape expectation.

### API Contract Details

`GET /api/pipeline/queue` response item:

```json
{
  "id": "ddr-1",
  "file_path": "/app/uploads/ddr-1.pdf",
  "status": "processing",
  "well_name": "Pembina 14-25",
  "created_at": 1770000000,
  "date_counts": {
    "success": 2,
    "warning": 1,
    "failed": 1,
    "total": 5
  }
}
```

`GET /api/ddrs/{ddr_id}/dates` response item:

```json
{
  "date": "20241031",
  "status": "success",
  "created_at": 1770000000
}
```

Status values:

- DDR status: `queued`, `processing`, `complete`, `failed`.
- Date status currently includes `queued`, `success`, `warning`, `failed` in code. Historical docs sometimes list only `success/warning/failed`; do not remove `queued` because upload/pipeline uses it.

### Architecture Compliance

- Backend standard: Python FastAPI `src/` layout, `decouple + BackendBaseSettings`, async SQLAlchemy repository pattern, Alembic under `src/repository/migrations`, pytest, Ruff.
- No `os.getenv` or `os.environ.get`.
- No loose DB helpers or raw DB access in route files.
- No blocking sync SDK calls in async routes. This story should not call external SDKs.
- API success responses are direct objects/arrays. Error shape is `{ error, code, details }`.
- Every protected route must reject unauthenticated requests.

### Regression Guardrails

- Do not change `DDRDateInResponse`; it is used by existing DDR detail and retry responses.
- Do not change `/api/ddrs/{ddr_id}` response shape.
- Do not change `/api/ddrs/{ddr_id}/status/stream`; SSE is already implemented and tested.
- Do not modify processing pipeline status transitions.
- Do not add frontend API calls yet. Story 7.4 will consume queue/status UI.
- Do not expose full `error_log` through `/ddrs/{ddr_id}/dates`; that belongs to Story 7.2.
- Do not introduce pagination for `/pipeline/queue`; AC requires list of all DDR jobs.

### Testing Requirements

- Tests must run from `ces-ddr-platform/ces-backend` with activated UV virtualenv.
- Use existing `backend_app.dependency_overrides` pattern and clear overrides in `finally`.
- Stub repositories can use `SimpleNamespace` rows as existing tests do.
- Verify no leaked fields in lean date response by asserting exact JSON.
- Verify OpenAPI generated paths include `/api/pipeline/queue` and `/api/ddrs/{ddr_id}/dates`.

### Latest Technical Notes

- FastAPI `response_model` filters returned objects to declared fields; use response models on both new endpoints to prevent accidental leakage of `raw_response` or `error_log`.
- Avoid duplicate/ambiguous route templates. More specific nested route `/ddrs/{ddr_id}/dates` is distinct from `/ddrs/{ddr_id}`; keep path names unique in OpenAPI.

### Project Structure Notes

- Backend root: `ces-ddr-platform/ces-backend`.
- Likely updated files:
  - `src/api/routes/v1/pipeline.py`
  - `src/api/routes/v1/ddr.py`
  - `src/models/schemas/ddr.py` or a dedicated existing schema module for date status response
  - `src/models/schemas/monitor.py` or a dedicated pipeline schema module for queue response
  - `src/services/pipeline/queue.py` if creating a new service class
- Likely new tests:
  - `tests/test_pipeline_queue_route.py`

### References

- Story source: `_bmad-output/planning-artifacts/epics.md#Story-7.1-Pipeline-Queue--Per-Date-Status-API`
- Architecture API patterns: `_bmad-output/planning-artifacts/architecture.md#API--Communication-Patterns`
- Backend structure rule: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md#Implementation-Handoff`
- RBAC change context: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md#Implementation-Handoff`
- Current pipeline router: `ces-ddr-platform/ces-backend/src/api/routes/v1/pipeline.py`
- Current DDR router: `ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py`
- Current repositories: `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py`
- Current DDR models: `ces-ddr-platform/ces-backend/src/models/db/ddr.py`
- Current schema constants: `ces-ddr-platform/ces-backend/src/models/schemas/ddr.py`
- Current monitor queue implementation: `ces-ddr-platform/ces-backend/src/services/monitor.py`

## Story Context Completion

Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Agent Model Used

TBD by dev agent

### Debug Log References

### Completion Notes List

### File List
