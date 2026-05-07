# Story 2.2: PDF Upload Endpoint & Processing Queue

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want to upload a DDR PDF and have it immediately queued for processing,
so that extraction starts without waiting and I get acknowledgement within 1 second.

## Acceptance Criteria

1. Given an authenticated user submits a PDF via `POST /ddrs/upload` as `multipart/form-data`, when the request is received, then the PDF is saved to `/app/uploads/{uuid}.pdf`, a `ddrs` row is created with `status: "queued"` and `file_path` set, a `processing_queue` row is inserted for the DDR, HTTP 201 returns within 1 second with `{ "id": "<uuid>", "status": "queued" }`, and a FastAPI/asyncio background task is dispatched without blocking the response.
2. Given a non-PDF file is uploaded, when the upload endpoint validates the file, then HTTP 400 returns `{ "error": "Only PDF files accepted", "code": "VALIDATION_ERROR", "details": {} }`, and no file is saved to disk.
3. Given `GET /ddrs` is called by an authenticated user, when the response is returned, then all DDRs are returned with `id`, `file_path`, `status`, `well_name`, and `created_at`, sorted by `created_at` descending.
4. Given `GET /ddrs/:id` is called with a valid DDR id, when the DDR exists, then DDR detail returns `id`, `status`, `file_path`, `well_name`, and `created_at`.
5. Given `GET /ddrs/:id` is called with a missing DDR id, when no row exists, then HTTP 404 returns `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`.
6. Given OpenAPI generation is active, when `GET /docs` is opened, then `/auth/login`, `/ddrs`, `/ddrs/upload`, and `/ddrs/:id` are documented.

## Tasks / Subtasks

- [x] Confirm Story 2.1 schema exists before route work (AC: 1, 3-5)
  - [x] Verify `DDR` and `ProcessingQueue` ORM models exist under `ces-backend/src/models/db/ddr.py`.
  - [x] Verify `DDRCRUDRepository` and `ProcessingQueueCRUDRepository` exist under `ces-backend/src/repository/crud/ddr.py`.
  - [x] Verify Alembic migration for `ddrs` and `processing_queue` exists and uses epoch `BIGINT` timestamps.
  - [x] If Story 2.1 has not been implemented yet, implement or block on it first; do not duplicate schema classes in this story.
- [x] Add upload storage configuration (AC: 1-2)
  - [x] Add an upload directory setting to `BackendBaseSettings`, loaded with `decouple + BackendBaseSettings`, defaulting to `/app/uploads`.
  - [x] Do not use `os.getenv`, `os.environ.get`, or hardcoded environment reads.
  - [x] Keep timestamps as epoch integers.
- [x] Add DDR API schemas (AC: 1-5)
  - [x] Extend `ces-backend/src/models/schemas/ddr.py` with upload response, list item, and detail response schemas.
  - [x] Keep API fields snake_case: `id`, `file_path`, `status`, `well_name`, `created_at`.
  - [x] Return direct object/list responses, not wrapper models, unless existing route contract tests prove the local API has already standardized otherwise.
- [x] Add upload and queue service classes (AC: 1-2)
  - [x] Create `ces-backend/src/services/ddr.py` or equivalent service module with class-based workflow ownership.
  - [x] Validate uploaded file by content type and filename suffix; accept `.pdf` and `.PDF`, reject anything else before writing.
  - [x] Save to `{upload_dir}/{uuid}.pdf`; generated filename must not include user-supplied path segments.
  - [x] Write file without blocking the event loop. If using sync file I/O, wrap it with `asyncio.to_thread()`.
  - [x] Create the `ddrs` and `processing_queue` rows atomically in one service/repository transaction. If file write succeeds but DB insert fails, remove the saved file.
  - [x] Calculate queue `position` using repository logic that is concurrency-safe enough for current single-process V1. Do not create loose query helpers.
  - [x] Dispatch a placeholder background pipeline task with FastAPI `BackgroundTasks` or an app-level asyncio task hook, but do not implement pre-splitting, Gemini extraction, SSE, occurrence generation, or cost tracking in this story.
- [x] Add DDR routes (AC: 1-6)
  - [x] Create `ces-backend/src/api/routes/v1/ddr.py` with `APIRouter(prefix="/ddrs", tags=["DDRs"])`.
  - [x] Register the router in `ces-backend/src/api/endpoints.py`.
  - [x] Protect every DDR route with existing JWT verification dependency; `/api/auth/login` remains the only unauthenticated API route.
  - [x] Implement `POST /ddrs/upload` with `UploadFile` and `BackgroundTasks`; response status must be 201.
  - [x] Implement `GET /ddrs` sorted by `created_at` descending.
  - [x] Implement `GET /ddrs/{id}` using FastAPI path syntax while preserving documented URL shape `/ddrs/:id`.
- [x] Align expected error response shape for this story (AC: 2, 5)
  - [x] Add or reuse domain exceptions so upload validation returns exactly `{ "error": "Only PDF files accepted", "code": "VALIDATION_ERROR", "details": {} }`.
  - [x] Add or reuse not-found behavior so missing DDR returns exactly `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`.
  - [x] If current global exception handlers still return the older `ResponseModel` wrapper, update the smallest route-level or handler-level path needed for this story and cover it with tests.
- [x] Add required dependency for multipart uploads (AC: 1, 6)
  - [x] Add `python-multipart` to `ces-backend/pyproject.toml`; FastAPI requires it for `multipart/form-data` file uploads.
  - [x] Do not add Celery, Redis, arq, or a distributed queue for this story.
- [x] Add focused tests (AC: 1-6)
  - [x] Add route contract tests for authenticated upload success, non-PDF rejection, list sorting, detail success, missing DDR 404, and OpenAPI path presence.
  - [x] Mock or fake background dispatch so tests prove response returns without running the extraction pipeline.
  - [x] Test no file remains after validation failure and no DB write happens for invalid files.
  - [x] Test DB failure after file write removes the saved file.
  - [x] Add service/repository tests for queue row creation and descending DDR list order.
  - [x] Keep tests under `ces-backend/tests/`; do not read real `.env` secrets.
- [x] Preserve non-story behavior (AC: all)
  - [x] Do not alter login token contract, password hashing, health route, frontend routes, Gemini extraction, PDF pre-splitter, SSE stream, occurrence generation, Qdrant, corrections, exports, or keyword management.
  - [x] Do not add source-file comments.

### Review Findings

- [x] [Review][Patch] DDR contract tests cannot collect because tests import dependency helpers that route no longer defines [ces-ddr-platform/ces-backend/tests/test_ddr_upload_contract.py:9]
- [x] [Review][Patch] Ruff validation fails on unused and unsorted DDR route imports [ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py:1]
- [x] [Review][Patch] DDR routes use JWT dependency that queries missing `User.is_active`, so authenticated requests fail [ces-ddr-platform/ces-backend/src/securities/authorizations/jwt_authentication.py:63]
- [x] [Review][Patch] PDF validation trusts client filename and content type, so spoofed non-PDF bytes are saved [ces-ddr-platform/ces-backend/src/services/ddr.py:55]
- [x] [Review][Patch] Upload service reads the entire PDF into memory and has no size guard [ces-ddr-platform/ces-backend/src/services/ddr.py:60]
- [x] [Review][Patch] Queue position allocation uses `max(position)+1` without lock or uniqueness, allowing duplicate positions under concurrent uploads [ces-ddr-platform/ces-backend/src/repository/crud/ddr.py:99]
- [x] [Review][Patch] Partial file write failures can leave saved fragments because cleanup starts only after `write_upload` completes [ces-ddr-platform/ces-backend/src/services/ddr.py:42]

## Dev Notes

### Current Sprint State

Epic 2 is in progress. Story 2.1 exists as `ready-for-dev`, not `done`, so implementation of 2.2 must first verify that DDR schema work has landed in the working tree. Current `rg` found no implemented `DDR`, `ProcessingQueue`, `ddrs`, `processing_queue`, `python-multipart`, `pdfs`, or `/app/uploads` code outside story docs and compose notes. Treat Story 2.1 as a hard dependency, not assumed runtime reality. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

### Existing Backend State To Preserve

Backend root is `ces-ddr-platform/ces-backend/`. Current route registration starts in `src/main.py`, includes `src/api/endpoints.py` under `settings.API_PREFIX`, and registered v1 routes live under `src/api/routes/v1/`. Existing auth route is `src/api/routes/v1/auth.py` with `APIRouter(prefix="/auth", tags=["Auth"])`; copy that route style for DDRs. [Source: ces-ddr-platform/ces-backend/src/main.py] [Source: ces-ddr-platform/ces-backend/src/api/endpoints.py] [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/auth.py]

Existing auth helpers are incomplete as route dependencies: `verify_token(token: str, request: Request)` exists, and `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")` exists, but current routes do not yet show a protected-route dependency pattern. The dev agent must wire authentication deliberately, likely using `Depends(oauth2_scheme)` plus `verify_token`, and add tests proving unauthenticated DDR routes return 401. Do not make DDR routes public to satisfy tests quickly. [Source: ces-ddr-platform/ces-backend/src/api/dependencies/auth.py] [Source: _bmad-output/planning-artifacts/architecture.md#API Boundaries]

Repository pattern is class-based. `get_repository()` injects repositories from `src/api/dependencies/repository.py`; repositories extend `BaseCRUDRepository`; `UserCRUDRepository` demonstrates current query style. Extend this pattern for DDR queries and queue insertion instead of adding standalone helpers. [Source: ces-ddr-platform/ces-backend/src/api/dependencies/repository.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/base.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/user.py]

Settings use `decouple.AutoConfig` inside `BackendBaseSettings`. Add upload path config there or a subclass setting that still flows through `BackendBaseSettings`; project rules forbid `os.environ.get` and `os.getenv`. [Source: ces-ddr-platform/ces-backend/src/config/settings/base.py] [Source: ces-ddr-platform/ces-backend/src/config/manager.py]

### API Contract

Routes are served under `/api` because `main.py` includes `api_endpoint_router` with `prefix=settings.API_PREFIX`. Implement router paths as:

```text
POST /api/ddrs/upload
GET  /api/ddrs
GET  /api/ddrs/{id}
```

OpenAPI must show the same effective paths. Architecture docs use no `/v1/` prefix for V1. Do not add `/api/v1`. [Source: ces-ddr-platform/ces-backend/src/main.py] [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]

Success responses are direct JSON object/list payloads:

```json
{ "id": "<uuid>", "status": "queued" }
```

```json
[
  { "id": "<uuid>", "file_path": "/app/uploads/<uuid>.pdf", "status": "queued", "well_name": null, "created_at": 1770000000 }
]
```

Errors required by this story are direct standard error objects:

```json
{ "error": "Only PDF files accepted", "code": "VALIDATION_ERROR", "details": {} }
```

```json
{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }
```

Current exception code has legacy wrapper behavior and malformed `general_exception_handler` fields. Do not let that leak into this story's contract. Fix only the necessary exception/route path and test the exact response bodies. [Source: ces-ddr-platform/ces-backend/src/utilities/exceptions/exceptions.py] [Source: _bmad-output/planning-artifacts/architecture.md#Standard Error Response]

### Upload Storage Rules

Save valid uploads to the Docker-mounted path `/app/uploads/{uuid}.pdf` and store that full path in `ddrs.file_path`. Generate a fresh UUID for the file name; never trust the client filename except for validation. Ensure parent directory creation is handled by service code or container setup. If using `pathlib.Path.mkdir()` or file writes inside async route flow, run sync operations through `asyncio.to_thread()` per project async rules. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2] [Source: _bmad-output/planning-artifacts/architecture.md#Gap 2 - PDF storage]

`ces-ddr-platform/docker-compose.yml` currently declares only `postgres` and `qdrant`; Story 2.1 should add `pdfs`. Story 2.2 must not invent a production backend compose service unless Story 2.1 implementation already established that direction. [Source: ces-ddr-platform/docker-compose.yml] [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md#Docker Compose Guardrails]

### Queue And Background Processing Rules

`processing_queue` must be DB-backed because queue state must survive restarts. On successful upload, create both rows before returning 201. FastAPI `BackgroundTasks` is explicitly sufficient for V1 volume, but durable processing state is still the database row, not in-memory task storage. The background task can be a no-op or status handoff stub until Story 2.3 implements pre-splitting. Do not implement real extraction in this story. [Source: _bmad-output/planning-artifacts/architecture.md#Gap 3 - Python background tasks] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-backend/pyproject.toml
ces-ddr-platform/ces-backend/src/api/endpoints.py
ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py
ces-ddr-platform/ces-backend/src/config/settings/base.py
ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/src/services/ddr.py
ces-ddr-platform/ces-backend/tests/test_ddr_upload_contract.py
```

Story 2.1 may already create some DDR schemas/repositories. If so, extend those files rather than creating duplicates. Do not create root `app/`, `db/queries`, SQL migration folders, Go files, frontend files, or standalone utility modules. [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization] [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md#Project Structure Notes]

### Library And Framework Requirements

Current backend dependencies pin FastAPI `>=0.135.1,<0.136.0`, SQLAlchemy `>=2.0.0,<3.0.0`, Alembic `>=1.18.4,<2.0.0`, and Python `>=3.12`. Stay inside those ranges. Add only `python-multipart` for upload form parsing unless tests expose a real gap. [Source: ces-ddr-platform/ces-backend/pyproject.toml]

FastAPI official docs require `python-multipart` for file uploads sent as form data and show `UploadFile` for upload endpoints. FastAPI official background task docs support declaring `BackgroundTasks` as a path operation parameter and adding work after the response is prepared. Use those APIs; do not add a broker for V1. [Source: https://fastapi.tiangolo.com/tutorial/request-files/] [Source: https://fastapi.tiangolo.com/tutorial/background-tasks/]

### Async Correctness

All route handlers must be `async def`. All SQLAlchemy repository calls must be awaited. Any sync file I/O, file deletion, directory creation, or SDK call introduced by this story must be wrapped in `asyncio.to_thread()`. Do not block the event loop while writing uploaded PDFs. [Source: AGENTS.md Backend Guidelines] [Source: _bmad-output/planning-artifacts/architecture.md#Async Pattern]

### Previous Story Intelligence

Story 2.1 defines schema, repository, migration, and Docker volume guardrails. Reuse its DDR status constants and model names if implemented. It also resolved the timestamp conflict: use epoch `BIGINT`, not `TIMESTAMPTZ` or Python `datetime`, even though original Epic 2 text says timestamp types. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

Story 1.4 review intelligence from 2.1 still applies: keep scope tight, avoid raw implementation leaks, and obey no source-file comments. Story 2.2 should not start frontend upload UI; UX upload progress belongs to Story 2.5/frontend integration unless explicitly pulled forward. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md#Previous Story Intelligence]

### Git Intelligence

Recent commits:

```text
42309be Implement unified exception handling system with strategies and registry
8c0988b remove go
6617c4d feat: implement authentication and protected routes
25f66e9 Implement JWT authentication and user management in Go and Python backends
2932cd9 migration setup
```

Treat Python backend as canonical. Do not restore removed Go code. The latest exception work is user/project work; adjust it narrowly if needed for exact DDR error contracts, and do not revert unrelated exception changes. [Source: git log -5 --oneline]

### Testing Requirements

Run backend checks from `ces-ddr-platform/ces-backend/` with the UV virtualenv activated:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Use `TestClient` or `httpx` patterns already present in tests. Mock auth only if tests also prove real JWT dependency rejects unauthenticated calls. Use temp directories for upload path tests by overriding settings or service constructor inputs; do not write test PDFs to `/app/uploads`. [Source: ces-ddr-platform/ces-backend/tests/test_health.py] [Source: ces-ddr-platform/ces-backend/tests/test_auth_contract.py]

### Project Structure Notes

No `project-context.md` file exists in the project despite workflow persistent facts requesting it. Use `AGENTS.md` rules as the local project authority: decouple settings, class/service encapsulation, no comments, async correctness, epoch timestamps, and UV virtualenv activation for tests. [Source: AGENTS.md]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]
- [Source: _bmad-output/planning-artifacts/architecture.md#Component Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap 2 - PDF storage]
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap 3 - Python background tasks]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: ces-ddr-platform/ces-backend/src/main.py]
- [Source: ces-ddr-platform/ces-backend/src/api/endpoints.py]
- [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/auth.py]
- [Source: ces-ddr-platform/ces-backend/src/api/dependencies/auth.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/base.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/user.py]
- [Source: ces-ddr-platform/ces-backend/src/config/settings/base.py]
- [Source: ces-ddr-platform/ces-backend/pyproject.toml]
- [Source: https://fastapi.tiangolo.com/tutorial/request-files/]
- [Source: https://fastapi.tiangolo.com/tutorial/background-tasks/]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- `source .venv/bin/activate && ruff check .`
- `source .venv/bin/activate && pytest`

### Completion Notes List

- Added `/api/ddrs/upload`, `/api/ddrs`, and `/api/ddrs/{ddr_id}` routes with JWT protection.
- Added async upload service, PDF validation, `/app/uploads/{uuid}.pdf` storage, DB-backed queue insert, file cleanup on DB failure, and placeholder background task dispatch.
- Extended 2.1 DDR schemas/repositories with direct API response models, descending list query, queue position calculation, and atomic DDR plus queue creation.
- Added exact route-level error bodies for upload validation and missing DDR records.
- Full backend validation passed: ruff green, pytest 24 passed.

### File List

- ces-ddr-platform/ces-backend/pyproject.toml
- ces-ddr-platform/ces-backend/src/api/endpoints.py
- ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py
- ces-ddr-platform/ces-backend/src/config/settings/base.py
- ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
- ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
- ces-ddr-platform/ces-backend/src/services/__init__.py
- ces-ddr-platform/ces-backend/src/services/ddr.py
- ces-ddr-platform/ces-backend/tests/test_ddr_upload_contract.py
