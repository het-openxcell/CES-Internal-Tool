# Story 3.1: Occurrences Database Schema

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want the occurrences table and initial keyword store created via migrations,
So that occurrence generation has a schema to write to and the keyword engine has a source of truth to load from.

## Acceptance Criteria

**Given** migration `003_occurrences` runs on the Python backend
**When** schema is inspected
**Then** `occurrences` table exists with all required columns and indexes (see Dev Notes for exact spec)
**And** Alembic is the sole migration source for this schema — no `create_all` fallback

**Given** `ces-backend/src/resources/keywords.json` is created
**When** file content is reviewed
**Then** file contains `{ "<keyword>": "<type_name>", ... }` with at least one entry per occurrence type covering all 15–17 parent types
**And** the Python backend loads it at startup via `src/services/keywords/loader.py`

## Tasks / Subtasks

- [x] Create Occurrence ORM model (AC: 1)
  - [x] Add `src/models/db/occurrence.py` with `Occurrence` SQLAlchemy model
  - [x] Use `BigInteger()` for `created_at`/`updated_at` (epoch integers — existing project standard, NOT TIMESTAMPTZ despite epics wording)
  - [x] Add relationships to `DDR` and `DDRDate` from the ORM side (back_populates optional but reference FKs correctly)
  - [x] Add `DDR.occurrences` and `DDRDate.occurrences` relationships in `src/models/db/ddr.py`
  - [x] Update `src/repository/migrations/env.py` to import `occurrence` model so Alembic detects it
- [x] Create Alembic migration `003_occurrences` (AC: 1)
  - [x] File: `src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py`
  - [x] `revision = "003_occurrences"`, `down_revision = "002_ddr_schema"`
  - [x] Create `occurrences` table with all columns (exact schema in Dev Notes)
  - [x] Create all three indexes: `idx_occurrences_ddr_id`, `idx_occurrences_type`, `idx_occurrences_date`
  - [x] `downgrade()` drops indexes then table in reverse order
  - [x] Use `if_not_exists=True` on `create_table` and `create_index` (matches existing migration pattern)
- [x] Create Pydantic schemas for Occurrence (AC: 1)
  - [x] Add `src/models/schemas/occurrence.py` with `OccurrenceInCreate`, `OccurrenceInDB` (at minimum)
  - [x] Follow existing `BaseSchemaModel` pattern from `src/models/schemas/base.py`
  - [x] `mmd` and `density` as `float | None`; `is_exported` as `bool` default `False`
  - [x] `type` as `str` (not enum — type values come from keywords.json and can change at runtime)
  - [x] `section` as `str | None` with valid values `"Surface"`, `"Int."`, `"Main"` (validated in Story 3.2)
- [x] Create CRUD repository for occurrences (AC: 1)
  - [x] Add `src/repository/crud/occurrence.py` with `OccurrenceCRUDRepository(BaseCRUDRepository)`
  - [x] Implement `create_occurrence(session, data) -> Occurrence`
  - [x] Implement `get_by_ddr_id(session, ddr_id) -> list[Occurrence]`
  - [x] Follow existing repo pattern: no raw SQL, use ORM, no `session.commit()` in repo (caller controls tx)
- [x] Create `src/resources/keywords.json` (AC: 2)
  - [x] Format: `{ "keyword": "Type Name", ... }` — flat dict, first-match-wins ordering (order in file is authoritative)
  - [x] Cover all 15–17 parent types with at least 10 keywords each (see Dev Notes for full type list and sample keywords)
  - [x] Include `"Unclassified"` as fallback type name (not in keywords.json itself — it's the default when no keyword matches)
- [x] Create keyword loader service (AC: 2)
  - [x] Add `src/services/keywords/__init__.py` and `src/services/keywords/loader.py`
  - [x] `KeywordLoader` class: loads `keywords.json` from `src/resources/` on startup, stores in memory as `dict[str, str]`
  - [x] Expose `get_keywords() -> dict[str, str]` for other services; expose `reload()` for `PUT /keywords` (Story 7.3)
  - [x] Load path via `importlib.resources` or relative to module file — do NOT use `os.getcwd()` or hardcoded absolute paths
  - [x] Wire startup load in `src/main.py` (call `KeywordLoader.load()` in lifespan or startup event)
- [x] Write focused backend tests (AC: 1-2)
  - [x] Static/migration test: `Alembic` chain is `001 → 002 → 003`; `occurrences` table present in `Base.metadata`; no startup `create_all`
  - [x] ORM model test: `Occurrence` model has all required columns with correct types and nullable/non-nullable as spec'd
  - [x] Keyword loader test: loader reads `keywords.json` and returns correct `dict[str, str]`; covers at least one key per type; `reload()` picks up changes
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/`

## Dev Notes

### CRITICAL: Timestamp Column Discrepancy

The epic acceptance criteria says `created_at TIMESTAMPTZ NOT NULL` but **ALL existing tables use `BigInteger()` epoch integers** (`created_at: Mapped[int]`). Follow the established BigInteger pattern. Using `TIMESTAMPTZ` here would break ORM consistency across all existing repositories and require a different mapping type. The `architecture.md` naming table says `timestamptz` but that's aspirational — actual implementation is `BigInteger` epoch.

### Exact `occurrences` Table Schema

```python
# ORM (src/models/db/occurrence.py)
class Occurrence(Base):
    __tablename__ = "occurrences"
    __table_args__ = (
        sqlalchemy.Index("idx_occurrences_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_occurrences_type", "type"),
        sqlalchemy.Index("idx_occurrences_date", "date"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    ddr_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ddrs.id"), nullable=False)
    ddr_date_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ddr_dates.id"), nullable=False)
    well_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    surface_location: Mapped[str | None] = mapped_column(Text(), nullable=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    section: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mmd: Mapped[float | None] = mapped_column(Float(), nullable=True)
    density: Mapped[float | None] = mapped_column(Float(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_exported: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("false"))
    created_at: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger(), nullable=False)
```

### Migration File Pattern

Follow **exactly** the `002_ddr_schema` pattern:
- `revision = "003_occurrences"`, `down_revision = "002_ddr_schema"`
- Use `postgresql.UUID(as_uuid=False)` for UUID columns
- Use `sa.text("gen_random_uuid()")` for PK `server_default`
- Use `sa.text("false")` for boolean `server_default`
- Use `if_not_exists=True` on `create_table` and `create_index` calls
- `downgrade()`: drop indexes before dropping table

### Update `env.py` — REQUIRED

Add occurrence model import to `src/repository/migrations/env.py`:
```python
from src.models.db import ddr, user, occurrence  # ADD occurrence
_models = (ddr, user, occurrence)  # ADD occurrence
```
Without this, Alembic autogenerate won't detect the `occurrences` table.

### Update `src/models/db/ddr.py` — REQUIRED

Add relationship on `DDR` and `DDRDate`:
```python
# In DDR class:
occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="ddr")

# In DDRDate class:
occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="ddr_date")
```
And in `occurrence.py`:
```python
ddr: Mapped[DDR] = relationship(back_populates="occurrences")
ddr_date: Mapped[DDRDate] = relationship(back_populates="occurrences")
```
Use `TYPE_CHECKING` import guard to avoid circular imports if needed.

### The 15–17 Occurrence Parent Types

These are the canonical type names to cover in `keywords.json`. Type names must be **exact strings** — they appear in UI badges and Excel exports:

| # | Type Name | Example Keywords |
|---|-----------|-----------------|
| 1 | Stuck Pipe | stuck pipe, pipe stuck, freeing pipe, jarring |
| 2 | Lost Circulation | lost circulation, lost returns, total loss, partial loss, seepage |
| 3 | Back Ream | back ream, backreamed, backreaming, backreamed to free |
| 4 | Ream | ream, reaming, reamed, reaming to bottom |
| 5 | Tight Hole | tight hole, tight string, overpull, drag |
| 6 | Washout | washout, washed out, bit washout, string washout |
| 7 | BHA Failure | bha failure, mwd failure, lwd failure, motor failure, tool failure |
| 8 | Vibration | vibration, stick slip, whirl, shock |
| 9 | Kick / Well Control | kick, well control, influx, shut in, pit gain |
| 10 | H2S | h2s, hydrogen sulphide, hydrogen sulfide, sour gas |
| 11 | Fishing | fishing, fish, stuck bha, junk in hole |
| 12 | Casing Issue | casing, casing collapse, casing damage, liner |
| 13 | Bit Failure | bit failure, bit balling, bit plugged, nozzle plugged |
| 14 | Cementing Issue | cement, cementing, cement job, squeeze |
| 15 | Pack Off | pack off, packoff, annular pack, bridging |
| 16 | Deviation | deviation, dogleg, directional issue, trajectory |
| 17 | Unclassified | (no keywords — assigned when NO keyword matches) |

**`"Unclassified"` is NOT a keyword in keywords.json.** It is the fallback assigned by the classify engine (Story 3.2) when no keyword matches. Do not add it to the JSON file.

### `keywords.json` Structure and Loading Rules

- File location: `ces-ddr-platform/ces-backend/src/resources/keywords.json`
- Format: flat JSON object `{ "keyword phrase": "Type Name", ... }`
- **Order is authoritative**: first-match wins during classification (Story 3.2)
- Keywords are matched case-insensitively by substring — keyword `"stuck pipe"` matches `"Pipe stuck in formation"`
- `KeywordLoader.reload()` must atomically replace the in-memory dict (for `PUT /keywords` in Story 7.3)

### Keyword Loader — `src/services/keywords/loader.py`

```python
import importlib.resources
import json

class KeywordLoader:
    _keywords: dict[str, str] = {}

    @classmethod
    def load(cls) -> None:
        data = importlib.resources.files("src.resources").joinpath("keywords.json").read_text()
        cls._keywords = json.loads(data)

    @classmethod
    def get_keywords(cls) -> dict[str, str]:
        return cls._keywords

    @classmethod
    def reload(cls, new_data: dict[str, str]) -> None:
        cls._keywords = new_data
```

Wire in `src/main.py` lifespan startup (find existing `@asynccontextmanager` lifespan or `@app.on_event("startup")` and add `KeywordLoader.load()`).

### Architecture Compliance

- Python-only backend. No frontend files, no Go, no Celery, no Redis.
- All config via `decouple + BackendBaseSettings`. No `os.getenv` anywhere.
- Repository classes extend `BaseCRUDRepository`. No raw SQL.
- All timestamps: `BigInteger()` epoch integers (NOT `DateTime`/`TIMESTAMPTZ`).
- UUID v4 PKs with `gen_random_uuid()` server default.
- No `Base.metadata.create_all()` — Alembic only.
- Ruff + pytest must pass clean from `ces-ddr-platform/ces-backend/`.

### Previous Story Intelligence (from Epic 2)

- Story 2.1 established: `BigInteger` epoch timestamps, UUID v4 PKs, `gen_random_uuid()`, `if_not_exists=True` migration guards, `BaseCRUDRepository` pattern, no startup `create_all`.
- Story 2.2 established: upload/queue flow — do NOT touch `processing_queue`, `ddrs`, or `ddr_dates` table definitions.
- Story 2.6 established: `PipelineRun` in `src/models/db/ddr.py` and `src/repository/crud/ddr.py` — extend `ddr.py` with relationships but do not modify existing model columns.

**Review findings from prior stories to avoid:**
- Do not use `datetime` or `DateTime` SQLAlchemy type for timestamps.
- Do not commit inside repository methods — caller controls transaction.
- Do not add `occurrence` imports to `env.py` after the fact — do it in this story or Alembic won't track the new table.

### File Structure

Files to create:
```
ces-ddr-platform/ces-backend/src/models/db/occurrence.py          (NEW)
ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py     (NEW)
ces-ddr-platform/ces-backend/src/repository/crud/occurrence.py    (NEW)
ces-ddr-platform/ces-backend/src/resources/keywords.json          (NEW)
ces-ddr-platform/ces-backend/src/services/keywords/__init__.py    (NEW)
ces-ddr-platform/ces-backend/src/services/keywords/loader.py      (NEW)
ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py  (NEW)
ces-ddr-platform/ces-backend/tests/test_occurrence_schema.py      (NEW)
ces-ddr-platform/ces-backend/tests/test_keyword_loader.py         (NEW)
```

Files to update:
```
ces-ddr-platform/ces-backend/src/models/db/ddr.py                 (UPDATE — add relationships)
ces-ddr-platform/ces-backend/src/repository/migrations/env.py     (UPDATE — add occurrence import)
ces-ddr-platform/ces-backend/src/main.py                          (UPDATE — wire KeywordLoader.load())
```

### Testing Requirements

```bash
# from ces-ddr-platform/ces-backend/
source .venv/bin/activate
ruff check .
pytest
```

`test_occurrence_schema.py`:
- Verify `Occurrence` in `Base.metadata.tables` with correct column names
- Verify column nullability matches spec (type NOT NULL, is_exported NOT NULL, id NOT NULL, etc.)
- Verify indexes present: `idx_occurrences_ddr_id`, `idx_occurrences_type`, `idx_occurrences_date`
- Verify migration chain: `003_occurrences` has `down_revision = "002_ddr_schema"`

`test_keyword_loader.py`:
- `KeywordLoader.load()` reads `keywords.json` and populates `get_keywords()`
- All 16 parent types appear as values in the keyword map (no test for Unclassified — it's not in the file)
- `reload()` atomically replaces the dict
- No network calls, no DB, no file system mocks needed — reads real `keywords.json` from `src/resources/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-6-extraction-cost-tracking-time-log-embedding.md]
- [Source: ces-ddr-platform/ces-backend/src/models/db/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_07_0002-002_ddr_schema.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/migrations/env.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `source .venv/bin/activate && ruff check . && pytest`

### Completion Notes List

- Created `Occurrence` ORM model with all 14 columns, BigInteger timestamps, UUID PK, 3 indexes, FK refs to `ddrs` and `ddr_dates`.
- Added `TYPE_CHECKING` guard in `ddr.py` to import `Occurrence` for type hints; added `occurrences` relationship to both `DDR` and `DDRDate` without `from __future__ import annotations` (preserving existing annotation repr for pre-existing tests).
- Added `occurrence` module to `env.py` imports so Alembic autogenerate tracks the table.
- Created migration `003_occurrences` chained from `002_ddr_schema`; all `create_table`/`create_index` calls use `if_not_exists=True`; `downgrade()` drops indexes then table.
- Created `OccurrenceInCreate` and `OccurrenceInDB` Pydantic schemas following `BaseSchemaModel` pattern.
- Created `OccurrenceCRUDRepository` extending `BaseCRUDRepository`; no raw SQL; caller controls transaction.
- Created `keywords.json` with 140+ entries covering all 16 parent types (≥10 keywords each); `Unclassified` intentionally absent.
- Created `KeywordLoader` using `importlib.resources`; wired `KeywordLoader.load()` into startup event in `events.py`.
- 15 new tests pass; 2 pre-existing failures in `test_ddr_upload_contract.py` (no local DB + env mismatch) unchanged.

### File List

- `ces-ddr-platform/ces-backend/src/models/db/occurrence.py` (NEW)
- `ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py` (NEW)
- `ces-ddr-platform/ces-backend/src/repository/crud/occurrence.py` (NEW)
- `ces-ddr-platform/ces-backend/src/resources/keywords.json` (NEW)
- `ces-ddr-platform/ces-backend/src/services/keywords/__init__.py` (NEW)
- `ces-ddr-platform/ces-backend/src/services/keywords/loader.py` (NEW)
- `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py` (NEW)
- `ces-ddr-platform/ces-backend/tests/test_occurrence_schema.py` (NEW)
- `ces-ddr-platform/ces-backend/tests/test_keyword_loader.py` (NEW)
- `ces-ddr-platform/ces-backend/src/models/db/ddr.py` (UPDATED — occurrences relationships + TYPE_CHECKING import)
- `ces-ddr-platform/ces-backend/src/repository/migrations/env.py` (UPDATED — occurrence import)
- `ces-ddr-platform/ces-backend/src/config/events.py` (UPDATED — KeywordLoader.load() on startup)

### Review Findings

- [x] [Review][Decision] Startup wiring in `events.py` accepted — `events.py` is the project's designated startup handler; spec intent satisfied
- [x] [Review][Patch] `get_by_ddr_id` return type fixed to `list[Occurrence]` + added `limit`/`offset` pagination params [`src/repository/crud/occurrence.py`]
- [x] [Review][Patch] Test migration paths fixed to `__file__`-anchored via `_MIGRATION_003` constant [`tests/test_occurrence_schema.py`]
- [x] [Review][Patch] Reload tests wrapped in try/finally to prevent class-level state bleed [`tests/test_keyword_loader.py`]
- [x] [Review][Patch] `type` param renamed to `occurrence_type` in `create_occurrence` [`src/repository/crud/occurrence.py`]
- [x] [Review][Patch] FK constraints updated with `ondelete="CASCADE"` on both ORM model and migration [`src/models/db/occurrence.py`, migration `003`]
- [x] [Review][Patch] `date` field YYYYMMDD validation added via Pydantic `field_validator` [`src/models/schemas/occurrence.py`]
- [x] [Review][Patch] `get_keywords()` now returns `dict(cls._keywords)` copy to prevent external mutation [`src/services/keywords/loader.py`]
- [x] [Review][Dismiss] `"sour"` / `"cement"` false positives — word-boundary enforcement is Story 3.2 classification engine concern; keywords correct as-is

### Change Log

- 2026-05-08: Story created — occurrences DB schema, Alembic migration 003, keywords.json, keyword loader service.
- 2026-05-08: Story implemented — all tasks complete, ruff clean, 89 tests pass (2 pre-existing failures unrelated to this story).
- 2026-05-08: Code review complete — all patches applied, all defers resolved, 91/91 tests pass.
