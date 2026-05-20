# Story 5.1: Per-DDR Excel Export Backend

Status: review

## Story

As a CES staff member,
I want to export all occurrences for a single DDR as a formatted .xlsx file with an edit history sheet when corrections exist,
So that I have a client-ready deliverable that is auditable and opens cleanly in Excel and LibreOffice.

## Acceptance Criteria

**Given** `GET /export/ddr/{ddr_id}` is called with a valid JWT for a DDR with occurrences
**When** the export is generated
**Then** response is a streaming `.xlsx` download with `Content-Disposition: attachment; filename="<ddr_id>_occurrences.xlsx"`
**And** Sheet 1 named "Occurrences" with columns: Well Name | Surface Location | Type | Section | mMD | Density | Notes
**And** header row has dark background (`#111827`) with white text
**And** export completes within 30 seconds for a full DDR occurrence set

**Given** the DDR has corrections in the `corrections` table
**When** the export is generated
**Then** Sheet 2 named "Edit History" is included with columns: Field | Original Value | Corrected Value | Reason | User | Timestamp | DDR Source
**And** if no corrections exist, Sheet 2 is omitted entirely

**Given** `GET /export/ddr/{ddr_id}` is called for a non-existent DDR
**When** the query finds no row
**Then** HTTP 404 is returned with `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`

## Tasks / Subtasks

- [x] **Task 1: Add openpyxl to pyproject.toml** (AC: all)
  - [x] Add with command `uv add openpyxl` to `[project.dependencies]` in `ces-ddr-platform/ces-backend/pyproject.toml`
  - [x] Run `uv sync` to lock: `source .venv/bin/activate && uv sync`

- [x] **Task 2: Create export service package** (AC: 1, 2)
  - [x] Create `src/services/export/__init__.py` (empty)
  - [x] Create `src/services/export/excel_report.py` with `DDRExcelExportService` class
  - [x] `generate(ddr_id, occurrences, corrections, ddr_source_label) -> io.BytesIO`
  - [x] Sheet 1 "Occurrences": header `#111827` bg / white font, columns: Well Name | Surface Location | Type | Section | mMD | Density | Notes
  - [x] Sheet 2 "Edit History": only included when `len(corrections) > 0`, columns: Field | Original Value | Corrected Value | Reason | User | Timestamp | DDR Source
  - [x] openpyxl is sync — wrap `wb.save(buf)` call in `asyncio.to_thread()` at the route level, or make `generate` a plain sync method called via `asyncio.to_thread`

- [x] **Task 3: Create export router** (AC: 1, 2, 3)
  - [x] Create `src/api/routes/v1/export.py`
  - [x] `GET /export/ddr/{ddr_id}` — auth via `jwt_authentication`
  - [x] Fetch DDR via `DDRCRUDRepository.read_by_id` → 404 if None
  - [x] Fetch occurrences via `OccurrenceCRUDRepository.get_by_ddr_id_filtered(ddr_id=ddr_id, limit=10000)`
  - [x] Fetch corrections via `CorrectionCRUDRepository.get_by_ddr_id(ddr_id=ddr_id, limit=10000)`
  - [x] Call `asyncio.to_thread(service.generate, ...)` — never block event loop
  - [x] Return `StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{ddr_id}_occurrences.xlsx"'})`

- [x] **Task 4: Register router in endpoints.py** (AC: 1)
  - [x] Import `export_router` in `src/api/endpoints.py`
  - [x] `router.include_router(router=export_router)` after existing includes

- [x] **Task 5: Write tests** (AC: all)
  - [x] Create `tests/export/` directory with `__init__.py`
  - [x] Create `tests/export/test_excel_report.py`
  - [x] Test: `DDRExcelExportService.generate` returns BytesIO with valid xlsx (open with openpyxl, check sheet names)
  - [x] Test: Sheet 1 header row cell fill = `#111827`, font color white
  - [x] Test: Sheet 2 "Edit History" present when corrections non-empty
  - [x] Test: Sheet 2 absent when corrections empty
  - [x] Test: `GET /export/ddr/{ddr_id}` returns 404 for unknown DDR (use TestClient with mock repos)
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest`

## Dev Notes

### CRITICAL: openpyxl NOT in pyproject.toml

`openpyxl` is referenced in the architecture spec but was never added to `pyproject.toml`. Add it first — the service will fail to import otherwise.

```toml
# ces-ddr-platform/ces-backend/pyproject.toml — add to [project.dependencies]
"openpyxl>=3.1.0,<4.0.0",
```

### CRITICAL: openpyxl is Synchronous — Wrap in asyncio.to_thread

Per CLAUDE.md rule: sync SDK calls must be wrapped in `asyncio.to_thread()`. `openpyxl` workbook operations are blocking. Pattern:

```python
import asyncio, io
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font

class DDRExcelExportService:
    def generate(
        self,
        occurrences: list,
        corrections: list,
        ddr_source_label: str,
    ) -> io.BytesIO:
        wb = Workbook()
        ws = wb.active
        ws.title = "Occurrences"
        
        HEADER_BG = "111827"
        header_fill = PatternFill("solid", fgColor=HEADER_BG)
        header_font = Font(color="FFFFFF", bold=True)
        
        headers = ["Well Name", "Surface Location", "Type", "Section", "mMD", "Density", "Notes"]
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
        
        for row_idx, occ in enumerate(occurrences, start=2):
            ws.cell(row=row_idx, column=1, value=occ.well_name)
            ws.cell(row=row_idx, column=2, value=occ.surface_location)
            ws.cell(row=row_idx, column=3, value=occ.type)
            ws.cell(row=row_idx, column=4, value=occ.section)
            ws.cell(row=row_idx, column=5, value=occ.mmd)
            ws.cell(row=row_idx, column=6, value=occ.density)
            ws.cell(row=row_idx, column=7, value=occ.notes)
        
        if corrections:
            ws2 = wb.create_sheet(title="Edit History")
            edit_headers = ["Field", "Original Value", "Corrected Value", "Reason", "User", "Timestamp", "DDR Source"]
            for col, h in enumerate(edit_headers, start=1):
                cell = ws2.cell(row=1, column=col, value=h)
                cell.fill = header_fill
                cell.font = header_font
            for row_idx, c in enumerate(corrections, start=2):
                ws2.cell(row=row_idx, column=1, value=c.field_name)
                ws2.cell(row=row_idx, column=2, value=c.original_value)
                ws2.cell(row=row_idx, column=3, value=c.corrected_value)
                ws2.cell(row=row_idx, column=4, value=c.reason)
                ws2.cell(row=row_idx, column=5, value=c.user_id)
                ws2.cell(row=row_idx, column=6, value=c.created_at)
                ws2.cell(row=row_idx, column=7, value=ddr_source_label)
        
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf
```

Route calls it as:
```python
buf = await asyncio.to_thread(service.generate, occurrences, corrections, ddr.file_path.split("/")[-1])
```

### CRITICAL: CorrectionCRUDRepository.get_by_ddr_id — Check Limit

`get_by_ddr_id(ddr_id, limit=100, offset=0)` defaults to `limit=100`. For export, pass `limit=10000` to get all corrections.

### Route Pattern — Follow ddr.py Exactly

```python
# src/api/routes/v1/export.py
import asyncio
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from src.api.dependencies.repository import get_repository
from src.repository.crud.ddr import DDRCRUDRepository
from src.repository.crud.occurrence import OccurrenceCRUDRepository
from src.repository.crud.correction import CorrectionCRUDRepository
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.export.excel_report import DDRExcelExportService

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/ddr/{ddr_id}")
async def export_ddr_excel(
    ddr_id: str,
    current_user=Depends(jwt_authentication),
    ddr_repository: DDRCRUDRepository = Depends(get_repository(DDRCRUDRepository)),
    occurrence_repository: OccurrenceCRUDRepository = Depends(get_repository(OccurrenceCRUDRepository)),
    correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository)),
) -> StreamingResponse:
    ddr = await ddr_repository.read_by_id(ddr_id)
    if ddr is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "DDR not found", "code": "NOT_FOUND", "details": {}},
        )
    occurrences = await occurrence_repository.get_by_ddr_id_filtered(ddr_id=ddr_id, limit=10000)
    corrections = await correction_repository.get_by_ddr_id(ddr_id=ddr_id, limit=10000)
    service = DDRExcelExportService()
    ddr_label = ddr.file_path.split("/")[-1]
    buf = await asyncio.to_thread(service.generate, occurrences, corrections, ddr_label)
    filename = f"{ddr_id}_occurrences.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

### endpoints.py Update

```python
# src/api/endpoints.py — add these two lines
from src.api.routes.v1.export import router as export_router
router.include_router(router=export_router)
```

### Correction.user_id in Edit History

`corrections` table has `user_id` (UUID string), not `username`. For export, write the `user_id` raw — story 4-4 defers embedding user sub-schema. This is acceptable for audit trail.

### No New Migration Needed

Export is pure service layer — reads existing `occurrences` and `corrections` tables. No schema changes.

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-backend/pyproject.toml` | UPDATE — add `openpyxl>=3.1.0,<4.0.0` |
| `ces-ddr-platform/ces-backend/src/services/export/__init__.py` | NEW |
| `ces-ddr-platform/ces-backend/src/services/export/excel_report.py` | NEW |
| `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` | NEW |
| `ces-ddr-platform/ces-backend/src/api/endpoints.py` | UPDATE — add export_router |
| `ces-ddr-platform/ces-backend/tests/export/__init__.py` | NEW |
| `ces-ddr-platform/ces-backend/tests/export/test_excel_report.py` | NEW |

### References

- `src/api/routes/v1/ddr.py` — exact router/dependency pattern to follow
- `src/api/endpoints.py` — where to register new router
- `src/repository/crud/correction.py` — `get_by_ddr_id(ddr_id, limit=100, offset=0)`
- `src/repository/crud/occurrence.py` — `get_by_ddr_id_filtered(ddr_id, limit=1000)`
- `src/models/db/occurrence.py` — Occurrence fields: well_name, surface_location, type, section, mmd, density, notes
- `src/models/db/correction.py` — Correction fields: field_name, original_value, corrected_value, reason, user_id, created_at

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Completion Notes List
- `DDRExcelExportService.generate` is sync, called via `asyncio.to_thread` in route
- Header fill uses `"FF111827"` (full ARGB) so openpyxl round-trips alpha correctly
- `CorrectionCRUDRepository._MAX_LIMIT` bumped to 10000 to allow full export; updated corresponding schema test
- 17 new tests, all pass; 4 pre-existing unrelated failures unchanged

### File List
- `ces-ddr-platform/ces-backend/pyproject.toml` — added openpyxl>=3.1.5
- `ces-ddr-platform/ces-backend/src/services/export/__init__.py` — NEW
- `ces-ddr-platform/ces-backend/src/services/export/excel_report.py` — NEW
- `ces-ddr-platform/ces-backend/src/api/routes/v1/export.py` — NEW
- `ces-ddr-platform/ces-backend/src/api/endpoints.py` — added export_router
- `ces-ddr-platform/ces-backend/src/repository/crud/correction.py` — _MAX_LIMIT 500→10000
- `ces-ddr-platform/ces-backend/tests/export/__init__.py` — NEW
- `ces-ddr-platform/ces-backend/tests/export/test_excel_report.py` — NEW
- `ces-ddr-platform/ces-backend/tests/test_corrections_schema.py` — updated _MAX_LIMIT assertion

## Change Log

- 2026-05-18: Story created — per-DDR Excel export backend
- 2026-05-18: Implemented — all ACs satisfied, 17 tests pass
