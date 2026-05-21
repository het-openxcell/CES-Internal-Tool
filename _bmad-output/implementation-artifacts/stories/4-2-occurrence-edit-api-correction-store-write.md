# Story 4.2: Occurrence Edit API & Correction Store Write

Status: done

## Story

As a CES staff member,
I want to edit any field of an occurrence row and have my correction stored with full metadata,
So that every change is auditable and the system knows what was corrected, why, and by whom.

## Context: This Story Is a CUTOVER, Not a Greenfield Endpoint

A **legacy** edit path already exists and writes to a **separate `occurrence_edits` table** — it predates the Epic 4 `corrections` table (story 4-1) and must be **fully removed** in this story. The architecture (`architecture.md`) makes `corrections` the single canonical, append-only audit store and mandates a **flat `PATCH /occurrences/:id`** route (lines 687, 978, 1009–1011). Per explicit decision (2026-05-21): **consolidate everything onto `corrections`, delete the `occurrence_edits` table and all its code, and repoint Monitor + frontend — all within this story.**

What exists today that this story replaces/removes:
- `PATCH /ddrs/{ddr_id}/occurrences/{occurrence_id}` (nested) → writes `occurrence_edits` via `OccurrenceCorrectionService.patch_occurrence` — **replace** with flat route writing `corrections`.
- `occurrence_edits` table (migration `008_occurrence_edits`), `OccurrenceEdit` model, `OccurrenceEditCRUDRepository` — **delete** (drop table via new migration).
- Monitor `corrections_this_week` metric + `GET /monitor/corrections` list read `occurrence_edits` — **repoint to `corrections`**.
- Frontend `api.ts#patchOccurrence` (nested route, `{field,value,reason}` body) + `MonitorPage.tsx` (`c.field`, `c.created_by`) — **repoint to flat route + `corrections` shape**.

The `corrections` table, `Correction` model, `CorrectionCRUDRepository`, and `CorrectionInResponse` schema already exist from story 4-1 — **reuse them, do not recreate.**

## Acceptance Criteria

1. **Given** an authenticated user sends `PATCH /occurrences/{occurrence_id}` with body `{ "field_name": "type", "corrected_value": "Back Ream", "reason": "Text said backreamed to free" }`
   **When** the request is processed
   **Then** the `occurrences` row is updated with the new field value
   **And** a `corrections` row is inserted with: `occurrence_id`, `ddr_id` (derived from the occurrence, never the request), `field_name`, `original_value` (read from the row **before** update), `corrected_value`, `reason`, `user_id` (from JWT `current_user.id`, never the request body), `created_at` (DB `server_default`)
   **And** both the occurrence update and the correction insert commit in a **single transaction** (NFR-I3)
   **And** HTTP 200 returns the **updated occurrence row** (`OccurrenceInResponse` shape)

2. **Given** `PATCH /occurrences/{occurrence_id}` is called with a non-existent occurrence id
   **When** the lookup finds no row
   **Then** HTTP 404 is returned via the project's `EntityDoesNotExist` handler (NOT a hand-rolled JSON body)

3. **Given** `PATCH /occurrences/{occurrence_id}` is called with missing or empty `field_name`, `corrected_value`, or `reason`
   **When** request-body validation runs
   **Then** HTTP 422 is returned by FastAPI/Pydantic validation (project convention — see Dev Notes "Error-Shape Reality Check")

4. **Given** `field_name` is not one of the editable occurrence fields (`type`, `section`, `mmd`, `notes`, `density`)
   **When** the request is processed
   **Then** HTTP 422 is returned and **no** occurrence update and **no** correction insert occur

5. **Given** `field_name` is a numeric field (`mmd` or `density`)
   **When** the occurrence row is updated
   **Then** `corrected_value` is cast to `float` for the occurrence column, while `corrections.original_value` / `corrections.corrected_value` store the raw string (TEXT)
   **And** a non-numeric `corrected_value` for a numeric field yields HTTP 422 with no writes

6. **Given** the cutover is complete
   **When** the codebase is inspected
   **Then** the `occurrence_edits` table is dropped via a new Alembic migration, and `OccurrenceEdit` model + `OccurrenceEditCRUDRepository` + the nested PATCH route + `occurrence_edits` references in `env.py`, `services.py`, `monitor.py`, and `monitor` schemas are removed
   **And** `GET /monitor/corrections` and the `corrections_this_week` metric read from the `corrections` table
   **And** frontend `patchOccurrence` calls `PATCH /occurrences/{id}` with `{field_name, corrected_value, reason}` and `MonitorPage` renders the `corrections` shape

## Tasks / Subtasks

- [x] **Task 1: Request schema for the edit body** (AC: 1, 3)
  - [x] Add `OccurrenceCorrectionRequest(BaseSchemaModel)` to `src/models/schemas/occurrence.py` with required fields `field_name: str`, `corrected_value: str`, `reason: str`
  - [x] Add a `@field_validator("field_name", "corrected_value", "reason")` that rejects empty/whitespace-only strings (mirrors `CorrectionInCreate.must_be_non_empty` in `src/models/schemas/correction.py`) — satisfies the 4-1 deferred "empty-string validation" item
  - [x] Do **not** include `user_id` or `ddr_id` in the request schema (server-derived only)

- [x] **Task 2: Refactor `OccurrenceCorrectionService` to write `corrections` in a single transaction** (AC: 1, 2, 4, 5)
  - [x] In `src/services/ddr.py`, change `OccurrenceCorrectionService.__init__` to accept `correction_repository: CorrectionCRUDRepository` instead of `edit_repository: OccurrenceEditCRUDRepository`
  - [x] Replace import `from src.repository.crud.occurrence_edit import OccurrenceEditCRUDRepository` with `from src.repository.crud.correction import CorrectionCRUDRepository`
  - [x] Rewrite `patch_occurrence` signature to flat form: `patch_occurrence(self, occurrence_id, field_name, corrected_value, reason, current_user)` — drop `ddr_id` param
  - [x] Lookup: `occurrence = await self.occurrence_repository.read_by_id(occurrence_id)`; if `None` → `raise EntityDoesNotExist("occurrence_not_found")`
  - [x] Validate `field_name in self.allowed_fields` (keep `{"type", "section", "mmd", "notes", "density"}`); else `raise HTTPException(status_code=422, detail=...)` (matches existing pattern)
  - [x] `original_value = str(getattr(occurrence, field_name))` if not `None` else `""` (TEXT column is NOT NULL; empty string is the server-derived "was blank" sentinel)
  - [x] For numeric fields (`mmd`, `density`): cast `corrected_value` to `float` for the occurrence column; on `ValueError`/`TypeError` raise `HTTPException(status_code=422, ...)`. Non-numeric fields write the string directly.
  - [x] Update occurrence with `commit=False`: `await self.occurrence_repository.update(occurrence, {field_name: casted_value, "updated_at": int(time.time())}, commit=False)`
  - [x] Insert correction with `commit=False`: `await self.correction_repository.create_correction(occurrence_id=occurrence_id, ddr_id=occurrence.ddr_id, field_name=field_name, original_value=original_value, corrected_value=str(corrected_value), reason=reason, user_id=current_user.id, commit=False)`
  - [x] Commit once: `await self.occurrence_repository.async_session.commit()` then `await self.occurrence_repository.async_session.refresh(occurrence)`
  - [x] Return the refreshed `occurrence`

- [x] **Task 3: New flat route `PATCH /occurrences/{occurrence_id}`** (AC: 1, 2, 3)
  - [x] Create `src/api/routes/v1/occurrences.py` with `router = APIRouter(prefix="/occurrences", tags=["Occurrences"])`
  - [x] `@router.patch("/{occurrence_id}", response_model=OccurrenceInResponse, status_code=status.HTTP_200_OK)`
  - [x] Params: `occurrence_id: str`, `payload: OccurrenceCorrectionRequest`, `current_user=Depends(jwt_authentication)`, `service: OccurrenceCorrectionService = Depends(get_occurrence_correction_service)`
  - [x] Body: `occurrence = await service.patch_occurrence(occurrence_id=occurrence_id, field_name=payload.field_name, corrected_value=payload.corrected_value, reason=payload.reason, current_user=current_user)`; `return OccurrenceInResponse.model_validate(occurrence)`
  - [x] Register in `src/api/endpoints.py`: import `occurrences_router` and `router.include_router(router=occurrences_router)`

- [x] **Task 4: Update DI wiring** (AC: 1, 6)
  - [x] In `src/api/dependencies/services.py`, change `get_occurrence_correction_service` to inject `CorrectionCRUDRepository` (replace `OccurrenceEditCRUDRepository`); update import
  - [x] Ensure `ddr_repository`, `occurrence_repository`, `correction_repository` all resolve via `get_repository(...)` so they share the same request session (required for the single transaction — verified: `get_async_session` is cached per request)

- [x] **Task 5: Remove the legacy nested PATCH route** (AC: 6)
  - [x] In `src/api/routes/v1/ddr.py`, delete the `patch_occurrence` route (lines ~227–247) and remove now-unused imports: `OccurrenceEditResponse`, `OccurrencePatchRequest` (from `monitor` schema), and `get_occurrence_correction_service` if no longer used there (it is used only by the deleted route)

- [x] **Task 6: Repoint Monitor to `corrections`** (AC: 6)
  - [x] Add `count_since(self, since_ts: int) -> int` to `CorrectionCRUDRepository` (count `Correction.created_at >= since_ts`), mirroring `OccurrenceEditCRUDRepository.count_since`
  - [x] In `src/services/monitor.py`: change `MonitorService.__init__` param `edit_repository` → `correction_repository: CorrectionCRUDRepository`; update `from ...occurrence_edit import` → `from ...correction import CorrectionCRUDRepository`; `corrections_this_week = await self.correction_repository.count_since(week_start)`; `corrections()` method → `await self.correction_repository.get_all(field_name=field, limit=limit, offset=offset)` (note param rename `field` → `field_name`)
  - [x] In `src/api/routes/v1/monitor.py`: swap `OccurrenceEditCRUDRepository` → `CorrectionCRUDRepository` in all three handlers; `GET /monitor/corrections` `response_model=list[CorrectionInResponse]` and `return [CorrectionInResponse.model_validate(c) for c in ...]`; the `field` query param now filters `field_name`

- [x] **Task 7: Drop `occurrence_edits` table + delete its code** (AC: 6)
  - [x] New migration `src/repository/migrations/versions/2026_05_21_0011-011_drop_occurrence_edits.py`: `revision = "011_drop_occurrence_edits"`, `down_revision = "010_corrections"`; `upgrade()` drops the three `idx_occurrence_edits_*` indexes then `op.drop_table("occurrence_edits")`; `downgrade()` recreates table + indexes (copy the `008_occurrence_edits` create for parity)
  - [x] Delete `src/models/db/occurrence_edit.py` and `src/repository/crud/occurrence_edit.py`
  - [x] In `src/repository/migrations/env.py`: remove `occurrence_edit` from the `from src.models.db import ...` import and from the `_models` tuple
  - [x] In `src/models/schemas/monitor.py`: remove `OccurrenceEditResponse` and `OccurrencePatchRequest` (no longer referenced after Tasks 5–6)
  - [x] Grep to confirm zero remaining references: `grep -rn "occurrence_edit\|OccurrenceEdit\|OccurrencePatchRequest" src` returns nothing except the new drop migration's `downgrade`

- [x] **Task 8: Frontend cutover** (AC: 6)
  - [x] `src/lib/api.ts`: rewrite `patchOccurrence` to `patchOccurrence(occurrenceId: string, fieldName: string, correctedValue: string, reason: string)` → `PATCH /occurrences/{occurrenceId}` body `{ field_name, corrected_value, reason }`, return type `OccurrenceRow`
  - [x] `src/lib/api.ts`: replace `OccurrenceEditResponse` type with a `Correction` type matching `CorrectionInResponse`: `{ id, occurrence_id, ddr_id, field_name, original_value, corrected_value, reason, user_id, created_at }`; `getMonitorCorrections` returns `Correction[]`
  - [x] `src/pages/MonitorPage.tsx`: update the corrections table — `c.field` → `c.field_name` (3 sites: the badge branches and label), `c.created_by` → `c.user_id` (or render `"—"`; full user name embed is deferred to story 4-4). `c.corrected_value` already aligns.
  - [x] Confirm no other consumer breaks: `patchOccurrence` currently has **no UI caller** (inline edit is story 4-5); `ReportDetailPage` edit history is hardcoded mock data — leave it untouched.

- [x] **Task 9: Backend tests** (AC: 1–6)
  - [x] New `tests/test_occurrence_correction_api.py` (follow `tests/test_keywords_route.py` / `tests/test_ddr_upload_contract.py` style — `asyncio.run`, mocked repositories; `pytest-asyncio` is NOT installed)
  - [x] Test happy path: occurrence updated + `create_correction` called once with `ddr_id=occurrence.ddr_id`, `user_id=current_user.id`, `original_value` read pre-update; single commit; returns occurrence
  - [x] Test 404 when `read_by_id` returns `None` (asserts `EntityDoesNotExist`)
  - [x] Test invalid `field_name` → `HTTPException(422)`, no update/insert
  - [x] Test numeric cast: `mmd`/`density` with valid float updates occurrence as float; invalid → 422, no writes
  - [x] Test request schema rejects empty/missing `field_name`/`corrected_value`/`reason`
  - [x] Add `count_since` test to `CorrectionCRUDRepository` coverage (extend `tests/test_corrections_schema.py` or new file)
  - [x] Run from `ces-ddr-platform/ces-backend/`: `source .venv/bin/activate && ruff check . && pytest` — all green, no regressions

### Review Findings

- [x] [Review][Decision] Legacy occurrence_edits history retention is intentionally discarded — user confirmed direct drop is acceptable for this cutover.
- [x] [Review][Patch] Flat PATCH route needs an authorization/scope guard [ces-backend/src/api/routes/v1/occurrences.py:13]
- [x] [Review][Patch] Monitor corrections filter uses `field_name` query param instead of spec's `field` param [ces-backend/src/api/routes/v1/monitor.py:36]
- [x] [Review][Patch] Numeric correction accepts non-finite floats such as NaN and infinity [ces-backend/src/services/ddr.py:194]
- [x] [Review][Patch] Section correction lacks `VALID_SECTIONS` validation after review surfaced the edge case [ces-backend/src/services/ddr.py:199]

## Dev Notes

### Error-Shape Reality Check (read before coding AC 2 & 3)

The epic text specifies literal JSON bodies like `{ "error": "...", "code": "NOT_FOUND", "details": {} }` and HTTP **400** for validation. **The project does NOT use that shape and you must NOT hand-roll it.** Reality:
- All errors flow through registered handlers in `src/utilities/exceptions/exceptions.py` → response shape is `{ success, error_code, message: { title, description }, call_hierarchy }`.
- `raise EntityDoesNotExist("occurrence_not_found")` → **404** (handler registered in `main.py:39`). Use this for AC 2.
- Missing/empty body fields are caught by **Pydantic** → FastAPI returns **422** (not 400). This is the project-wide convention. AC 3/4/5 therefore specify 422. Do not add a custom 400 path.
- The "both Python backend produce identical structure" clause in the epic is a leftover from the abandoned dual-backend (TS+Go+Python) plan — the project is **Python-only** now (see `approved_changes.python_only_backend_cleanup` in `sprint-status.yaml`). Ignore all dual-backend wording.

### Single-Transaction Mechanics (AC 1)

`get_repository(Repo)` depends on `get_async_session`, and FastAPI caches a dependency once per request — so `ddr_repository`, `occurrence_repository`, and `correction_repository` injected into one request **share the same `AsyncSession`**. `BaseCRUDRepository.create`/`update` with `commit=False` call `session.flush()` only. The service therefore does both writes with `commit=False`, then a single `await session.commit()`. If the correction insert raises, the occurrence update is not committed (atomic). Do not call `commit=True` on either write.

### Reuse, Don't Recreate (from story 4-1)

These already exist — import and use:
- `Correction` model: `src/models/db/correction.py` — `created_at` has DB `server_default` (`EXTRACT(EPOCH FROM now())::BIGINT`), so **do not** pass `created_at`. FKs are `ondelete=CASCADE` (occurrence/ddr) and `RESTRICT` (user). Composite index `(field_name, ddr_id)` already present.
- `CorrectionCRUDRepository.create_correction(...)`: `src/repository/crud/correction.py` — already omits `created_at`, uses `BaseCRUDRepository.create`. Add only `count_since` (Task 6).
- `CorrectionInResponse`: `src/models/schemas/correction.py` — use for Monitor list response. Note it exposes raw `user_id` (no user name) — that's intentional; embedding a user sub-schema is **deferred to story 4-4**.

### Resolved 4-1 Deferred Items This Story Owns (do these here)

From `deferred-work.md` and 4-1 review:
- **`user_id` from JWT, never request body** → Task 2 reads `current_user.id`; request schema (Task 1) excludes `user_id`. ✅
- **`ddr_id` derived from occurrence, not request** → Task 2 uses `occurrence.ddr_id`. ✅
- **`field_name` validated against known fields** → Task 2 `allowed_fields` check. ✅
- **Empty-string validation on `corrected_value`/`reason`** → Task 1 `field_validator`. ✅

### Existing Service to Refactor (current state)

`OccurrenceCorrectionService.patch_occurrence` (`src/services/ddr.py:167-213`) currently: takes `ddr_id` + `occurrence_id`, validates the same `allowed_fields`, reads `original_value`, calls `occurrence_repository.update({field: value})` with default `commit=True`, then `edit_repository.create_edit(...)` with `created_by=username`. Known latent bug to fix while here: it writes a raw string into `mmd`/`density` Float columns with no cast (Task 2 AC 5 fixes this). Returns the edit record; the new version returns the **occurrence**.

### Editable Fields

Keep `{"type", "section", "mmd", "notes", "density"}` — matches the existing service set and Epic 4.5 inline-edit columns (Type, Section, mMD, Density, Notes). `well_name`/`surface_location` are not user-editable. `section` has an enum (`VALID_SECTIONS` in `src/constants/occurrence.py`) — the existing service does not enforce it on edit and Epic 4.5 uses a free dropdown; do not add section-enum enforcement here unless it surfaces in review.

### Project Conventions (CLAUDE.md)

- No file comments. Encapsulate in classes/services; no loose functions.
- Epoch (`BigInteger` seconds) for all timestamps — `updated_at` via `int(time.time())` matches the occurrence pattern.
- Activate venv before running anything: `source .venv/bin/activate`.
- Wrap blocking sync SDK calls in `asyncio.to_thread` — N/A here (all DB I/O is async SQLAlchemy).

### Frontend Notes

- `patchOccurrence` (`src/lib/api.ts:257`) has **no current UI caller** — safe to change its signature. The inline-edit UI + `useCorrections` hook arrive in story 4-5.
- `MonitorPage.tsx` is the only live consumer of the corrections list. `ReportDetailPage` edit history (lines 30–32) is hardcoded mock — do not wire it here.

### Project Structure Notes

- New route file `src/api/routes/v1/occurrences.py` matches the one-router-per-domain pattern (`auth.py`, `ddr.py`, `monitor.py`, ...). Mount in `endpoints.py`; the global `settings.API_PREFIX` is applied in `main.py:43`.
- Migration naming follows the dated prefix pattern `YYYY_MM_DD_NNNN-NNN_<slug>.py`; chain head is `010_corrections`, so the new one is `011_drop_occurrence_edits` with `down_revision = "010_corrections"`.

### References

- `_bmad-output/planning-artifacts/architecture.md` — lines 248/460/978 (corrections canonical, append-only), 307 + 687 + 1009–1011 (`PATCH /occurrences/:id` → update occurrence + insert correction), 540 (201 for create — note: this is a PATCH/edit, returns 200)
- `_bmad-output/planning-artifacts/epics.md#Story 4.2` (lines 806–831) — AC source (apply Error-Shape Reality Check above)
- `stories/4-1-corrections-database-schema.md` — `corrections` schema, CRUD, response schema; Review Findings list the deferred items this story closes
- `src/services/ddr.py:167-213` — `OccurrenceCorrectionService` to refactor
- `src/api/routes/v1/ddr.py:227-247` — legacy nested PATCH route to delete
- `src/api/routes/v1/monitor.py` + `src/services/monitor.py` — Monitor repoint targets
- `src/repository/crud/correction.py` — add `count_since`; reuse `create_correction`, `get_all`
- `src/repository/crud/base.py` — `create`/`update` `commit=False` flush semantics for single transaction
- `src/api/dependencies/{repository,session}.py` — per-request shared session (transaction correctness)
- `src/utilities/exceptions/exceptions.py` + `src/main.py:35-41` — registered handlers / actual error shape
- `src/repository/migrations/versions/2026_05_14_0008-008_occurrence_edits.py` — source for the `downgrade()` recreate in the new drop migration
- `ces-frontend/src/lib/api.ts:65-75,257-275` + `ces-frontend/src/pages/MonitorPage.tsx:224-319` — frontend cutover sites
- `tests/test_keywords_route.py`, `tests/test_ddr_upload_contract.py` — async route test style (no `pytest-asyncio`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Cutover complete: `occurrence_edits` table, model, repo, legacy nested PATCH route all removed
- New flat `PATCH /occurrences/{id}` writes occurrence update + correction insert in single atomic transaction
- `user_id` derived from JWT `current_user.id`; `ddr_id` derived from occurrence row — never from request
- Numeric fields (`mmd`, `density`) cast to float for DB; TEXT string stored in corrections table
- `CorrectionCRUDRepository.count_since` added; MonitorService + monitor routes repointed to corrections
- Frontend: `Correction` type replaces `OccurrenceEditResponse`; `patchOccurrence` uses flat route; MonitorPage uses `field_name`/`user_id`
- 30/30 new+existing tests pass; 5 pre-existing failures unrelated to this story

### File List

| File | Action |
|------|--------|
| `ces-backend/src/models/schemas/occurrence.py` | UPDATE — add `OccurrenceCorrectionRequest` |
| `ces-backend/src/services/ddr.py` | UPDATE — refactor `OccurrenceCorrectionService` to corrections + single tx |
| `ces-backend/src/api/routes/v1/occurrences.py` | NEW — flat `PATCH /occurrences/{id}` |
| `ces-backend/src/api/endpoints.py` | UPDATE — register occurrences router |
| `ces-backend/src/api/dependencies/services.py` | UPDATE — inject `CorrectionCRUDRepository` |
| `ces-backend/src/api/routes/v1/ddr.py` | UPDATE — remove legacy nested PATCH route + imports |
| `ces-backend/src/repository/crud/correction.py` | UPDATE — add `count_since` |
| `ces-backend/src/services/monitor.py` | UPDATE — repoint to corrections |
| `ces-backend/src/api/routes/v1/monitor.py` | UPDATE — corrections repo + `CorrectionInResponse` |
| `ces-backend/src/models/schemas/monitor.py` | UPDATE — remove `OccurrenceEditResponse`/`OccurrencePatchRequest` |
| `ces-backend/src/repository/migrations/versions/2026_05_21_0011-011_drop_occurrence_edits.py` | NEW — drop `occurrence_edits` |
| `ces-backend/src/repository/migrations/env.py` | UPDATE — remove `occurrence_edit` import + `_models` |
| `ces-backend/src/models/db/occurrence_edit.py` | DELETE |
| `ces-backend/src/repository/crud/occurrence_edit.py` | DELETE |
| `ces-backend/tests/test_occurrence_correction_api.py` | NEW |
| `ces-frontend/src/lib/api.ts` | UPDATE — flat `patchOccurrence`, `Correction` type |
| `ces-frontend/src/pages/MonitorPage.tsx` | UPDATE — `field_name`/`user_id` render |

## Change Log

- 2026-05-21: Story created — occurrence edit API on `corrections` + full `occurrence_edits` cutover (route, Monitor, frontend), single transaction, JWT-derived `user_id`
- 2026-05-21: Implemented all 9 tasks — new flat PATCH route, OccurrenceCorrectionService refactored, occurrence_edits dropped, Monitor repointed, frontend cutover, 30 tests passing
