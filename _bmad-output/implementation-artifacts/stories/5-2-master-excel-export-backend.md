# Story 5.2: Master Excel Export Backend

Status: review

## Story

As a CES staff member,
I want to export all occurrences across all processed DDRs into a single occurrences_all.xlsx file,
So that I can share a comprehensive dataset with clients or analyze patterns across jobs.

## Acceptance Criteria

**Given** `GET /export/master` is called with a valid JWT
**When** occurrences exist across multiple DDRs
**Then** response is a streaming `.xlsx` download named `occurrences_all.xlsx`
**And** single sheet contains all occurrences with same column structure as per-DDR export plus a `DDR Source` column
**And** sorted by `date` descending, then `ddr_id`

**Given** `GET /export/master` is called with optional filter params `?type=`, `?ddr_id=`, `?date_from=`, `?date_to=`
**When** filters are applied
**Then** only matching occurrences are included
**And** filename is `occurrences_filtered.xlsx`

**Given** no occurrences exist in the system
**When** `GET /export/master` is called
**Then** HTTP 200 returns an `.xlsx` with header row only and a note row: "No occurrences found"

**Given** `GET /export/master` is called for a large dataset (1000+ occurrences)
**When** export is generated
**Then** response starts streaming within 5 seconds

## Tasks / Subtasks

- [x] **Task 1: Create master Excel export service** (AC: 1, 2, 3, 4)
  - [x] Create `src/services/export/excel_master.py` with `MasterExcelExportService` class
  - [x] `generate(occurrences_with_source: list[dict]) -> io.BytesIO` — sync method
  - [x] Sheet 1 named "Occurrences": same header styling as per-DDR export (`#111827` bg, white font)
  - [x] Columns: Well Name | Surface Location | Type | Section | mMD | Density | Notes | DDR Source
  - [x] Empty case: write header row + row 2 = "No occurrences found" in first cell
  - [x] Call `asyncio.to_thread(service.generate, ...)` at route level

- [x] **Task 2: Add master export query to OccurrenceCRUDRepository** (AC: 1, 2)
  - [x] Add `get_all_with_ddr_source` method to `src/repository/crud/occurrence.py`
  - [x] Joins `occurrences` → `ddrs` to get `ddr.file_path` as DDR source label
  - [x] Filter params: `type_filter`, `ddr_id`, `date_from`, `date_to`
  - [x] Order: `Occurrence.date.desc().nullslast()`, then `Occurrence.ddr_id`
  - [x] Returns `list[dict]` with all occurrence fields + `ddr_source` key

- [x] **Task 3: Add master export endpoint to export router** (AC: 1, 2, 3, 4)
  - [x] Add `GET /export/master` to `src/api/routes/v1/export.py` (same file as story 5.1)
  - [x] Query params: `type` (str | None), `ddr_id` (str | None), `date_from` (str | None, pattern `^\d{8}$`), `date_to` (str | None, pattern `^\d{8}$`)
  - [x] Determine filename: `occurrences_filtered.xlsx` when any filter present, else `occurrences_all.xlsx`
  - [x] Fetch via `get_all_with_ddr_source` with filters, `limit=50000`
  - [x] Call `asyncio.to_thread(service.generate, rows)`
  - [x] Return StreamingResponse with correct filename and xlsx media type

- [x] **Task 4: Write tests** (AC: all)
  - [x] Add to `tests/export/test_excel_report.py` OR create `tests/export/test_excel_master.py`
  - [x] Test: `MasterExcelExportService.generate` with empty list → 1 sheet, header row + "No occurrences found" row
  - [x] Test: `MasterExcelExportService.generate` with 2 rows → 3 rows total (header + 2 data)
  - [x] Test: sheet has 8 columns including "DDR Source"
  - [x] Test: `GET /export/master` returns 200 with xlsx content-type
  - [x] Test: `GET /export/master?ddr_id=xxx` returns filename `occurrences_filtered.xlsx` in Content-Disposition
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest`

## Dev Notes

### Dependencies on Story 5.1

Story 5.1 creates:
- `src/services/export/__init__.py` and package structure
- `src/api/routes/v1/export.py` router with `prefix="/export"`
- `openpyxl` added to `pyproject.toml`

If implementing 5.2 before 5.1 is merged, create those files yourself. If 5.1 is done, extend `export.py` and add the new service file only.

### CRITICAL: New Query Method on OccurrenceCRUDRepository

The existing `get_by_ddr_id_filtered` only queries one DDR. Need a cross-DDR method that joins with `ddrs` for the source label:

```python
# src/repository/crud/occurrence.py — add to OccurrenceCRUDRepository
async def get_all_with_ddr_source(
    self,
    type_filter: str | None = None,
    ddr_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50000,
) -> list[dict]:
    stmt = (
        sqlalchemy.select(
            Occurrence,
            DDR.file_path.label("ddr_file_path"),
        )
        .join(DDR, DDR.id == Occurrence.ddr_id)
        .order_by(Occurrence.date.desc().nullslast(), Occurrence.ddr_id)
        .limit(limit)
    )
    if type_filter is not None:
        stmt = stmt.where(Occurrence.type == type_filter)
    if ddr_id is not None:
        stmt = stmt.where(Occurrence.ddr_id == ddr_id)
    if date_from is not None:
        stmt = stmt.where(Occurrence.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Occurrence.date <= date_to)
    result = await self.async_session.execute(stmt)
    rows = []
    for occ, file_path in result.tuples().all():
        rows.append({
            "well_name": occ.well_name,
            "surface_location": occ.surface_location,
            "type": occ.type,
            "section": occ.section,
            "mmd": occ.mmd,
            "density": occ.density,
            "notes": occ.notes,
            "ddr_source": file_path.split("/")[-1] if file_path else "",
        })
    return rows
```

### CRITICAL: openpyxl is Sync — asyncio.to_thread

Same as story 5.1 — `generate` is a plain sync method; route calls via `asyncio.to_thread`.

### Filename Logic

```python
has_filters = any([type_filter, ddr_id, date_from, date_to])
filename = "occurrences_filtered.xlsx" if has_filters else "occurrences_all.xlsx"
```

### Master Export Service — Share Header Style with excel_report.py

Import and reuse the header styling constants if possible, or duplicate them. Do NOT import from `excel_report.py` unless it exports those constants cleanly — avoid circular imports.

### Empty Case

```python
if not rows:
    ws.cell(row=2, column=1, value="No occurrences found")
```

### Streaming Note

openpyxl writes the whole workbook to `io.BytesIO` before streaming. For 1000+ rows this is still fast (< 5s). Full streaming of xlsx requires `openpyxl` write-only mode or `xlsxwriter` with streaming — not worth the complexity for V1. The BytesIO approach is acceptable.

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-backend/src/services/export/excel_master.py` | NEW |
| `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` | UPDATE — add `GET /export/master` endpoint |
| `ces-ddr-platform/ces-backend/src/repository/crud/occurrence.py` | UPDATE — add `get_all_with_ddr_source` |
| `ces-ddr-platform/ces-backend/tests/export/test_excel_master.py` | NEW (or extend test_excel_report.py) |

### References

- `src/services/export/excel_report.py` (from story 5.1) — header style pattern to match
- `src/repository/crud/occurrence.py:89` — `search_history` — cross-DDR join pattern to adapt
- `src/api/routes/v1/export.py` (from story 5.1) — router to extend
- `src/api/routes/v1/history.py` — filter query param pattern to follow

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Completion Notes List
- `get_all_with_ddr_source` added to `OccurrenceCRUDRepository` — joins DDR for `file_path`, returns `list[dict]`
- `GET /export/master` added to export.py; filename `occurrences_filtered.xlsx` when any filter param present
- 5 new tests all pass

### File List
- `ces-ddr-platform/ces-backend/src/services/export/excel_master.py` — NEW
- `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` — added GET /export/master
- `ces-ddr-platform/ces-backend/src/repository/crud/occurrence.py` — added get_all_with_ddr_source
- `ces-ddr-platform/ces-backend/tests/export/test_excel_master.py` — NEW

## Change Log

- 2026-05-18: Story created — master Excel export backend
- 2026-05-18: Implemented — all ACs satisfied, 5 tests pass
