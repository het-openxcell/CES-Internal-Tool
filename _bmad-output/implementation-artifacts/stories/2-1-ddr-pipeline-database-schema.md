# Story 2.1: DDR & Pipeline Database Schema

Status: in-progress

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want DDR, pipeline, and cost tracking tables created via migrations on the Python backend,
so that all extraction pipeline data has a durable, structured home before any pipeline code runs.

## Acceptance Criteria

1. Given migration `002_ddr_schema` runs on the Python backend, when schema is inspected, then `ddrs` table exists with `id UUID PK`, `file_path TEXT NOT NULL`, `status VARCHAR(20) NOT NULL DEFAULT 'queued'`, `well_name TEXT`, `created_at BIGINT NOT NULL`, and `updated_at BIGINT NOT NULL`.
2. Given migration `002_ddr_schema` runs, when schema is inspected, then `ddr_dates` table exists with `id UUID PK`, `ddr_id UUID REFERENCES ddrs(id)`, `date VARCHAR(8) NOT NULL`, `status VARCHAR(20) NOT NULL`, `raw_response JSONB`, `final_json JSONB`, `error_log JSONB`, `created_at BIGINT NOT NULL`, and `updated_at BIGINT NOT NULL`.
3. Given migration `002_ddr_schema` runs, when schema is inspected, then `processing_queue` table exists with `id UUID PK`, `ddr_id UUID REFERENCES ddrs(id)`, `position INT NOT NULL`, and `created_at BIGINT NOT NULL`.
4. Given migration `002_ddr_schema` runs, when schema is inspected, then `pipeline_runs` table exists with `id UUID PK`, `ddr_date_id UUID REFERENCES ddr_dates(id)`, `gemini_input_tokens INT`, `gemini_output_tokens INT`, `cost_usd NUMERIC(10,6)`, and `created_at BIGINT NOT NULL`.
5. Given schema indexes are inspected, then `idx_ddr_dates_ddr_id` and `idx_processing_queue_ddr_id` exist, and Alembic is the sole migration source for the DDR pipeline schema.
6. Given `ddrs.status` is set by application code, when valid strings are reviewed, then only `queued`, `processing`, `complete`, and `failed` are accepted by schemas/services.
7. Given `ddr_dates.status` is set by application code, when valid strings are reviewed, then only `queued`, `success`, `warning`, and `failed` are accepted by schemas/services.
8. Given Docker Compose runs, when backend upload storage is inspected, then named Docker volume `pdfs` is declared and mounted at `/app/uploads` in the backend container.

## Tasks / Subtasks

- [x] Add SQLAlchemy ORM models for DDR pipeline persistence (AC: 1-4, 6-7)
  - [x] Create `ces-backend/src/models/db/ddr.py` with classes `DDR`, `DDRDate`, `ProcessingQueue`, and `PipelineRun`.
  - [x] Use existing `Base` from `src.repository.table`; do not create a second declarative base or metadata object.
  - [x] Use PostgreSQL `UUID(as_uuid=False)` primary keys with `server_default=sqlalchemy.text("gen_random_uuid()")`, matching `User`.
  - [x] Use `BigInteger` epoch columns for every timestamp. Do not use `TIMESTAMPTZ`, `DateTime`, Python `datetime`, or ISO strings in DB models.
  - [x] Add ORM relationships only where they improve clarity and do not create circular import workarounds.
- [x] Add Pydantic schemas and status constants (AC: 1-7)
  - [x] Create `ces-backend/src/models/schemas/ddr.py` with response/create/read schemas needed by future stories.
  - [x] Keep fields `snake_case`; UUIDs can remain strings at API boundary to match current project pattern.
  - [x] Encapsulate status values in class-based constants, enums, or schema validators. Do not scatter loose string variables.
  - [x] Include `queued` as valid `ddr_dates.status` because Story 2.3 creates queued date rows before extraction, even though Epic 2.1 source text omits it.
- [x] Add repository classes for new tables (AC: 1-7)
  - [x] Create `ces-backend/src/repository/crud/ddr.py`.
  - [x] Add repository classes such as `DDRCRUDRepository`, `DDRDateCRUDRepository`, `ProcessingQueueCRUDRepository`, and `PipelineRunCRUDRepository`.
  - [x] Extend `BaseCRUDRepository`; keep persistence inside classes, not loose query helpers.
  - [x] Commit transaction boundaries intentionally. If multiple row writes must be atomic for tests, add repository/service method that uses one session transaction.
- [x] Add Alembic revision for DDR schema (AC: 1-5)
  - [x] Create an Alembic version file under `ces-backend/src/repository/migrations/versions/` with slug `ddr_schema`.
  - [x] Before writing revision metadata, inspect current Alembic heads. If no user-table revision exists, do not create a broken divergent migration chain; add or repair the missing baseline in the smallest scope needed, then chain DDR migration after it.
  - [x] Use Alembic operations as migration authority. Do not rely on `Base.metadata.create_all()` in app startup or tests.
  - [x] Create tables and indexes in upgrade; drop indexes/tables in dependency-safe reverse order in downgrade.
  - [x] Do not add SQL file migrations or any Go migration artifacts.
- [x] Update Docker Compose upload volume (AC: 8)
  - [x] Update `ces-ddr-platform/docker-compose.yml` to declare named volume `pdfs`.
  - [x] Mount `pdfs:/app/uploads` into the backend service if a backend service exists in compose.
  - [x] If the backend service is not yet declared, add the volume declaration and document that backend container mount remains blocked until backend service is added; do not invent a production-ready backend compose service in this story.
- [x] Add focused backend tests (AC: 1-8)
  - [x] Add tests under `ces-backend/tests/` that inspect SQLAlchemy model table names, columns, nullable flags, defaults, foreign keys, and indexes.
  - [x] Add repository tests using an async session or repository-level doubles consistent with existing tests.
  - [x] Add migration tests that assert the Alembic version file exists and includes expected table/index operations.
  - [x] Add status validation tests for DDR and DDR date statuses.
  - [x] Add Docker Compose YAML test or static assertion for `pdfs` volume and `/app/uploads` mount/declaration.
- [x] Preserve backend foundation behavior (AC: all)
  - [x] Do not modify auth routes, JWT behavior, password hashing, frontend files, Qdrant, Gemini extraction, PDF upload endpoint, SSE stream, occurrence generation, corrections, export, or search.
  - [x] Do not read real `.env` values in tests.
  - [x] Do not add comments to source files.

### Review Findings

- [ ] [Review][Patch] Startup still calls `Base.metadata.create_all`, letting app startup bypass Alembic and create DDR tables without `alembic_version` [ces-ddr-platform/ces-backend/src/repository/events.py:44]
- [x] [Review][Patch] Users baseline migration fails on current database when `users` already exists but Alembic is unstamped [ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_07_0001-001_users_schema.py:14]
- [x] [Review][Patch] Migration coverage is static text-only and missed the live duplicate-table Alembic failure [ces-ddr-platform/ces-backend/tests/test_ddr_schema.py:119]
- [x] [Review][Patch] Processing queue position has no database uniqueness guard, so duplicate FIFO positions can persist [ces-ddr-platform/ces-backend/src/models/db/ddr.py:61]
- [x] [Review][Patch] DDR date reads are nondeterministic because `read_dates_by_ddr_id` has no ordering [ces-ddr-platform/ces-backend/src/repository/crud/ddr.py:84]
- [x] [Review][Patch] Pipeline run cost repository accepts `float`, which can drift before `NUMERIC(10,6)` storage [ces-ddr-platform/ces-backend/src/repository/crud/ddr.py:123]

## Dev Notes

### Current Sprint State

Epic 1 is marked `done`; Epic 2 is now being started with this story. The sprint status already records the approved backend structure alignment change, so this story must use the current Python-only backend structure rather than older Go or dual-backend references. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md]

### Existing Backend State

Current backend root is `ces-ddr-platform/ces-backend/`. It already contains:

- `src/repository/table.py`: single SQLAlchemy `DeclarativeBase` and `Base`.
- `src/models/db/user.py`: existing model style for UUID primary key and epoch `BigInteger` timestamps.
- `src/repository/database.py`: async SQLAlchemy engine/session factory loaded from `decouple + BackendBaseSettings` settings.
- `src/repository/crud/base.py`: generic async repository class.
- `src/repository/crud/user.py`: repository-class pattern to copy.
- `src/repository/migrations/env.py`: Alembic wired to `Base.metadata` and async DB URI.
- `src/repository/migrations/versions/`: currently empty in the working tree.

Read these files before editing. Extend current structure; do not create `app/`, `db/queries`, root migration folders, SQL scripts, or standalone utility modules. [Source: ces-ddr-platform/ces-backend/src/repository/table.py] [Source: ces-ddr-platform/ces-backend/src/models/db/user.py] [Source: ces-ddr-platform/ces-backend/src/repository/database.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/base.py] [Source: ces-ddr-platform/ces-backend/src/repository/crud/user.py] [Source: ces-ddr-platform/ces-backend/src/repository/migrations/env.py]

### Schema Requirements

Canonical tables:

```text
ddrs
  id UUID PK DEFAULT gen_random_uuid()
  file_path TEXT NOT NULL
  status VARCHAR(20) NOT NULL DEFAULT 'queued'
  well_name TEXT NULL
  created_at BIGINT NOT NULL
  updated_at BIGINT NOT NULL

ddr_dates
  id UUID PK DEFAULT gen_random_uuid()
  ddr_id UUID NOT NULL REFERENCES ddrs(id)
  date VARCHAR(8) NOT NULL
  status VARCHAR(20) NOT NULL
  raw_response JSONB NULL
  final_json JSONB NULL
  error_log JSONB NULL
  created_at BIGINT NOT NULL
  updated_at BIGINT NOT NULL

processing_queue
  id UUID PK DEFAULT gen_random_uuid()
  ddr_id UUID NOT NULL REFERENCES ddrs(id)
  position INT NOT NULL
  created_at BIGINT NOT NULL

pipeline_runs
  id UUID PK DEFAULT gen_random_uuid()
  ddr_date_id UUID NOT NULL REFERENCES ddr_dates(id)
  gemini_input_tokens INT NULL
  gemini_output_tokens INT NULL
  cost_usd NUMERIC(10,6) NULL
  created_at BIGINT NOT NULL
```

Indexes:

```text
idx_ddr_dates_ddr_id on ddr_dates(ddr_id)
idx_processing_queue_ddr_id on processing_queue(ddr_id)
```

Use application-enforced status validation unless there is already a local pattern for database check constraints. Do not add status values beyond those needed by Epic 2: DDR `queued | processing | complete | failed`; DDR date `queued | success | warning | failed`. [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]

### Timestamp Conflict Resolution

The original Epic 2.1 text says `TIMESTAMPTZ`, but project instructions and the approved backend structure change require all timestamps to be epoch integers. Implement `created_at` and `updated_at` as `BIGINT` epoch seconds, matching the existing `User` model. This story intentionally overrides the old `TIMESTAMPTZ` wording. [Source: AGENTS.md Backend Guidelines] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md#Technical Impact] [Source: ces-ddr-platform/ces-backend/src/models/db/user.py]

### Migration Guardrails

Alembic is the only migration authority. The migration script location is `src/repository/migrations`, and `env.py` uses `Base.metadata`. Import the new DDR models where needed so Alembic metadata sees them. Do not call `create_all()` in application startup to compensate for migration issues. [Source: ces-ddr-platform/ces-backend/alembic.ini] [Source: ces-ddr-platform/ces-backend/src/repository/migrations/env.py]

The versions directory is currently empty. Because Epic 1 is marked done but no version file is present, first inspect whether a user-table migration is missing from the working tree. If there is no current Alembic head, create a valid migration chain rather than a revision whose `down_revision` points to a nonexistent file. Keep any baseline repair minimal and covered by tests. [Source: ces-ddr-platform/ces-backend/src/repository/migrations/versions]

### Docker Compose Guardrails

Current `ces-ddr-platform/docker-compose.yml` contains only `postgres` and `qdrant`; no backend service is declared. Story 2.1 still requires a named `pdfs` volume and `/app/uploads` backend mount when compose runs. If adding a backend service is outside current compose scope, declare `pdfs` now and leave the mount requirement explicit for the story that adds the backend container. Do not expand `docker-compose.prod.yml`, which is currently a placeholder, unless tests or existing deployment docs already require it. [Source: ces-ddr-platform/docker-compose.yml] [Source: ces-ddr-platform/docker-compose.prod.yml]

### Architecture Compliance

Backend feature flow must remain:

```text
route/dependency -> service class -> repository class -> SQLAlchemy ORM model
```

This story mostly touches models, schemas, repositories, migrations, tests, and compose. No route is required yet. If a small service class is useful for status validation or queue positioning, place it under `src/services/` and keep it class-based. No loose functions or global mutable state. [Source: _bmad-output/planning-artifacts/architecture.md#Component Boundaries] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md]

### Latest Technical Information

Project dependencies currently pin SQLAlchemy `>=2.0.0,<3.0.0` and Alembic `>=1.18.4,<2.0.0`. Official SQLAlchemy docs list the 2.0 line as current, with 2.0.49 current release on April 3, 2026. Alembic official docs list 1.18.4 documentation as current. Keep implementation on existing dependency ranges; do not upgrade packages for this schema story unless tests prove a local bug requires it. [Source: ces-ddr-platform/ces-backend/pyproject.toml] [Source: https://docs.sqlalchemy.org/20/intro.html] [Source: https://alembic.sqlalchemy.org/en/latest/changelog.html]

PostgreSQL official docs for version 16 document `gen_random_uuid()` as returning UUID v4. Existing `User` model already uses `server_default=sqlalchemy.text("gen_random_uuid()")`; copy that pattern for new IDs. [Source: https://www.postgresql.org/docs/16/pgcrypto.html] [Source: ces-ddr-platform/ces-backend/src/models/db/user.py]

### Previous Story Intelligence

Story 1.4 was frontend-only, but review findings matter: previous review caught scope creep, raw implementation leaks, and comments violating repo rules. Apply that lesson here: keep story 2.1 strictly backend schema/compose focused; no upload endpoint, no pipeline execution, no Gemini calls, no frontend UI, and no source-file comments. [Source: _bmad-output/implementation-artifacts/stories/1-4-frontend-authentication-shell-protected-routing.md]

Stories 1.2 and 1.3 established current backend patterns but the active tree now shows no Alembic version files. Do not assume migrations exist just because sprint status says Epic 1 is done. Verify local files and make the migration chain real. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: ces-ddr-platform/ces-backend/src/repository/migrations/versions]

### Git Intelligence

Recent commits show backend cleanup and exception work:

```text
42309be Implement unified exception handling system with strategies and registry
8c0988b remove go
6617c4d feat: implement authentication and protected routes
25f66e9 Implement JWT authentication and user management in Go and Python backends
2932cd9 migration setup
```

Treat existing backend structure and exception modules as current user/project work. Do not revert unrelated changes or resurrect deleted Go code. [Source: git log -5 --oneline]

### Testing Requirements

Run backend checks from `ces-ddr-platform/ces-backend/` with the UV virtualenv activated:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Prefer focused static/model tests where possible so schema validation does not require a live PostgreSQL service. If migration execution is tested against PostgreSQL, use Docker Compose postgres and never read real secrets from `.env`.

### Project Structure Notes

Expected files to create or update:

```text
ces-ddr-platform/docker-compose.yml
ces-ddr-platform/ces-backend/src/models/db/__init__.py
ces-ddr-platform/ces-backend/src/models/db/ddr.py
ces-ddr-platform/ces-backend/src/models/schemas/__init__.py
ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/__init__.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/src/repository/migrations/env.py
ces-ddr-platform/ces-backend/src/repository/migrations/versions/*_ddr_schema.py
ces-ddr-platform/ces-backend/tests/test_ddr_schema.py
```

Optional if baseline migration is missing:

```text
ces-ddr-platform/ces-backend/src/repository/migrations/versions/*_users_schema.py
```

Do not create or update frontend files for this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-07.md]
- [Source: ces-ddr-platform/ces-backend/src/models/db/user.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/database.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/base.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/migrations/env.py]
- [Source: ces-ddr-platform/docker-compose.yml]
- [Source: https://docs.sqlalchemy.org/20/intro.html]
- [Source: https://alembic.sqlalchemy.org/en/latest/changelog.html]
- [Source: https://www.postgresql.org/docs/16/pgcrypto.html]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `source .venv/bin/activate && pytest tests/test_ddr_schema.py` passed: 7 tests.
- `source .venv/bin/activate && pytest` passed: 18 tests.
- `source .venv/bin/activate && ruff check .` passed.

### Completion Notes List

- Added DDR pipeline SQLAlchemy models with epoch timestamp columns, PostgreSQL UUID defaults, JSONB extraction payload columns, foreign keys, and required indexes.
- Added class-based DDR and DDR date status validation plus create/update/response schemas for future pipeline stories.
- Added repository classes for DDR, DDR dates, processing queue entries, and pipeline runs using the existing `BaseCRUDRepository`.
- Added minimal users baseline migration and chained `002_ddr_schema` Alembic migration because no prior version files existed locally.
- Declared the `pdfs` named Docker volume; backend mount remains pending because compose has no backend service yet.
- Added focused static contract tests for models, schemas, repositories, migrations, and compose volume declaration.

### File List

- `ces-ddr-platform/docker-compose.yml`
- `ces-ddr-platform/ces-backend/run.py`
- `ces-ddr-platform/ces-backend/src/models/db/ddr.py`
- `ces-ddr-platform/ces-backend/src/models/schemas/ddr.py`
- `ces-ddr-platform/ces-backend/src/repository/crud/ddr.py`
- `ces-ddr-platform/ces-backend/src/repository/migrations/env.py`
- `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_07_0001-001_users_schema.py`
- `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_07_0002-002_ddr_schema.py`
- `ces-ddr-platform/ces-backend/tests/test_ddr_schema.py`

### Change Log

- 2026-05-07: Implemented DDR pipeline schema foundation, migrations, repository/schema contracts, compose volume, and validation tests.
