# Story 4.0: Well Name & Surface Location Extraction

Status: review

## Story

As a CES staff member,
I want Well Name and Surface Location columns in the occurrence table to show actual values extracted from the DDR PDF,
so that I can identify which well each occurrence belongs to without having to open the source PDF.

## Acceptance Criteria

**Given** a DDR PDF is processed through the Gemini extraction pipeline
**When** at least one date chunk is successfully extracted
**Then** `ddrs.well_name` is populated with the well name found in the PDF (or remains null if not found)
**And** `ddrs.surface_location` is populated with the surface location found in the PDF (or remains null if not found)
**And** both values are written in a single `UPDATE` to the `ddrs` row after all date extractions complete

**Given** `ddrs.well_name` and `ddrs.surface_location` are populated
**When** `OccurrenceGenerationService.generate_for_ddr` runs
**Then** every occurrence row for that DDR has `well_name` set from `ddr.well_name`
**And** every occurrence row has `surface_location` set from `ddr.surface_location`
**And** `surface_location` is no longer hardcoded `None`

**Given** Gemini returns `well_name` and `surface_location` fields in extracted JSON
**When** `DDRExtractionValidator` validates the response
**Then** both fields pass validation (they are accepted by the Pydantic model, not rejected as extra)
**And** `final_json` stored in `ddr_dates` includes `well_name` and `surface_location`

**Given** a DDR where all dates fail extraction
**When** pipeline finishes
**Then** `ddrs.well_name` and `ddrs.surface_location` remain null
**And** no error is raised for missing metadata

**Given** `GET /ddrs/:id/occurrences` is called for a DDR with extracted well metadata
**When** occurrences are returned
**Then** each occurrence item includes non-null `well_name` and `surface_location` values

## Tasks / Subtasks

- [x] **Task 1: Alembic migration — add `surface_location` to `ddrs`** (AC: 1)
  - [x] Create `src/repository/migrations/versions/2026_05_12_0004-004_well_metadata.py`
  - [x] `upgrade()`: `op.add_column("ddrs", sa.Column("surface_location", sa.Text(), nullable=True))`
  - [x] `downgrade()`: `op.drop_column("ddrs", "surface_location")`
  - [x] `down_revision = "003_occurrences"`, `revision = "004_well_metadata"`

- [x] **Task 2: DDR ORM model — add `surface_location`** (AC: 1)
  - [x] Add `surface_location: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)` to `DDR` class in `src/models/db/ddr.py`

- [x] **Task 3: DDR Pydantic schemas — add `surface_location`** (AC: 1, 5)
  - [x] Add `surface_location: str | None = None` to `DDRBase` in `src/models/schemas/ddr.py`
  - [x] Add `surface_location: str | None = None` to `DDRListItemResponse`
  - [x] Add `well_name: str | None = None` and `surface_location: str | None = None` to `DDRExtractionPayload`
  - [x] `DDRExtractionPayload` inherits `extra="forbid"` from `DDRExtractionSchemaModel` — adding these fields explicitly allows Gemini to return them without validation rejection

- [x] **Task 4: Extraction schema — add `well_name` and `surface_location`** (AC: 3)
  - [x] Update `src/resources/ddr_schema.json`: add `well_name` and `surface_location` as optional top-level properties (type `["string", "null"]`, NOT in `required`)
  - [x] Update `GeminiDDRExtractor.build_prompt` in `src/services/pipeline/extract.py` to exclude `well_name`/`surface_location` from the data sections list and add an explicit instruction to extract them from the report header

- [x] **Task 5: DDR CRUD — add `update_well_metadata` method** (AC: 1)
  - [x] Add `async def update_well_metadata(self, ddr, well_name, surface_location, commit=True)` to `DDRCRUDRepository` in `src/repository/crud/ddr.py`
  - [x] Method sets `ddr.well_name`, `ddr.surface_location`, `ddr.updated_at`, then flushes/commits

- [x] **Task 6: Pipeline service — aggregate and write well metadata** (AC: 1, 4)
  - [x] In `PreSplitPipelineService._extract_all_dates`, after `asyncio.gather` completes, scan `final_json` of all successful `ddr_dates` rows for first non-null `well_name` and `surface_location`
  - [x] Call `ddr_repository.update_well_metadata(ddr, well_name, surface_location)` before `finalize_status_from_dates`
  - [x] Also apply in `retry_date` flow after `_generate_occurrences` call
  - [x] Pass `ddr_surface_location` to `_generate_occurrences`

- [x] **Task 7: `_generate_occurrences` — pass surface_location** (AC: 2)
  - [x] Update `PreSplitPipelineService._generate_occurrences` signature to accept and forward `ddr_surface_location`
  - [x] Update `OccurrenceGenerationService.generate_for_ddr` to accept `ddr_surface_location: str | None = None`
  - [x] Replace hardcoded `"surface_location": None` with `"surface_location": ddr_surface_location` in the occurrence dict in `src/services/occurrence/generate.py`

- [x] **Task 8: Tests** (AC: all)
  - [x] Unit test: `update_well_metadata` sets both fields and updates `updated_at`
  - [x] Unit test: `generate_for_ddr` with `ddr_surface_location="AB 01-02-003-04W5"` → all occurrences have that `surface_location`
  - [x] Unit test: `DDRExtractionValidator.validate` with JSON containing `well_name` and `surface_location` → `is_valid=True`, both in `final_json`
  - [x] Unit test: pipeline `_extract_all_dates` aggregates `well_name`/`surface_location` from first successful date's `final_json`
  - [x] Unit test: all dates fail → `update_well_metadata` called with `None, None` (no crash)

## Dev Notes

### Architecture Pattern

Follow the existing async SQLAlchemy repository pattern. All DB writes through repository methods. Use `BaseCRUDRepository.update()` or direct session add — match style of `update_status` in `DDRCRUDRepository`.

### File List (all backend — no frontend changes)

| File | Action |
|------|--------|
| `src/repository/migrations/versions/2026_05_12_0004-004_well_metadata.py` | NEW |
| `src/models/db/ddr.py` | UPDATE — add `surface_location` to `DDR` |
| `src/models/schemas/ddr.py` | UPDATE — add `surface_location` to `DDRBase`, `DDRListItemResponse`, `DDRExtractionPayload` |
| `src/resources/ddr_schema.json` | UPDATE — add `well_name`/`surface_location` properties |
| `src/services/pipeline/extract.py` | UPDATE — `build_prompt` excludes metadata fields from sections list |
| `src/repository/crud/ddr.py` | UPDATE — add `update_well_metadata` method |
| `src/services/pipeline_service.py` | UPDATE — aggregate metadata, call `update_well_metadata`, pass to `_generate_occurrences` |
| `src/services/occurrence/generate.py` | UPDATE — accept `ddr_surface_location`, propagate to dict |

**No frontend changes required.** `OccurrenceInResponse` already includes `well_name` and `surface_location`. Once backend populates them, they appear in the table automatically.

### Critical: `extra="forbid"` on Pydantic Model

`DDRExtractionPayload` inherits `extra="forbid"` from `DDRExtractionSchemaModel`. If you add `well_name`/`surface_location` to `ddr_schema.json` but NOT to the Pydantic model, the validator will reject them as extra fields, causing all extractions to fail validation. Add to BOTH.

### Critical: `additionalProperties: false` in JSON Schema

`ddr_schema.json` has `"additionalProperties": false` at root level. Adding `well_name` and `surface_location` to `properties` is required — they will NOT be returned by Gemini otherwise.

### ddr_schema.json Change

Add these two properties at the top-level `properties` object (alongside `time_logs`, `mud_records`, etc.). Do NOT add to `required` — treat as optional:

```json
"well_name": {"type": ["string", "null"]},
"surface_location": {"type": ["string", "null"]}
```

### `build_prompt` Update in `GeminiDDRExtractor`

The current prompt lists all `schema.section_names()` as "sections". After adding `well_name`/`surface_location` to the schema, they'd be listed as data sections (wrong). Filter them out:

```python
def build_prompt(self, date: str) -> str:
    metadata_keys = {"well_name", "surface_location"}
    data_sections = [k for k in self._schema.section_names() if k not in metadata_keys]
    sections = ", ".join(data_sections)
    time_log_fields = ", ".join(
        self._schema.raw["properties"]["time_logs"]["items"]["properties"].keys()
    )
    return (
        "You are extracting structured data from a Daily Drilling Report (DDR) PDF for date "
        f"{date}. Return JSON with sections: {sections}. "
        "Also extract well_name (string or null) and surface_location (string or null) "
        "from the report header — these are DDR-level fields, not per-section data. "
        "For 'time_logs', preserve the original row order from the report and emit fields in this "
        f"exact order per row: {time_log_fields}. Use null for missing optional values."
    )
```

### Well Metadata Aggregation in Pipeline

After all dates finish in `_extract_all_dates`, re-read `ddr_dates` rows and extract first non-null metadata:

```python
rows = await self.ddr_date_repository.read_dates_by_ddr_id(ddr_id)
well_name = next(
    (r.final_json.get("well_name") for r in rows if r.final_json and r.final_json.get("well_name")),
    None,
)
surface_location = next(
    (r.final_json.get("surface_location") for r in rows if r.final_json and r.final_json.get("surface_location")),
    None,
)
await self.ddr_repository.update_well_metadata(ddr, well_name, surface_location)
```

Call this BEFORE `finalize_status_from_dates` so both DB writes happen in logical sequence.

### `update_well_metadata` in DDRCRUDRepository

```python
async def update_well_metadata(
    self, ddr: DDR, well_name: str | None, surface_location: str | None, commit: bool = True
) -> DDR:
    return await self.update(
        ddr,
        {"well_name": well_name, "surface_location": surface_location, "updated_at": int(time.time())},
        commit=commit,
    )
```

Check `BaseCRUDRepository.update()` signature — it takes an entity and a dict. Match the commit pattern used by `update_status`.

### `generate_for_ddr` Signature Update

```python
async def generate_for_ddr(
    self,
    ddr_id: str,
    ddr_well_name: str | None = None,
    ddr_surface_location: str | None = None,
    surface_shoe: float = DEFAULT_SURFACE_SHOE_DEPTH,
    intermediate_shoe: float = DEFAULT_INTERMEDIATE_SHOE_DEPTH,
) -> int:
```

In the occurrence dict, replace `"surface_location": None` with `"surface_location": ddr_surface_location`.

Call site in `pipeline_service._generate_occurrences`:
```python
return await service.generate_for_ddr(
    ddr_id=ddr_id,
    ddr_well_name=getattr(ddr, "well_name", None),
    ddr_surface_location=getattr(ddr, "surface_location", None),
)
```

Note: `ddr` object must be refreshed AFTER `update_well_metadata` runs — or pass the values directly rather than re-reading from the `ddr` object. Safest: pass `well_name` and `surface_location` as explicit args to `_generate_occurrences` rather than reading from `ddr`.

### `retry_date` Flow

`retry_date` in `pipeline_service.py` also calls `_generate_occurrences`. Apply the same metadata aggregation there too (re-read all `final_json` rows, extract first non-null, call `update_well_metadata`, pass to generation).

### Migration Naming Convention

Existing files: `2026_05_07_0001-001_...`, `2026_05_07_0002-002_...`, `2026_05_08_0003-003_...`
New file: `2026_05_12_0004-004_well_metadata.py`
`revision = "004_well_metadata"`, `down_revision = "003_occurrences"`

### No Frontend Changes

The frontend already handles these fields:
- `OccurrenceInResponse` has `well_name: string | null` and `surface_location: string | null`
- `OccurrenceTable.tsx` already renders them with `getValue() ?? "—"` fallback
- `api.ts` already maps these fields

Once the backend populates the DB, the existing frontend will display real values automatically.

### Testing Pattern

Follow existing test pattern in `tests/`. Use `pytest` with async fixtures. Mock `ddr_repository` and `ddr_date_repository` where needed. For integration-style tests, follow patterns in `tests/test_occurrence_generation.py` and `tests/test_ddr_upload_contract.py`.

### References

- `src/services/occurrence/generate.py` — current `generate_for_ddr`, hardcoded `surface_location: None` at line 60
- `src/services/pipeline_service.py` — `_generate_occurrences` at line 255, `_extract_all_dates` flow
- `src/resources/ddr_schema.json` — current schema (no `well_name`/`surface_location`)
- `src/services/pipeline/extract.py` — `build_prompt` method
- `src/models/schemas/ddr.py` — `DDRExtractionPayload` with `extra="forbid"` via `DDRExtractionSchemaModel`
- `src/repository/crud/ddr.py` — `DDRCRUDRepository`, existing `update_status` pattern to follow
- `src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py` — migration pattern to follow
- Story 3.4 (`stories/3-4-occurrence-generation-api-pipeline-integration.md`) — prior context on why `surface_location` was `None`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `surface_location` column to `ddrs` via migration 004_well_metadata (down_revision: 003_occurrences)
- Added `surface_location` ORM field to `DDR` model
- Added `surface_location` to `DDRBase`, `DDRListItemResponse`; added `well_name` + `surface_location` to `DDRExtractionPayload` (extra="forbid" safe — explicit fields)
- Added `well_name`/`surface_location` as optional properties to `ddr_schema.json`; updated `build_prompt` to filter them out of section list and add explicit header extraction instruction
- Added `DDRCRUDRepository.update_well_metadata` using existing `BaseCRUDRepository.update` pattern
- `_extract_all_dates`: aggregates first non-null `well_name`/`surface_location` from all `ddr_date.final_json` after gather, calls `update_well_metadata`, passes both to `_generate_occurrences`
- `retry_date`: same aggregation pattern after `finalize_status_from_dates`
- `_generate_occurrences`: accepts `well_name`/`surface_location` params, passes to `generate_for_ddr`
- `generate_for_ddr`: new `ddr_surface_location` param replaces hardcoded `None`
- 9 new unit tests in `tests/test_well_metadata.py` (all passing); updated stubs in `test_ddr_extraction_pipeline.py` and `test_ddr_status_stream.py`
- Full test suite: 202 passed, 0 failed

### File List

- ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_12_0004-004_well_metadata.py (NEW)
- ces-ddr-platform/ces-backend/src/models/db/ddr.py (UPDATED)
- ces-ddr-platform/ces-backend/src/models/schemas/ddr.py (UPDATED)
- ces-ddr-platform/ces-backend/src/resources/ddr_schema.json (UPDATED)
- ces-ddr-platform/ces-backend/src/services/pipeline/extract.py (UPDATED)
- ces-ddr-platform/ces-backend/src/repository/crud/ddr.py (UPDATED)
- ces-ddr-platform/ces-backend/src/services/pipeline_service.py (UPDATED)
- ces-ddr-platform/ces-backend/src/services/occurrence/generate.py (UPDATED)
- ces-ddr-platform/ces-backend/tests/test_well_metadata.py (NEW)
- ces-ddr-platform/ces-backend/tests/test_ddr_extraction_pipeline.py (UPDATED — added update_well_metadata stub)
- ces-ddr-platform/ces-backend/tests/test_ddr_status_stream.py (UPDATED — added update_well_metadata stub)

## Change Log

- 2026-05-12: Story 4.0 implemented — surface_location extraction from DDR headers, written to ddrs table, propagated to occurrences
