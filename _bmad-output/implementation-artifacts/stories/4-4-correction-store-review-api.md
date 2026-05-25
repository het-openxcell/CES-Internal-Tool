# Story 4.4: Correction Store Review API

Status: done

## Story

As a CES staff member,
I want to view all stored corrections across all DDRs through a paginated, filterable API,
So that I can identify systemic misclassification patterns and decide which keyword rules to update.

## Context: Read FIRST — a `/corrections` listing already half-exists, but NOT in the shape this story needs

There is already a corrections-listing endpoint, but it is **not** what this story specifies and you must **not** reshape or remove it:

- `GET /monitor/corrections` (`src/api/routes/v1/monitor.py:34-43`) returns a **plain `list[CorrectionInResponse]`** (no envelope), takes a `field` query param (note: `field`, not `field_name`), `limit`/`offset`, has **no `ddr_id` filter**, and lives under the `/monitor` prefix. It feeds the monitor dashboard (Epic 7 territory). **Leave it exactly as-is.**

This story (4-4) requires a **new, dedicated** `GET /corrections` route (prefix `/corrections`, real path `/api/corrections`) returning the **paginated envelope** `{ "items": [...], "total": N, "page": 1, "page_size": 50 }`, with `field_name` **and** `ddr_id` filters and `page`/`page_size` query params. Two endpoints coexist — different prefix, different contract, no conflict. Do not merge them; do not change `/monitor/corrections`.

The "both Python backend" / dual-backend phrasing seen in sibling epics is dead — project is **Python-only** (`sprint-status.yaml#approved_changes.python_only_backend_cleanup`). Ignore any such wording.

## Reuse map (checked — do NOT recreate)

- **`CorrectionCRUDRepository.get_all(field_name=None, ddr_id=None, limit=100, offset=0)`** (`src/repository/crud/correction.py:48-63`) already filters by `field_name` **and** `ddr_id`, orders by `created_at desc`, and applies the `_MAX_LIMIT` cap. **Use it directly for the page items.** Do not write a new query.
- The **only** missing repo capability is a matching **count** for `total`. Add one small `count_all(field_name=None, ddr_id=None)` method to the same repository (mirror the `get_all` WHERE-clause logic; pattern for the count query already exists in `count_since`, `src/repository/crud/correction.py:71-74`).
- **`CorrectionInResponse`** schema (`src/models/schemas/correction.py:21-30`) exists but includes `user_id`, which this story's AC item shape does **not** list. Add a dedicated `CorrectionReviewItem` (the exact 8 AC fields) + a `CorrectionPageResponse` envelope rather than overloading `CorrectionInResponse` (keep the monitor endpoint's schema untouched).
- Route registration pattern: `src/api/endpoints.py` (`include_router`). DI pattern: `src/api/dependencies/services.py` + `get_repository(...)`. JWT guard: `Depends(jwt_authentication)` (`src/securities/authorizations/jwt_authentication.py`).
- API is mounted under `/api`, so `GET /corrections` resolves to `/api/corrections`.

## Acceptance Criteria

1. **Given** `GET /corrections` is called with a valid JWT
   **When** corrections exist
   **Then** HTTP 200 returns `{ "items": [...], "total": N, "page": <page>, "page_size": <page_size> }`
   **And** each item includes exactly: `id`, `occurrence_id`, `ddr_id`, `field_name`, `original_value`, `corrected_value`, `reason`, `created_at`
   **And** items are sorted by `created_at` descending
   **And** `total` is the count of **all** corrections matching the active filters (NOT the count of the returned page)

2. **Given** `GET /corrections?field_name=type`
   **When** the filter is applied
   **Then** only corrections where `field_name = "type"` are returned, and `total` reflects that filtered count

3. **Given** `GET /corrections?ddr_id=<uuid>`
   **When** the filter is applied
   **Then** only corrections for that specific DDR are returned, and `total` reflects that filtered count
   **And** `field_name` and `ddr_id` filters compose (both applied together when both present)

4. **Given** no corrections exist (or none match the filters)
   **When** `GET /corrections` is called
   **Then** HTTP 200 returns `{ "items": [], "total": 0, "page": 1, "page_size": 50 }`

5. **Given** pagination params `?page=2&page_size=50`
   **When** the request is processed
   **Then** the items returned are the slice at `offset = (page - 1) * page_size`, limited to `page_size`
   **And** the response echoes back the requested `page` and `page_size`
   **And** defaults are `page=1`, `page_size=50` when omitted

6. **Given** `GET /corrections` is called without a valid JWT
   **When** the request is processed
   **Then** HTTP 401 is returned (route is auth-guarded like every other v1 route)

## Tasks / Subtasks

- [x] **Task 1: Repository count method** (AC: 1, 2, 3, 4)
  - [x] In `src/repository/crud/correction.py`, add `async def count_all(self, field_name: str | None = None, ddr_id: str | None = None) -> int`
  - [x] Build `select(func.count(self.model.id))`; apply the **same** `field_name` / `ddr_id` `.where(...)` conditionals as `get_all` so the count always matches the filtered list
  - [x] Return `int(result.scalar_one() or 0)` (mirror `count_since`)
  - [x] No new ordering/limit/offset on the count query

- [x] **Task 2: Response schemas** (AC: 1, 4, 5)
  - [x] In `src/models/schemas/correction.py`, add `CorrectionReviewItem(BaseSchemaModel)` with exactly: `id: str`, `occurrence_id: str`, `ddr_id: str`, `field_name: str`, `original_value: str`, `corrected_value: str`, `reason: str`, `created_at: int` (epoch seconds — matches the model; CLAUDE.md datetime rule)
  - [x] Add `CorrectionPageResponse(BaseSchemaModel)` with `items: list[CorrectionReviewItem]`, `total: int`, `page: int`, `page_size: int`
  - [x] Do **not** modify `CorrectionInResponse` or `CorrectionInCreate`

- [x] **Task 3: Review service** (AC: 1–5)
  - [x] Create `src/services/correction/review.py` with class `CorrectionReviewService`
  - [x] `__init__(self, correction_repository: CorrectionCRUDRepository)` — store repo (no loose functions; CLAUDE.md)
  - [x] `async def list_corrections(self, field_name: str | None, ddr_id: str | None, page: int, page_size: int) -> CorrectionPageResponse`:
    - [x] `offset = (page - 1) * page_size`
    - [x] `rows = await self.correction_repository.get_all(field_name=field_name, ddr_id=ddr_id, limit=page_size, offset=offset)`
    - [x] `total = await self.correction_repository.count_all(field_name=field_name, ddr_id=ddr_id)`
    - [x] map each row → `CorrectionReviewItem.model_validate(row)`; return `CorrectionPageResponse(items=..., total=total, page=page, page_size=page_size)`
  - [x] Keep it small and self-documenting; no file comments

- [x] **Task 4: Route** (AC: 1–6)
  - [x] Create `src/api/routes/v1/corrections.py` with `router = APIRouter(prefix="/corrections", tags=["Corrections"])`
  - [x] `@router.get("", response_model=CorrectionPageResponse, status_code=status.HTTP_200_OK)`
  - [x] Query params (use FastAPI `Query`): `field_name: str | None = Query(default=None)`, `ddr_id: str | None = Query(default=None)`, `page: int = Query(default=1, ge=1)`, `page_size: int = Query(default=50, ge=1, le=200)`
  - [x] Dependencies: `current_user=Depends(jwt_authentication)`, `service: CorrectionReviewService = Depends(get_correction_review_service)`
  - [x] Body: `return await service.list_corrections(field_name=field_name, ddr_id=ddr_id, page=page, page_size=page_size)`
  - [x] Mirror `src/api/routes/v1/occurrences.py` import/structure style

- [x] **Task 5: DI + registration** (AC: 1–6)
  - [x] In `src/api/dependencies/services.py` add `get_correction_review_service(correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository))) -> CorrectionReviewService` returning `CorrectionReviewService(correction_repository)` (import `CorrectionReviewService`; `CorrectionCRUDRepository` import already present)
  - [x] In `src/api/endpoints.py`: `from src.api.routes.v1.corrections import router as corrections_router` and `router.include_router(router=corrections_router)`

- [x] **Task 6: Tests** (AC: 1–6) — style: `asyncio.run` + `SimpleNamespace`/stub repos for service tests, `TestClient` + `dependency_overrides` for route tests (match `tests/test_occurrence_correction_api.py`)
  - [x] New `tests/test_correction_review_api.py`
  - [x] **Repo count test** (extend `tests/test_corrections_schema.py` or new): `count_all` with no filter, with `field_name`, with `ddr_id`, with both — counts match the corresponding `get_all` length on a seeded set
  - [x] **Service tests** with a stub correction repo:
    - [x] happy path: `get_all` returns 3 rows, `count_all` returns 7 → response `items` length 3, `total` 7, echoes `page`/`page_size`; items mapped to the 8 AC fields (assert no `user_id` key leaks)
    - [x] filter pass-through: assert `field_name` and `ddr_id` are forwarded to **both** `get_all` and `count_all`
    - [x] pagination: `page=2, page_size=50` → assert `get_all` called with `offset=50, limit=50`
    - [x] empty: `get_all` → `[]`, `count_all` → `0` → `items=[]`, `total=0` (AC 4)
  - [x] **Route tests** (`TestClient`, override `jwt_authentication` like the sibling test):
    - [x] `GET /api/corrections` with auth override + service override → 200, envelope keys present (`items`, `total`, `page`, `page_size`)
    - [x] `GET /api/corrections` with **no** auth → 401 (AC 6)
    - [x] OpenAPI includes `/api/corrections` path
  - [x] Run from `ces-ddr-platform/ces-backend/`: `source .venv/bin/activate && ruff check . && pytest` — all green, no new failures

### Review Findings

- [x] [Review][Patch] Validate `ddr_id` before repository UUID comparison [ces-ddr-platform/ces-backend/src/api/routes/v1/corrections.py:12]
- [x] [Review][Patch] Make correction pagination order stable for equal `created_at` values [ces-ddr-platform/ces-backend/src/repository/crud/correction.py:51]
- [x] [Review][Patch] Replace source/mock-only `count_all` checks with seeded filter-count coverage [ces-ddr-platform/ces-backend/tests/test_corrections_schema.py:340]
- [x] [Review][Patch] Clear backend dependency overrides with `try/finally` in route test [ces-ddr-platform/ces-backend/tests/test_correction_review_api.py:207]

## Dev Notes

### Why a new route instead of extending `/monitor/corrections`

The monitor endpoint and this review endpoint serve different consumers and have incompatible contracts (plain list + `field` param vs. paginated envelope + `field_name`/`ddr_id`/`page`/`page_size`). Story 4-5 (inline-edit UI) and the correction-review dashboard (FR16) consume **this** `/corrections` envelope. Reshaping `/monitor/corrections` would break the monitor consumer for no benefit. Two thin endpoints over the same repository is the correct, low-coupling shape here.

### `total` semantics (do not get this wrong)

`total` is the count of **all** rows matching the active filters across **all** pages — not `len(items)`. That is the whole point of a separate `count_all`. A reviewer will check that `total` can exceed `page_size`. Compute it with the **same** filters as the page query, or the count and the list will silently disagree.

### Field shape — match the AC exactly

AC 1 lists 8 item fields and `user_id` is **not** among them. Use the dedicated `CorrectionReviewItem` (8 fields). Do **not** return `CorrectionInResponse` here — it exposes `user_id`, which this contract intentionally omits. `created_at` is epoch seconds (`BigInteger` on the model), so `int` in the schema (CLAUDE.md: all datetimes epoch).

### Reuse discipline (CLAUDE.md)

- `get_all` already does field_name + ddr_id filtering + desc ordering + `_MAX_LIMIT` cap — **reuse it**. The only addition to the repo is `count_all`.
- Everything encapsulated in a service (`CorrectionReviewService`) — no loose functions, no logic in the route body beyond delegation.
- No file comments. Self-documenting names. `page_size` capped (`le=200`) to keep the `get_all` `_MAX_LIMIT` ceiling meaningful and avoid unbounded page sizes.

### Model fields available (story 4-1)

`Correction` row: `id`, `occurrence_id`, `ddr_id`, `field_name`, `original_value`, `corrected_value`, `reason`, `user_id`, `created_at`. `original_value`/`corrected_value`/`reason` are TEXT NOT NULL — no `None`-guarding needed when mapping items. Append-only table (no `updated_at`).

### Pagination math

`offset = (page - 1) * page_size`. With `page` floored at `1` (FastAPI `ge=1`), the smallest offset is `0`. No clamping of `page` against `total` is required — a page past the end simply yields `items: []` with the real `total` (acceptable; AC does not require last-page clamping).

### Test style (match the repo, no pytest-asyncio)

`tests/test_occurrence_correction_api.py` is the template: `asyncio.run` for async service calls, `SimpleNamespace`/stub classes for repos, `TestClient(backend_app)` + `backend_app.dependency_overrides[jwt_authentication] = _override_auth` for route auth, and `backend_app.dependency_overrides[get_correction_review_service] = ...` to stub the service in route tests. `_override_auth` returns `{"user_id": "user-1"}`. Clear overrides in the fixture teardown.

### Project Structure Notes

- New route file `src/api/routes/v1/corrections.py` sits beside `occurrences.py`, `monitor.py`, etc.
- New service `src/services/correction/review.py` joins the existing `src/services/correction/` package (alongside `context_builder.py` from story 4-3) — `__init__.py` already exists.
- No migration, no schema/DB change (table exists from story 4-1). No frontend in this story (dashboard/inline UI is story 4-5).

### References

- `_bmad-output/planning-artifacts/epics.md#Story 4.4` (lines 859-883) — AC source (envelope shape, filters, empty case)
- `_bmad-output/planning-artifacts/epics.md:186` — FR16 (correction store review dashboard) → this API backs it
- `_bmad-output/planning-artifacts/architecture.md` — corrections store + review surface (search "correction")
- `src/repository/crud/correction.py:48-63` — `get_all(field_name, ddr_id, limit, offset)` to reuse; `:71-74` `count_since` as the count-query pattern for `count_all`
- `src/api/routes/v1/monitor.py:34-43` — the **existing, do-not-touch** `/monitor/corrections` (different contract)
- `src/api/routes/v1/occurrences.py` — route/import style to mirror
- `src/api/dependencies/services.py` — DI factory pattern (`get_repository`, `Depends`)
- `src/api/endpoints.py` — `include_router` registration
- `src/models/schemas/correction.py` — add `CorrectionReviewItem` + `CorrectionPageResponse`; leave existing schemas
- `src/models/schemas/base.py` — `BaseSchemaModel` base for new schemas
- `tests/test_occurrence_correction_api.py` — service-stub + route-auth test template
- `tests/test_corrections_schema.py` — repo test style

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-21: Added failing repository count tests; confirmed `count_all` missing failure.
- 2026-05-21: `pytest tests/test_corrections_schema.py -q` passed after `count_all` implementation.
- 2026-05-21: Full backend `pytest -q` passed: 276 passed.
- 2026-05-21: Added failing schema tests for review item/envelope; confirmed missing schema import failure.
- 2026-05-21: `pytest tests/test_corrections_schema.py -q` passed after schemas: 25 passed.
- 2026-05-21: Full backend `pytest -q` passed: 278 passed.
- 2026-05-21: Added failing service tests; confirmed missing `src.services.correction.review` module.
- 2026-05-21: `pytest tests/test_correction_review_api.py -q` passed after service: 4 passed.
- 2026-05-21: Full backend `pytest -q` passed: 282 passed.
- 2026-05-21: Added failing route tests for `/api/corrections`; confirmed missing route/DI path.
- 2026-05-21: `pytest tests/test_correction_review_api.py -q` passed after route: 6 passed.
- 2026-05-21: Full backend `pytest -q` passed: 284 passed.
- 2026-05-21: Added failing backend app registration tests; confirmed `/api/corrections` missing from OpenAPI and returned 404.
- 2026-05-21: `pytest tests/test_correction_review_api.py -q` passed after registration: 8 passed.
- 2026-05-21: Full backend `pytest -q` passed: 286 passed.
- 2026-05-21: Initial `ruff check . && pytest` failed on import formatting in `tests/test_corrections_schema.py`; fixed import wrapping.
- 2026-05-21: Final `ruff check . && pytest` passed: ruff clean, 286 passed.
- 2026-05-21: Completion gate `ruff check . && pytest -q` passed: ruff clean, 286 passed.

### Completion Notes List

- Implemented filtered `CorrectionCRUDRepository.count_all` with no pagination, ordering, or limit.
- Added dedicated correction review item and paginated response schemas without changing existing correction schemas.
- Added `CorrectionReviewService` to compute page offsets, reuse repository list/count methods, and return exact paginated envelope.
- Added auth-guarded `/corrections` route with `field_name`, `ddr_id`, `page`, and `page_size` query parameters.
- Registered correction review service dependency and included the corrections router in the v1 API.
- Added service, route, registration, schema, and repository tests for the correction review API; final ruff and pytest passed.

### File List

| File | Action |
|------|--------|
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | UPDATE — mark story 4-4 review |
| `_bmad-output/implementation-artifacts/stories/4-4-correction-store-review-api.md` | UPDATE — task status, status, and dev record |
| `ces-ddr-platform/ces-backend/src/repository/crud/correction.py` | UPDATE — add `count_all(field_name, ddr_id)` |
| `ces-ddr-platform/ces-backend/src/models/schemas/correction.py` | UPDATE — add `CorrectionReviewItem` + `CorrectionPageResponse` |
| `ces-ddr-platform/ces-backend/src/services/correction/review.py` | NEW — `CorrectionReviewService.list_corrections` |
| `ces-ddr-platform/ces-backend/src/api/routes/v1/corrections.py` | NEW — `GET /corrections` paginated, filtered, auth-guarded |
| `ces-ddr-platform/ces-backend/src/api/dependencies/services.py` | UPDATE — add `get_correction_review_service` |
| `ces-ddr-platform/ces-backend/src/api/endpoints.py` | UPDATE — register `corrections_router` |
| `ces-ddr-platform/ces-backend/tests/test_corrections_schema.py` | UPDATE — add review schema and `count_all` tests |
| `ces-ddr-platform/ces-backend/tests/test_correction_review_api.py` | NEW — service, route, auth, OpenAPI, and registration tests |

## Change Log

- 2026-05-21: Story created — dedicated paginated `GET /corrections` review API (reuses `get_all`, adds `count_all`); explicitly separated from the existing `/monitor/corrections` endpoint.
- 2026-05-21: Implemented correction review API with repository count, review schemas, service, route, DI registration, and tests.
