# Story 7.2: Error Log & Per-Date Re-run API

Status: ready-for-dev

## Story

As a CES staff member,
I want to view the raw error log for any failed date and re-run extraction with an optional manual date override,
so that extraction failures are diagnosable and recoverable without a code deploy.

## Acceptance Criteria

1. Given `GET /api/ddrs/{ddr_id}/dates/{date}` is called with a valid JWT and the `ddr_dates` row exists, then HTTP 200 returns a JSON object with `id`, `ddr_id`, `date`, `status`, `error_log` (full JSONB), `raw_response` (full JSONB), `final_json`, `source_page_numbers`, `created_at`, `updated_at`.
2. Given `GET /api/ddrs/{ddr_id}/dates/{date}` is called and no matching `ddr_dates` row exists, then HTTP 404 returns `{ "error": "Date not found", "code": "NOT_FOUND", "details": {} }`.
3. Given `GET /api/ddrs/{ddr_id}/dates/{date}` is called without authentication, then HTTP 401 is returned.
4. Given `POST /api/ddrs/{ddr_id}/dates/{date}/rerun` is called with body `{}` and the date row is `failed` or `warning`, then HTTP 202 is returned immediately with `{ "status": "accepted" }`. The row status resets to `"queued"` and extraction re-triggers asynchronously using the same PDF chunk.
5. Given `POST /api/ddrs/{ddr_id}/dates/{date}/rerun` with `{ "manual_date_override": "20241031" }`, then the pipeline uses `"20241031"` as the date string for extraction context (chunk still keyed by the original `date` URL param). The override is logged in `error_log` before re-run begins: `{ "manual_override": "20241031", "triggered_at": <epoch> }`.
6. Given `POST /api/ddrs/{ddr_id}/dates/{date}/rerun` is called for a non-`failed`/`warning` date, then HTTP 400 returns `{ "error": "Date is not retryable", "code": "DATE_NOT_RETRYABLE", "details": {} }`.
7. Given re-run completes successfully, then `ddr_dates.status` updates to `"success"`, new occurrences are written, and SSE `date_complete` event fires if client is still connected.
8. Given `POST /api/ddrs/{ddr_id}/dates/{date}/rerun` is called without authentication, then HTTP 401 is returned.
9. Given either new endpoint is called, OpenAPI schema at `/openapi.json` includes both new paths.
10. Existing endpoints must not regress: `POST /api/ddrs/{ddr_id}/dates/{date}/retry`, `GET /api/ddrs/{ddr_id}`, `GET /api/ddrs/{ddr_id}/dates`, `GET /api/pipeline/queue`, `GET /api/pipeline/cost`.

## Tasks / Subtasks

- [ ] Add repository read method for single date without lock (AC: 1, 2)
  - [ ] In `src/repository/crud/ddr.py`, add `DDRDateCRUDRepository.read_date_by_ddr_and_date(ddr_id, date) -> DDRDate | None` — plain SELECT without `with_for_update()`. Do NOT modify `read_date_for_update`; it is already used by `prepare_retry`.
- [ ] Add new request/response schemas (AC: 4, 5)
  - [ ] In `src/models/schemas/ddr.py`, add `DDRDateRerunRequest(BaseSchemaModel)` with `manual_date_override: str | None = None`.
  - [ ] Add `DDRDateRerunAcceptedResponse(BaseSchemaModel)` with `status: str` (always `"accepted"`).
  - [ ] Do NOT create a new detail response schema. `DDRDateInResponse` already carries all fields (`error_log`, `raw_response`, `date`, `status`, `created_at`, etc.) — use it directly for the GET endpoint.
- [ ] Add `prepare_rerun` and `execute_rerun` to `PreSplitPipelineService` (AC: 4, 5, 6, 7)
  - [ ] Add `prepare_rerun(self, ddr_id, date, manual_date_override=None) -> DDRDate`:
    - Call `self.ddr_date_repository.read_date_for_update(ddr_id, date)` (already exists, already used by `prepare_retry`).
    - Raise `EntityDoesNotExist("date_not_found")` if row is `None`.
    - Raise `BadRequestException("date_not_retryable")` if `row.status` not in `(FAILED, WARNING)`.
    - If `manual_date_override` is provided, call a new `ddr_date_repository` method to patch `error_log` with `{"manual_override": manual_date_override, "triggered_at": <epoch int>}` before resetting status (do not lose existing error_log fields — merge/append the override key).
    - Reset status to `QUEUED` via existing `self.ddr_date_repository.update_status(row, DDRDateStatus.QUEUED)`.
    - Update DDR status to `PROCESSING` via existing `self.ddr_repository.update_status(ddr, DDRStatus.PROCESSING)`.
    - Return row.
  - [ ] Add `execute_rerun(self, ddr_id, date, effective_date=None) -> None`:
    - `effective_date = effective_date or date` — the date string passed to the extractor.
    - Download chunk via existing `self.storage_service.download_chunk(ddr_id, date)` (always keyed by original `date`).
    - Get `date_page_numbers` via existing `self._page_numbers_for_rows(ddr_id, [row])`.
    - Call existing `self._process_one_date(extractor, row, effective_date, chunk_bytes, original_page_numbers=...)`.
    - After processing: read all rows, extract metadata, update well metadata, finalize DDR status — **copy the post-processing steps from existing `execute_retry` verbatim** (lines 143–161 in `pipeline_service.py`). Do NOT reimplement this logic; just replicate the same call sequence.
  - [ ] Do NOT modify `prepare_retry` or `execute_retry`. These are used by the existing `/retry` endpoint.
- [ ] Add `error_log` merge helper to `DDRDateCRUDRepository` (AC: 5)
  - [ ] Add `patch_error_log(self, ddr_date, extra: dict) -> DDRDate` — reads current `ddr_date.error_log` (may be `None`), merges `extra` keys into it, writes back. Use async SQLAlchemy session commit.
- [ ] Implement `GET /api/ddrs/{ddr_id}/dates/{date}` (AC: 1, 2, 3, 9)
  - [ ] Add route to `src/api/routes/v1/ddr.py` **before** `GET /{ddr_id}` in file order to avoid path-template ambiguity.
  - [ ] Validate `date` param with `Path(pattern=r"^\d{8}$")` as existing retry route does.
  - [ ] Use `ddr_date_repository.read_date_by_ddr_and_date(ddr_id, date)`.
  - [ ] Return `DDRDateInResponse.model_validate(row)` on success.
  - [ ] Return exact 404 `JSONResponse` on not found: `{"error": "Date not found", "code": "NOT_FOUND", "details": {}}`.
  - [ ] Use `response_model=DDRDateInResponse` so FastAPI filters unexpected fields.
- [ ] Implement `POST /api/ddrs/{ddr_id}/dates/{date}/rerun` (AC: 4, 5, 6, 7, 8, 9)
  - [ ] Add route to `src/api/routes/v1/ddr.py`.
  - [ ] Accept `payload: DDRDateRerunRequest = Body(default_factory=DDRDateRerunRequest)`.
  - [ ] Call `await service.prepare_rerun(ddr_id, date, payload.manual_date_override)`.
  - [ ] Catch `EntityDoesNotExist` → return 404 `NOT_FOUND` shape.
  - [ ] Catch `BadRequestException` → return 400 `DATE_NOT_RETRYABLE` shape.
  - [ ] Add `background_tasks.add_task(service.execute_rerun, ddr_id, date, payload.manual_date_override)`.
  - [ ] Return `DDRDateRerunAcceptedResponse(status="accepted")` with HTTP 202.
  - [ ] Use `get_pipeline_service` dependency (already defined in `services.py`) — do NOT create a new dependency factory.
- [ ] Add backend tests (AC: 1–10)
  - [ ] Create `tests/test_ddr_date_rerun_route.py` following `test_pipeline_cost_route.py` dependency-override style and `test_ddr_status_stream.py` stub patterns.
  - [ ] Test GET requires auth (401).
  - [ ] Test GET returns `DDRDateInResponse` shape including `error_log` and `raw_response` fields.
  - [ ] Test GET 404 for non-existent date with exact error shape.
  - [ ] Test POST rerun requires auth (401).
  - [ ] Test POST rerun returns 202 with `{"status": "accepted"}`.
  - [ ] Test POST rerun 400 for non-retryable status with exact error shape.
  - [ ] Test POST rerun 404 for non-existent date.
  - [ ] Test POST rerun with `manual_date_override` calls `prepare_rerun` with override value.
  - [ ] Test OpenAPI includes both new paths.
- [ ] Run quality gates (AC: 10)
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && pytest`
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && ruff check src tests`

## Dev Notes

### Critical Context

- Backend-only story. No frontend changes.
- Two new endpoints: `GET /api/ddrs/{ddr_id}/dates/{date}` and `POST /api/ddrs/{ddr_id}/dates/{date}/rerun`.
- The `/rerun` endpoint is distinct from the existing `/retry` endpoint — both will coexist. Do NOT delete or modify `/retry`.
- All timestamps are epoch integers. No datetime objects in API responses.

### DO NOT REIMPLEMENT — Reuse These

| Existing thing | Where | How to use in 7-2 |
|---|---|---|
| `DDRDateInResponse` | `src/models/schemas/ddr.py` | Use directly for GET detail response — already has `error_log`, `raw_response`, `date`, `status`, `created_at` |
| `read_date_for_update` | `DDRDateCRUDRepository` | Call from `prepare_rerun` for the write-side lock (same as `prepare_retry`) |
| `read_dates_by_ddr_id` | `DDRDateCRUDRepository` | Already sorted by `date` asc; reuse in `execute_rerun` post-processing |
| `prepare_retry` logic | `PreSplitPipelineService` | `prepare_rerun` extends it — same status check, same `update_status` calls, plus override logging |
| `execute_retry` post-processing | `PreSplitPipelineService` (lines 143–161) | Copy verbatim into `execute_rerun`; do not invent alternative finalization logic |
| `_process_one_date` | `PreSplitPipelineService` | Call from `execute_rerun` with `effective_date` as the `date` param |
| `storage_service.download_chunk(ddr_id, date)` | `StorageService` | Always use original URL `date` as chunk key, even with override |
| `_page_numbers_for_rows` | `PreSplitPipelineService` | Reuse in `execute_rerun` — identical to `execute_retry` |
| `get_pipeline_service` | `src/api/dependencies/services.py` | Reuse as-is for both new routes — already wires all repos and services |
| `jwt_authentication` | `src/securities/authorizations/jwt_authentication.py` | Same `Depends(jwt_authentication)` as every other protected route |
| `BadRequestException`, `EntityDoesNotExist` | `src/utilities/exceptions` | Same exception classes as `prepare_retry` uses |
| `BackgroundTasks` pattern | `ddr.py` retry route | Same pattern: `background_tasks.add_task(service.execute_rerun, ...)` |

### Route Order Warning

FastAPI registers routes in declaration order. In `ddr.py`, `GET /{ddr_id}` is currently the catch-all detail route. Add `GET /{ddr_id}/dates/{date}` BEFORE `GET /{ddr_id}` in the file to ensure FastAPI matches the more-specific template first. Existing routes already set this precedent: `GET /{ddr_id}/occurrences` and `GET /{ddr_id}/status/stream` both appear before `GET /{ddr_id}` in the file.

### API Contracts

`GET /api/ddrs/{ddr_id}/dates/{date}` — 200 response (reuses `DDRDateInResponse`):
```json
{
  "id": "uuid",
  "ddr_id": "uuid",
  "date": "20241031",
  "status": "failed",
  "error_log": { "code": "EXTRACTION_FAILED", "detail": "..." },
  "raw_response": { "text": "..." },
  "final_json": null,
  "source_page_numbers": [3, 4, 5],
  "created_at": 1770000000,
  "updated_at": 1770000000
}
```

`POST /api/ddrs/{ddr_id}/dates/{date}/rerun` — 202 response:
```json
{ "status": "accepted" }
```

`POST /api/ddrs/{ddr_id}/dates/{date}/rerun` — request body (both are valid):
```json
{}
{ "manual_date_override": "20241031" }
```

Error shapes (exact — do not use different keys):
```json
{ "error": "Date not found", "code": "NOT_FOUND", "details": {} }
{ "error": "Date is not retryable", "code": "DATE_NOT_RETRYABLE", "details": {} }
```

### manual_date_override Logic

When `manual_date_override` is set:
1. Read current `ddr_date.error_log` (may be `None` → treat as `{}`).
2. Merge in `{ "manual_override": "20241031", "triggered_at": <epoch int> }` — do not wipe existing keys.
3. Write updated `error_log` back via `patch_error_log`.
4. Then reset status to `queued`.
5. In `execute_rerun`, pass `effective_date = manual_date_override` to `_process_one_date`. The storage chunk download still uses original `date` URL param.

### 400 Error for Non-Retryable Status

The existing `prepare_retry` already raises `BadRequestException("date_not_retryable")` for non-FAILED/WARNING status. Translate that into a `JSONResponse` in the route handler (same as how other routes translate exceptions). Do not use FastAPI exception handlers that don't exist yet — use explicit try/except in the route.

### Existing `/retry` Route — Do Not Touch

`POST /api/ddrs/{ddr_id}/dates/{date}/retry` (existing):
- Returns `DDRDateInResponse` (synchronous row snapshot).
- No `manual_date_override` support.
- Status 200.

`POST /api/ddrs/{ddr_id}/dates/{date}/rerun` (new story 7-2):
- Returns `{ "status": "accepted" }` with 202.
- Supports `manual_date_override`.

These are **two different endpoints** that will coexist. The retry route and `prepare_retry`/`execute_retry` methods stay completely unchanged.

### Architecture Compliance

- Python FastAPI `src/` layout, `decouple + BackendBaseSettings`, async SQLAlchemy repository pattern, pytest, Ruff.
- No `os.getenv` or `os.environ.get`.
- No raw DB access in routes — all DB work in repository methods.
- No blocking sync calls in async routes.
- Routes stay thin: auth + dependency injection + service call + response serialization only.
- Use `response_model=` on routes to prevent accidental field leakage.

### Regression Guardrails

- Do not change `DDRDateInResponse` — it is used by detail, retry, and stream routes.
- Do not change `DDRDateCRUDRepository.read_date_for_update` — used by `prepare_retry`.
- Do not change `prepare_retry` or `execute_retry` — used by the existing `/retry` endpoint.
- Do not change `GET /api/ddrs/{ddr_id}` response shape — frontend monitor depends on it.
- Do not change `GET /api/ddrs/{ddr_id}/dates` (Story 7-1 endpoint) — its lean response shape must remain.
- Do not expose SSE stream or pipeline internal state through new endpoints.

### Testing Pattern

Follow `test_pipeline_cost_route.py`:
- `backend_app.dependency_overrides[jwt_authentication] = override_auth`
- `backend_app.dependency_overrides[route_dependency(...)] = StubService`
- Always clear overrides in `finally` block

Follow `test_ddr_status_stream.py` for DDR/DDRDate stub style:
- Use `SimpleNamespace` rows with all needed fields.
- Assert exact JSON response shape.

For `prepare_rerun` / `execute_rerun` service unit tests (optional, lower priority):
- Stub `ddr_date_repository` and `ddr_repository` with `SimpleNamespace` objects as done in `test_ddr_extraction_pipeline.py`.

### Project Structure

Updated files:
- `src/api/routes/v1/ddr.py` — add GET date detail + POST rerun routes
- `src/models/schemas/ddr.py` — add `DDRDateRerunRequest`, `DDRDateRerunAcceptedResponse`
- `src/repository/crud/ddr.py` — add `read_date_by_ddr_and_date`, `patch_error_log` to `DDRDateCRUDRepository`
- `src/services/pipeline_service.py` — add `prepare_rerun`, `execute_rerun` to `PreSplitPipelineService`

New test file:
- `tests/test_ddr_date_rerun_route.py`

### References

- Story source: `_bmad-output/planning-artifacts/epics.md#Story-7.2`
- Existing retry route: `ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py` (`retry_ddr_date`)
- Existing prepare/execute retry: `ces-ddr-platform/ces-backend/src/services/pipeline_service.py` (lines 114–166)
- DDRDate CRUD: `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py` (`DDRDateCRUDRepository`)
- Schemas: `ces-ddr-platform/ces-backend/src/models/schemas/ddr.py`
- Pipeline service dependency: `ces-ddr-platform/ces-backend/src/api/dependencies/services.py` (`get_pipeline_service`)
- Test pattern: `ces-ddr-platform/ces-backend/tests/test_pipeline_cost_route.py`
- Stub pattern: `ces-ddr-platform/ces-backend/tests/test_ddr_status_stream.py`

## Story Context Completion

Ultimate context engine analysis completed — comprehensive developer guide created. Key focus: reuse of existing `DDRDateInResponse`, `prepare_retry` pattern, `execute_retry` post-processing, and `get_pipeline_service` dependency. No reimplementation of retry logic.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
