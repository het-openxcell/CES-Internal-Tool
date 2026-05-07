# Sprint Change Proposal: Adopt Project Backend Structure

**Project:** Canadian Energy Service Internal Tool  
**Date:** 2026-05-07 12:18:55 IST  
**Requested by:** Het  
**Status:** Approved for implementation  
**Change trigger:** Backend should use the project `src/` structure as the structural reference, including SQLAlchemy async database access, repository classes, session dependencies, settings manager, security modules, exception handling, and backend conventions now present in the project.

## 1. Issue Summary

Current planning and completed story artifacts still contain backend drift from earlier implementation direction. The PRD says Python-only FastAPI, but architecture, epics, and story artifacts still reference Go, dual-backend parity, duplicate migration tracks, and direct lower-level DB query patterns.

The requested correction is to make the project backend structure the reference for the project. The backend remains `ces-ddr-platform/ces-backend`, and future backend implementation should follow this structure:

- `src/config/settings/*` style settings split, adapted to this repo as `decouple + BackendBaseSettings`.
- `src/repository/database.py` style SQLAlchemy async engine/session factory.
- `src/api/dependencies/session.py` style session dependency.
- `src/repository/crud/*` style repository classes instead of loose query functions.
- `src/models/db/*` SQLAlchemy ORM models and `src/models/schemas/*` Pydantic schemas.
- `src/securities/*` JWT and password hashing organization.
- `src/utilities/exceptions/*` centralized exception strategy.
- `src/services/*` for DDR pipeline, occurrence generation, search, export, corrections, and keyword management.

Imported reference code may have comments and generic names in places. Those should not be copied blindly. Adopt the architecture pattern, naming discipline, SQLAlchemy async approach, and module boundaries, while keeping this repo's rules: no file comments, epoch timestamps, no loose functions when class/service encapsulation is appropriate, and no `os.getenv` or `os.environ.get`.

## 2. Impact Analysis

### Epic Impact

Epic 1 is affected because foundation, migration, and authentication stories define backend structure. Existing completed stories should be treated as superseded where they conflict with the project backend standard.

Epics 2-7 remain valid in product behavior. Their backend implementation guidance changes from ad hoc FastAPI modules to project-aligned service, repository, schema, and dependency modules.

No UX behavior changes. Frontend still consumes the same `/api` contract.

### Story Impact

Affected stories:

- Story 1.1 must replace current backend scaffold guidance with a project-aligned FastAPI application factory, settings manager, routers, event handlers, exception handlers, and SQLAlchemy-ready structure.
- Story 1.2 must use Alembic with SQLAlchemy ORM metadata and async SQLAlchemy URL handling. No Go SQL migration track.
- Story 1.3 must use project-aligned security modules for JWT/password hashing and SQLAlchemy-backed user repository.
- Future Epic 2-7 backend stories must use service classes plus repository classes, not standalone query modules or scattered helpers.

### Artifact Conflicts

PRD is mostly aligned because it already states Python-only. It needs a short backend implementation note that SQLAlchemy async and the project `src/` structure are the canonical backend pattern.

Architecture conflicts are substantial:

- It says no backend structure selection was required.
- It includes Go as backend technology.
- It includes Go setup commands, Go testing, Go SSE, Go JSON conventions, and dual-backend parity.
- It lists `Alembic (Go) + Alembic (Python)` instead of one SQLAlchemy/Alembic track.
- It lacks canonical service/repository/session/settings layout.

Epics conflict in Epic 1 and story acceptance criteria:

- Story 1.1 includes `go run main.go`.
- Story 1.2 compares Alembic schema to Go migration output.
- Story 1.3 says Go is canonical.
- Several future stories mention Python/Go split implementation.

Implementation story files also conflict and need cleanup before more backend work.

### Technical Impact

Adopt these backend decisions:

- Backend package remains `ces-ddr-platform/ces-backend`.
- Source layout must use `src/*`. Make all future stories consistent with that project structure.
- Use SQLAlchemy 2 async ORM and `asyncpg`.
- Use `async_sessionmaker` for request-scoped sessions.
- Use repository classes for persistence access.
- Use service classes for business logic.
- Use Pydantic schemas for request/response contracts.
- Use Alembic against SQLAlchemy model metadata as sole migration authority.
- Store all timestamps as epoch integers, not `TIMESTAMPTZ`.
- Keep config through `decouple + BackendBaseSettings`; do not import `os` for environment lookup.
- Wrap blocking sync SDK calls with `asyncio.to_thread()`.

## 3. Recommended Approach

Recommended path: Direct Adjustment.

Rationale:

- Product scope is unchanged.
- The project backend structure gives enough module boundaries to avoid inventing architecture during every story.
- SQLAlchemy async gives a consistent data layer for migrations, repositories, and future DDR domain tables.
- Direct adjustment is lower risk than rollback because current backend is still early and Epic 2+ are backlog.

Effort: Medium.

Risk: Medium if current auth/migration files are rewritten without preserving tests. Low if handled story-by-story with pytest after each backend slice.

Timeline impact: One backend foundation cleanup story before Epic 2 work. This prevents larger rework later.

Scope classification: Moderate.

## 4. Detailed Change Proposals

### Architecture: Backend Structure Decision

OLD:

```md
Full-stack web application + AI data pipeline. Pre-decided stack from PRD — no starter
template selection required.
```

NEW:

```md
Backend standard is the project `src/` structure. The CES backend remains Python-only FastAPI, with settings manager, SQLAlchemy async database/session layer, dependency-injected sessions, repository classes, service classes, SQLAlchemy ORM models, Pydantic schemas, centralized security modules, and centralized exception handling.
```

Rationale: The backend has a chosen project structure now. Architecture must guide future agents to use it.

### Architecture: Stack Summary

OLD:

```md
| Python backend | FastAPI + uvicorn | PRD locked |
| Python backend | Go + FastAPI | PRD + user confirmed |
```

NEW:

```md
| Backend | Python 3.12+ FastAPI + uvicorn | PRD locked |
| Backend structure | Project `src/` backend structure adapted to CES rules | User confirmed |
| Database layer | SQLAlchemy 2 async ORM + asyncpg | Template locked |
```

Rationale: Removes dual-backend contradiction and adds SQLAlchemy as canonical.

### Architecture: Project Structure

OLD:

```md
ces-backend/
├── app/
│   ├── api/
│   ├── pipeline/
│   ├── occurrence/
│   ├── search/
│   ├── export/
│   └── models/
```

NEW:

```md
ces-backend/
├── src/
│   ├── api/
│   │   ├── dependencies/
│   │   └── routes/
│   ├── config/
│   │   └── settings/
│   ├── models/
│   │   ├── db/
│   │   └── schemas/
│   ├── repository/
│   │   ├── crud/
│   │   └── migrations/
│   ├── securities/
│   │   ├── authorizations/
│   │   └── hashing/
│   ├── services/
│   ├── external/
│   └── utilities/
```

Rationale: Aligns future backend stories with the project structure and gives clear module ownership.

### Architecture: Migration Strategy

OLD:

```md
DB migration strategy — Alembic (Go) + Alembic (Python)
```

NEW:

```md
DB migration strategy — Alembic only, using SQLAlchemy model metadata and explicit migrations. All timestamp columns store epoch integers.
```

Rationale: One backend, one migration authority, epoch-time repo rule.

### Epic 1 Story 1.1

OLD:

```md
Given the Python backend scaffold exists
When `go run main.go` is run in `ces-backend/`
Then FastAPI server starts and `GET /health` returns `{ "status": "ok" }` with HTTP 200
And `internal/config/config.go` contains `Config` struct — all config from env vars
```

NEW:

```md
Given the backend scaffold follows the project `src/` structure
When `source .venv/bin/activate && uvicorn src.main:backend_app --reload` is run in `ces-backend/`
Then server starts and `GET /health` returns `{ "status": "ok" }` with HTTP 200
And settings use `decouple + BackendBaseSettings`
And SQLAlchemy async session dependencies are available through the API dependency layer
And no `os.getenv`, `os.environ.get`, Go files, or loose DB query functions exist in backend business logic
```

Rationale: Makes project structure adoption verifiable.

### Epic 1 Story 1.2

OLD:

```md
Then `users` table schema matches Go migration output exactly
```

NEW:

```md
Then `users` table schema matches the SQLAlchemy ORM model and Alembic revision exactly
And `created_at` and `updated_at` are epoch integer columns
```

Rationale: Removes Go baseline and enforces epoch-time rule.

### Epic 1 Story 1.3

OLD:

```md
And Go implementation is canonical; Python behavior matches exactly
```

NEW:

```md
And Python FastAPI implementation is canonical
And authentication uses project-aligned security classes/modules for JWT creation, JWT validation, password hashing, and current-user dependency
And user lookup is handled through a SQLAlchemy-backed repository class
```

Rationale: Auth belongs in security/repository layers.

### Future Backend Stories

OLD:

```md
Implement API behavior in route modules and direct query helpers as needed.
```

NEW:

```md
Each backend feature uses this flow: route dependency validates request and session, service class owns business workflow, repository class owns persistence, SQLAlchemy ORM model owns DB mapping, Pydantic schema owns request/response shape.
```

Rationale: Prevents loose functions and scattered data access.

## 5. Checklist Status

- [x] 1.1 Triggering story identified: backend foundation and upcoming Epic 2 work.
- [x] 1.2 Core problem defined: backend artifacts do not yet enforce project `src/` structure and SQLAlchemy async structure.
- [x] 1.3 Evidence gathered: imported reference contains settings, SQLAlchemy database/session, repository, schemas, security, exception modules; current planning artifacts still contain Go and dual-backend references.
- [x] 2.1 Current epic assessed: Epic 1 must be adjusted; Epic 2 can proceed after foundation cleanup.
- [x] 2.2 Epic-level changes identified: no new epic needed; add backend foundation cleanup story or revise Epic 1 stories.
- [x] 2.3 Remaining epics reviewed: Epics 2-7 keep product goals but use project-aligned backend implementation.
- [x] 2.4 No future epics invalidated.
- [x] 2.5 Priority change needed: do backend structure alignment before Epic 2.
- [x] 3.1 PRD impact reviewed: minor note needed.
- [x] 3.2 Architecture impact reviewed: substantial cleanup needed.
- [x] 3.3 UX impact reviewed: none.
- [x] 3.4 Other artifacts reviewed: implementation stories and sprint status need update after approval.
- [x] 4.1 Direct Adjustment viable: medium effort, medium risk.
- [N/A] 4.2 Rollback not needed.
- [N/A] 4.3 MVP Review not needed.
- [x] 4.4 Recommended path selected: Direct Adjustment.
- [x] 5.1 Issue summary created.
- [x] 5.2 Epic and artifact impacts documented.
- [x] 5.3 Recommended path documented.
- [x] 5.4 MVP impact defined: no scope reduction.
- [x] 5.5 Handoff plan defined.
- [x] 6.3 Explicit user approval captured on 2026-05-07.
- [x] 6.4 `sprint-status.yaml` should record approved change after approval.

## 6. Implementation Handoff

Recommended next implementation task:

Create a backend foundation cleanup story before Epic 2:

```md
Story 1.5: Backend Structure Alignment

Goal: Refactor `ces-backend` to follow the project backend architecture while preserving current health/auth behavior and tests.

Acceptance criteria:
- Backend source layout follows `src/*` project modules.
- Settings use `decouple + BackendBaseSettings`.
- SQLAlchemy async engine, sessionmaker, and request-scoped session dependency exist.
- User model is SQLAlchemy ORM-backed with epoch integer timestamps.
- User repository class replaces direct user query helper.
- Auth route uses service/repository/security classes.
- Alembic uses SQLAlchemy model metadata and remains sole migration authority.
- Tests pass with `source .venv/bin/activate && pytest`.
- Ruff is configured and passes with `source .venv/bin/activate && ruff check .`.
- New backend modules include pytest coverage for contracts, repositories, migrations, auth, and lint-relevant imports.
- No Go backend references remain in active planning artifacts.
```

Handoff recipient: Developer agent.

Responsibilities:

- Update PRD, architecture, epics, and affected story files after approval.
- Refactor backend structure in a small, tested pass.
- Preserve current API contracts unless a proposal explicitly changes them.
- Run backend pytest from activated UV virtualenv.

Success criteria:

- Future backend stories have one clear pattern.
- No dual-backend ambiguity remains.
- SQLAlchemy async data layer is ready before DDR pipeline tables are added.
- Repo rules are enforced: epoch timestamps, `decouple + BackendBaseSettings`, service/repository encapsulation, async correctness, no unnecessary comments.

Correct Course workflow state: approved; implementation cleanup started.
