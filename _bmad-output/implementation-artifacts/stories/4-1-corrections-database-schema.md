# Story 4.1: Corrections Database Schema

Status: done

## Story

As a platform developer,
I want the corrections table created via Alembic migration on the Python backend,
So that every occurrence edit can be durably stored with full metadata in an append-only audit trail.

## Acceptance Criteria

**Given** migration `005_corrections` runs on the Python backend
**When** schema is inspected
**Then** `corrections` table exists: `id UUID PK`, `occurrence_id UUID REFERENCES occurrences(id)`, `ddr_id UUID REFERENCES ddrs(id)`, `field_name VARCHAR(100) NOT NULL`, `original_value TEXT NOT NULL`, `corrected_value TEXT NOT NULL`, `reason TEXT NOT NULL`, `user_id UUID REFERENCES users(id)`, `created_at TIMESTAMPTZ NOT NULL`
**And** indexes `idx_corrections_ddr_id` and `idx_corrections_occurrence_id` are created
**And** `corrections` table has no `updated_at` — append-only, never updated or deleted
**And** Alembic is the sole migration source for this schema

**Given** the ORM model is in place
**When** `Base.metadata` is inspected
**Then** `corrections` table is registered in metadata and `Correction` model has all required columns

**Given** Alembic env.py is updated
**When** `alembic upgrade head` runs from `ces-ddr-platform/ces-backend/`
**Then** migration chain 001 → 002 → 003 → 004 → 005 completes without error

## Tasks / Subtasks

- [x] **Task 1: Create Correction ORM model** (AC: 1, 2)
  - [x] Add `src/models/db/correction.py` with `Correction` SQLAlchemy model
  - [x] Columns: `id` (UUID PK), `occurrence_id` (UUID FK → occurrences.id), `ddr_id` (UUID FK → ddrs.id), `field_name` (String(100) NOT NULL), `original_value` (Text NOT NULL), `corrected_value` (Text NOT NULL), `reason` (Text NOT NULL), `user_id` (UUID FK → users.id), `created_at` (BigInteger NOT NULL)
  - [x] No `updated_at` — append-only table
  - [x] Add `__table_args__` with `idx_corrections_ddr_id` and `idx_corrections_occurrence_id`
  - [x] Add `Occurrence.corrections` relationship in `src/models/db/occurrence.py` (back_populates="occurrence")
  - [x] Add `DDR.corrections` relationship in `src/models/db/ddr.py` (back_populates="ddr")

- [x] **Task 2: Alembic migration `005_corrections`** (AC: 1, 3)
  - [x] File: `src/repository/migrations/versions/2026_05_18_0010-010_corrections.py` (adapted: chain was at 009, used 010)
  - [x] `revision = "010_corrections"`, `down_revision = "009_ddr_uploader"`
  - [x] `upgrade()`: `op.create_table("corrections", ...)` with all columns + `PrimaryKeyConstraint` + `ForeignKeyConstraint` for each FK
  - [x] `upgrade()`: create both indexes with `if_not_exists=True`
  - [x] `downgrade()`: drop both indexes, then drop table

- [x] **Task 3: Update Alembic env.py to register model** (AC: 3)
  - [x] In `src/repository/migrations/env.py`, add `correction` to the existing import: `from src.models.db import ddr, occurrence, user, correction`
  - [x] Add `correction` to `_models` tuple: `_models = (ddr, user, occurrence, correction)`

- [x] **Task 4: Pydantic schemas** (AC: 2)
  - [x] Add `src/models/schemas/correction.py`
  - [x] `CorrectionInCreate(BaseSchemaModel)`: `occurrence_id: str`, `ddr_id: str`, `field_name: str`, `original_value: str`, `corrected_value: str`, `reason: str`, `user_id: str`
  - [x] `CorrectionInResponse(BaseSchemaModel)`: all of above + `id: str`, `created_at: int`; add `model_config = ConfigDict(from_attributes=True)`

- [x] **Task 5: CRUD repository** (AC: 2)
  - [x] Add `src/repository/crud/correction.py` with `CorrectionCRUDRepository(BaseCRUDRepository[Correction])`
  - [x] `create_correction(occurrence_id, ddr_id, field_name, original_value, corrected_value, reason, user_id, commit=True) -> Correction`
  - [x] `get_by_ddr_id(ddr_id, limit=100, offset=0) -> list[Correction]`
  - [x] `get_all(field_name=None, ddr_id=None, limit=100, offset=0) -> list[Correction]` — filters optional, ordered by `created_at DESC`
  - [x] `get_recent(limit=20) -> list[Correction]` — ordered `created_at DESC`, used by context builder in story 4-3

- [x] **Task 6: Write backend tests** (AC: all)
  - [x] `tests/test_corrections_schema.py`
  - [x] Test: `Correction` in `Base.metadata.tables` — `corrections` key exists
  - [x] Test: `Correction` has no `updated_at` attribute
  - [x] Test: migration chain `010_corrections` → `down_revision = "009_ddr_uploader"` (adapted to actual chain)
  - [x] Test: `CorrectionCRUDRepository.create_correction` calls `BaseCRUDRepository.create` with correct dict (mock `async_session`)
  - [x] Test: `get_all` with `field_name` filter → WHERE clause targets `field_name` column
  - [x] Test: `get_recent` returns at most `limit` rows ordered by `created_at DESC`
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/` — 13/13 pass

## Dev Notes

### CRITICAL: Migration Number Is 005, NOT 004

The epic says "migration `004_corrections`" but **004 is already taken by `004_well_metadata` (story 4-0)**. Existing chain:
- `001_users_schema` → `002_ddr_schema` → `003_occurrences` → `004_well_metadata`

The new migration MUST be:
- `revision = "005_corrections"`, `down_revision = "004_well_metadata"`
- File: `2026_05_12_0005-005_corrections.py`

Using `004` will cause Alembic to fail with a duplicate revision error.

### CRITICAL: Timestamp Is BigInteger, NOT TIMESTAMPTZ

The epic says `created_at TIMESTAMPTZ NOT NULL` but **all existing tables use `BigInteger()` epoch integers**. Story 3-1 caught this same discrepancy. Use `BigInteger()` to match the established pattern. Using `TIMESTAMPTZ` would break ORM consistency across all repositories and require a different mapping type.

### Exact ORM Model

```python
# src/models/db/correction.py
from __future__ import annotations
from typing import TYPE_CHECKING
import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import text
from src.repository.table import Base

if TYPE_CHECKING:
    from src.models.db.occurrence import Occurrence
    from src.models.db.ddr import DDR
    from src.models.db.user import User


class Correction(Base):
    __tablename__ = "corrections"
    __table_args__ = (
        sqlalchemy.Index("idx_corrections_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_corrections_occurrence_id", "occurrence_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurrence_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("occurrences.id"), nullable=False
    )
    ddr_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(sqlalchemy.String(100), nullable=False)
    original_value: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    corrected_value: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    reason: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)
    # NO updated_at — append-only, never updated or deleted

    occurrence: Mapped["Occurrence"] = relationship(back_populates="corrections")
    ddr: Mapped["DDR"] = relationship(back_populates="corrections")
    user: Mapped["User"] = relationship()
```

### Exact Migration

```python
# src/repository/migrations/versions/2026_05_12_0005-005_corrections.py
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "005_corrections"
down_revision = "004_well_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corrections",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ddr_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["ddr_id"], ["ddrs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("idx_corrections_ddr_id", "corrections", ["ddr_id"], if_not_exists=True)
    op.create_index("idx_corrections_occurrence_id", "corrections", ["occurrence_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_corrections_occurrence_id", table_name="corrections")
    op.drop_index("idx_corrections_ddr_id", table_name="corrections")
    op.drop_table("corrections")
```

### env.py Update (exact diff)

Current line: `from src.models.db import ddr, occurrence, user`
New line: `from src.models.db import ddr, occurrence, user, correction`

Current line: `_models = (ddr, user, occurrence)`
New line: `_models = (ddr, user, occurrence, correction)`

File: `ces-ddr-platform/ces-backend/src/repository/migrations/env.py`

### Relationships to Add in Existing Models

**`src/models/db/occurrence.py`** — add after existing relationships (inside `Occurrence` class):
```python
corrections: Mapped[list["Correction"]] = relationship(back_populates="occurrence")
```
Also add to TYPE_CHECKING import block: `from src.models.db.correction import Correction`

**`src/models/db/ddr.py`** — add after existing relationships (inside `DDR` class):
```python
corrections: Mapped[list["Correction"]] = relationship(back_populates="ddr")
```
Also add to TYPE_CHECKING import block: `from src.models.db.correction import Correction`

### CRUD Pattern

Follow `OccurrenceCRUDRepository` exactly. Use `BaseCRUDRepository.create()` — do not write raw SQL or call `session.commit()` directly. Use `self.model` not `Correction` directly in queries to follow the generic pattern.

```python
# get_all with optional filters — pattern from OccurrenceCRUDRepository.get_by_ddr_id_filtered
async def get_all(
    self,
    field_name: str | None = None,
    ddr_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Correction]:
    stmt = (
        sqlalchemy.select(Correction)
        .order_by(Correction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if field_name is not None:
        stmt = stmt.where(Correction.field_name == field_name)
    if ddr_id is not None:
        stmt = stmt.where(Correction.ddr_id == ddr_id)
    result = await self.async_session.execute(stmt)
    return list(result.scalars().all())
```

### Pydantic Schema Pattern

Follow `src/models/schemas/occurrence.py`. Inherit `BaseSchemaModel` from `src/models/schemas/base.py`. Use `ConfigDict(from_attributes=True)` only on the response schema.

### What This Story Does NOT Include

- No API routes (story 4-2 adds `PATCH /occurrences/:id` and story 4-4 adds `GET /corrections`)
- No service layer logic (story 4-2 adds correction write service, story 4-3 adds context builder)
- No frontend changes
- No changes to `src/main.py` — the ORM model is picked up via `env.py` for migrations; no startup wiring needed for schema-only story

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-backend/src/models/db/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_12_0005-005_corrections.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/migrations/env.py` | UPDATE — add `correction` import + `_models` |
| `ces-ddr-platform/ces-backend/src/models/db/occurrence.py` | UPDATE — add `corrections` relationship |
| `ces-ddr-platform/ces-backend/src/models/db/ddr.py` | UPDATE — add `corrections` relationship |
| `ces-ddr-platform/ces-backend/src/models/schemas/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/crud/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/tests/test_corrections_schema.py` | NEW |

### References

- `src/repository/migrations/versions/2026_05_08_0003-003_occurrences.py` — exact migration pattern to follow (create_table, FKs, indexes, if_not_exists)
- `src/repository/migrations/versions/2026_05_12_0004-004_well_metadata.py` — current head revision (`004_well_metadata`), this story's `down_revision`
- `src/repository/migrations/env.py` — where to add `correction` to `_models` tuple
- `src/models/db/occurrence.py` — FK target `occurrences.id`; where to add `corrections` relationship
- `src/models/db/ddr.py` — FK target `ddrs.id`; where to add `corrections` relationship
- `src/models/db/user.py` — FK target `users.id`
- `src/repository/crud/occurrence.py` — CRUD pattern to follow exactly
- `src/models/schemas/occurrence.py` — Pydantic schema pattern to follow
- Story 3-1 (`stories/3-1-occurrences-database-schema.md`) — parallel schema story; established BigInteger timestamp override of TIMESTAMPTZ in epics

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Migration number adapted: story specified `005_corrections`/`down_revision=004_well_metadata` but actual chain was at `009_ddr_uploader`. Used `010_corrections` with `down_revision=009_ddr_uploader`.
- `pytest-asyncio` not installed; converted async test to `asyncio.run()` pattern matching existing test conventions.

### Completion Notes List

- `Correction` ORM model created — append-only (no `updated_at`), BigInteger epoch timestamp, UUID FKs to occurrences/ddrs/users, two indexes.
- `corrections` relationship added to `Occurrence` and `DDR` models via TYPE_CHECKING imports.
- Migration `010_corrections` created with idempotent `if_not_exists=True` guards; correct chain from `009_ddr_uploader`.
- env.py updated: `correction` module imported and added to `_models` tuple.
- `CorrectionInCreate` and `CorrectionInResponse` Pydantic schemas follow `BaseSchemaModel` pattern.
- `CorrectionCRUDRepository` implements `create_correction`, `get_by_ddr_id`, `get_all` (optional filters), `get_recent` — all follow `OccurrenceEditCRUDRepository` pattern.
- 13 tests pass, ruff clean, no regressions in full suite (2 pre-existing failures unrelated to this story).

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-backend/src/models/db/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_18_0010-010_corrections.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/migrations/env.py` | UPDATE — added `correction` import + `_models` |
| `ces-ddr-platform/ces-backend/src/models/db/occurrence.py` | UPDATE — added `corrections` relationship |
| `ces-ddr-platform/ces-backend/src/models/db/ddr.py` | UPDATE — added `corrections` relationship |
| `ces-ddr-platform/ces-backend/src/models/schemas/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/src/repository/crud/correction.py` | NEW |
| `ces-ddr-platform/ces-backend/tests/test_corrections_schema.py` | NEW |

### Review Findings

- [x] [Review][Decision] FK ON DELETE behavior missing — `corrections.occurrence_id`, `corrections.ddr_id`, `corrections.user_id` FKs have no `ON DELETE` rule (default RESTRICT). `OccurrenceCRUDRepository.replace_for_ddr` issues a bulk DELETE on occurrences; any existing corrections will cause a FK violation, breaking pipeline reprocess. `occurrence_edits` uses `ondelete="CASCADE"`. Choose: CASCADE (deletes corrections when parent deleted, loses audit trail), RESTRICT (current — blocks pipeline reprocess), or SET NULL. [`src/models/db/correction.py:29,32,39` / `010_corrections.py:23,24,25`]
- [x] [Review][Decision] `created_at` set via `int(time.time())` in app layer — deviates from project pattern where all other tables use PostgreSQL `server_default` (`EXTRACT(EPOCH FROM now())::BIGINT`). Risk: clock skew across app instances, retry produces duplicate timestamps. Fix requires adding `server_default` to ORM + migration AND removing `"created_at"` from `create_correction` dict. [`src/repository/crud/correction.py:32` / `src/models/db/correction.py:41`]
- [x] [Review][Patch] `get_all` applies `.limit().offset()` before `.where()` filters — misleading ordering; filters must precede pagination for clarity and future-safety. Functionally correct due to SQLAlchemy immutable builder, but fragile. [`src/repository/crud/correction.py:55-65`]
- [x] [Review][Defer] `user_id` in `CorrectionInCreate` is caller-supplied — security concern when API is wired (story 4-2); service layer must extract `user_id` from JWT, never accept from request body. [`src/models/schemas/correction.py:13`] — deferred, pre-existing in schema design; story 4-2 owns enforcement
- [x] [Review][Defer] No empty-string validation on `original_value`, `corrected_value`, `reason` — DB allows `""` silently. Add Pydantic validators in story 4-2 when API is built. [`src/models/schemas/correction.py`] — deferred, schema-only story
- [x] [Review][Defer] No upper-bound cap on `limit` parameter in `get_by_ddr_id`, `get_all`, `get_recent` — caller can pass `limit=999999`. Enforce in story 4-4 API layer. [`src/repository/crud/correction.py`] — deferred, pre-existing
- [x] [Review][Defer] `ddr_id` in `CorrectionInCreate` is derivable from `occurrence.ddr_id` — caller can supply mismatched pair. Story 4-2 service layer must validate `correction.ddr_id == occurrence.ddr_id`. [`src/models/schemas/correction.py:8`] — deferred, story 4-2
- [x] [Review][Defer] `CorrectionInResponse` exposes raw `user_id` UUID with no user info — consumers need N+1 lookup. Embed user sub-schema in story 4-4. [`src/models/schemas/correction.py`] — deferred, story 4-4
- [x] [Review][Defer] `field_name` is free-text `String(100)` with no enum/validation — typos create phantom correction categories. Validate against known field names in story 4-2 service layer. [`src/models/db/correction.py:34`] — deferred, story 4-2
- [x] [Review][Defer] No index on `field_name` — `get_all(field_name=x)` does full table scan. Add composite index `(field_name, ddr_id)` in story 4-4 if query patterns justify it. — deferred, story 4-4
- [x] [Review][Defer] `CorrectionInResponse.model_config` override drops `populate_by_name=True` and `validate_assignment=True` from `BaseSchemaModel` — same pattern exists in `OccurrenceInResponse` so pre-existing project-wide issue. [`src/models/schemas/correction.py:17`] — deferred, pre-existing pattern across all response schemas

## Change Log

- 2026-05-12: Story created — corrections database schema (migration 005, ORM, schemas, CRUD)
- 2026-05-18: Implemented all tasks — migration 010_corrections, ORM, env.py, Pydantic schemas, CRUD repository, 13 tests (all pass)
- 2026-05-18: Code review — 2 decision-needed, 1 patch, 10 deferred, 5 dismissed
