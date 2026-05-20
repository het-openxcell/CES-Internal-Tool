# Story 5.3: Time Log CSV Export Backend

Status: review

## Story

As a CES staff member,
I want to export structured time log data for any processed well as a CSV file,
So that I can analyze ROP, depth, and event data in Excel without opening the source PDF.

## Acceptance Criteria

**Given** `GET /export/timelogs/{ddr_id}` is called with a valid JWT
**When** time log data exists for that DDR
**Then** response is a streaming CSV download named `<ddr_id>_timelogs.csv`
**And** CSV columns: date | time_from | time_to | activity | details | depth
**And** sorted by `date` ascending, then `time_from` ascending

**Given** `GET /export/timelogs/{ddr_id}` is called for a DDR with no processed data
**When** no matching records exist
**Then** HTTP 404 is returned with `{ "error": "Well data not found", "code": "NOT_FOUND", "details": {} }`

**Given** CSV is opened in Excel
**When** file encoding is inspected
**Then** file is UTF-8 with BOM — Excel opens without encoding dialog on Windows

## Tasks / Subtasks

- [x] **Task 1: Create time log CSV export service** (AC: 1, 2, 3)
  - [x] Create `src/services/export/csv_timelogs.py` with `TimeLogCSVExportService` class
  - [x] `generate(ddr_dates_with_timelogs: list[dict]) -> io.BytesIO` — sync method
  - [x] Write UTF-8 BOM via `io.BytesIO`; use stdlib `csv` module (no external deps needed)
  - [x] Columns: date | time_from | time_to | activity | details | depth
  - [x] Flatten: for each `ddr_date`, extract `final_json.time_logs` list, write one row per time_log entry
  - [x] Sort: sort all rows by (date asc, time_from asc) before writing

- [x] **Task 2: Add time log query to DDRDateCRUDRepository** (AC: 1, 2)
  - [x] Add `get_dates_with_timelogs(ddr_id: str) -> list[DDRDate]` to `src/repository/crud/ddr.py`
  - [x] Returns DDRDate rows where `status = "success"` and `final_json IS NOT NULL` for the given `ddr_id`
  - [x] Ordered by `DDRDate.date ASC`

- [x] **Task 3: Add timelog CSV endpoint to export router** (AC: 1, 2, 3)
  - [x] Add `GET /export/timelogs/{ddr_id}` to `src/api/routes/v1/export.py`
  - [x] Fetch DDR via `DDRCRUDRepository.read_by_id` → 404 if None
  - [x] Fetch dates via `get_dates_with_timelogs(ddr_id)`
  - [x] If no dates → 404 with `{ "error": "Well data not found", "code": "NOT_FOUND", "details": {} }`
  - [x] Build list of dicts from dates: `[{"date": d.date, "time_logs": d.final_json.get("time_logs", [])} for d in dates]`
  - [x] Call `asyncio.to_thread(service.generate, ddr_dates_data)` — csv.writer is sync
  - [x] Return `StreamingResponse(buf, media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": f'attachment; filename="{ddr_id}_timelogs.csv"'})`

- [x] **Task 4: Write tests** (AC: all)
  - [x] Create `tests/export/test_csv_timelogs.py`
  - [x] Test: `TimeLogCSVExportService.generate` with 2 dates × 3 time_logs each → 7 rows (header + 6 data)
  - [x] Test: output starts with UTF-8 BOM bytes `b'\xef\xbb\xbf'`
  - [x] Test: columns match expected header
  - [x] Test: rows sorted by date asc then time_from asc
  - [x] Test: `GET /export/timelogs/{ddr_id}` returns 404 when DDR not found
  - [x] Test: `GET /export/timelogs/{ddr_id}` returns 404 when DDR exists but no processed dates
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest`

## Dev Notes

### CRITICAL: No `wells` Table — Use ddr_id, Not well_id

The epic specifies `GET /export/timelogs/:well_id` but **there is no `wells` table and no `well_id` UUID in the database**. Wells are identified only by `well_name` (text field on `ddrs`). Implementing with a `well_id` UUID parameter would require a non-existent lookup.

**Decision: Use `ddr_id` as the path parameter.** The endpoint is `GET /export/timelogs/{ddr_id}`. Story 5.4 UI wires this with `ddr.id`. This aligns with all existing DB relationships and the frontend's use of `ddr_id` throughout.

The future Epic 6 Story 6.3 (`GET /wells/:id/timelogs`) may introduce a proper wells table — that is separate scope.

### CRITICAL: CSV Column Mapping

The epic says columns: `date | time_from | time_to | code | details | depth`

The actual `ddr_dates.final_json.time_logs` schema (from `src/resources/ddr_schema.json`):
- `start_time` → maps to `time_from`
- `end_time` → maps to `time_to`
- `activity` → maps to `activity` (epic says "code" but schema has no "code" field — use "activity")
- `comment` → maps to `details`
- `depth_md` → maps to `depth`

Use column name `activity` (not `code`) to match the actual extracted data. There is no "code" field in the extraction schema.

### CSV Service — Exact Implementation

```python
# src/services/export/csv_timelogs.py
import csv
import io


class TimeLogCSVExportService:
    def generate(self, ddr_dates_data: list[dict]) -> io.BytesIO:
        rows = []
        for entry in ddr_dates_data:
            date = entry["date"]
            for tl in entry.get("time_logs", []):
                if not isinstance(tl, dict):
                    continue
                rows.append({
                    "date": date,
                    "time_from": tl.get("start_time", ""),
                    "time_to": tl.get("end_time", ""),
                    "activity": tl.get("activity", ""),
                    "details": tl.get("comment", "") or "",
                    "depth": tl.get("depth_md", "") if tl.get("depth_md") is not None else "",
                })
        rows.sort(key=lambda r: (r["date"] or "", r["time_from"] or ""))
        
        buf = io.BytesIO()
        # UTF-8 BOM for Excel compatibility
        buf.write(b"\xef\xbb\xbf")
        text_buf = io.TextIOWrapper(buf, encoding="utf-8", newline="", write_through=True)
        writer = csv.DictWriter(
            text_buf,
            fieldnames=["date", "time_from", "time_to", "activity", "details", "depth"],
        )
        writer.writeheader()
        writer.writerows(rows)
        text_buf.detach()
        buf.seek(0)
        return buf
```

### DDRDateCRUDRepository.get_dates_with_timelogs

Check `src/repository/crud/ddr.py` for existing `DDRDateCRUDRepository` — add the method there, not in a new file.

```python
async def get_dates_with_timelogs(self, ddr_id: str) -> list[DDRDate]:
    stmt = (
        sqlalchemy.select(DDRDate)
        .where(DDRDate.ddr_id == ddr_id)
        .where(DDRDate.status == "success")
        .where(DDRDate.final_json.isnot(None))
        .order_by(DDRDate.date.asc())
    )
    result = await self.async_session.execute(stmt)
    return list(result.scalars().all())
```

### 404 Logic

Two distinct 404 cases:
1. DDR row not found in `ddrs` table → `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`
2. DDR exists but no successfully processed dates → `{ "error": "Well data not found", "code": "NOT_FOUND", "details": {} }`

The epic specifies "Well data not found" for case 2. Use that exact message.

### media_type for UTF-8 BOM CSV

Use `media_type="text/csv; charset=utf-8-sig"` — the `utf-8-sig` charset signals BOM to clients. The BOM is also written directly to the buffer so Excel on Windows opens it correctly without an encoding dialog.

### No New Migration

No schema changes — reads from existing `ddr_dates.final_json`.

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-backend/src/services/export/csv_timelogs.py` | NEW |
| `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` | UPDATE — add `GET /export/timelogs/{ddr_id}` |
| `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py` | UPDATE — add `get_dates_with_timelogs` to `DDRDateCRUDRepository` |
| `ces-ddr-platform/ces-backend/tests/export/test_csv_timelogs.py` | NEW |

### References

- `src/resources/ddr_schema.json` — time_logs fields: start_time, end_time, duration_hours, activity, depth_md, comment, page_number
- `src/repository/crud/ddr.py` — `DDRDateCRUDRepository` — where to add the new method
- `src/api/routes/v1/export.py` (story 5.1) — router to extend
- `src/models/db/ddr.py:54` — `DDRDate` model — `final_json: Mapped[dict | None]`

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Completion Notes List
- `TimeLogCSVExportService.generate` writes UTF-8 BOM then uses `csv.DictWriter` via `TextIOWrapper` + detach
- `get_dates_with_timelogs` filters `status="success"` and `final_json IS NOT NULL` — ordered ASC
- Two 404 cases: DDR not found vs DDR exists but no processed dates (different error messages)
- 6 new tests all pass

### File List
- `ces-ddr-platform/ces-backend/src/services/export/csv_timelogs.py` — NEW
- `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` — added GET /export/timelogs/{ddr_id}
- `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py` — added get_dates_with_timelogs to DDRDateCRUDRepository
- `ces-ddr-platform/ces-backend/tests/export/test_csv_timelogs.py` — NEW

## Change Log

- 2026-05-18: Story created — time log CSV export backend
- 2026-05-18: Implemented — all ACs satisfied, 6 tests pass
