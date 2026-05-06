# Story 1.1: Project Scaffold & Development Infrastructure

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As an authenticated CES user,
I want the platform infrastructure initialized and running locally,
so that development can begin on a stable, reproducible foundation.

## Acceptance Criteria

1. Given the monorepo root `ces-ddr-platform/` is created, when `docker compose up -d` is run, then PostgreSQL 16 starts healthy on port `5432`, Qdrant starts healthy on port `6333`, and `docker compose ps` shows both services as running.
2. Given the frontend scaffold exists, when `npm run dev` is run in `ces-frontend/`, then Vite starts on port `5173`, `vite.config.ts` proxies `/api/*` to the backend URL, `tailwind.config.js` contains CES tokens `--ces-red: #C41230`, `--edit-indicator: #D97706`, `--surface: #F9FAFB`, shadcn/ui components live in `src/components/ui/`, and `<html class="light">` disables dark mode at root.
3. Given the Python backend scaffold exists, when `uvicorn app.main:app --reload` is run in `ces-backend-python/`, then `GET /health` returns HTTP 200 with `{ "status": "ok" }`, and `app/config.py` uses Pydantic Settings with all config from environment variables.
4. Given the Go backend scaffold exists, when `go run main.go` is run in `ces-backend-go/`, then `GET /health` returns HTTP 200 with `{ "status": "ok" }`, and `internal/config/config.go` contains a central `Config` struct loaded from environment variables.
5. Given `.env.example` files exist in repo root, `ces-frontend/`, `ces-backend-python/`, and `ces-backend-go/`, when `.gitignore` is reviewed, then `.env` files are ignored at all levels, and `GEMINI_API_KEY`, `JWT_SECRET`, and `POSTGRES_PASSWORD` never appear in committed files.

## Tasks / Subtasks

- [x] Create monorepo scaffold under `ces-ddr-platform/` (AC: 1-5)
  - [x] Add root `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`, and optional `docker-compose.prod.yml` placeholder.
  - [x] Add top-level folders `ces-frontend/`, `ces-backend-python/`, `ces-backend-go/`, `shared/`, `nginx/`, and `.github/workflows/`.
  - [x] Keep scaffold aligned with CES internal DDR extraction/reporting scope from `AGENTS.md`.
- [x] Add local infrastructure (AC: 1)
  - [x] Define `postgres:16-alpine` service with database `ces_ddr`, user `ces`, password from `${POSTGRES_PASSWORD}`, persisted volume `postgres_data`, and local port `5432`.
  - [x] Define `qdrant/qdrant` service with persisted volume `qdrant_data` mounted to `/qdrant/storage`, REST port `6333`, and gRPC port `6334`.
  - [x] Add healthchecks so `docker compose ps` reports meaningful health/running state.
- [x] Scaffold frontend (AC: 2)
  - [x] Initialize React + Vite + TypeScript in `ces-frontend/`.
  - [x] Configure dev server port `5173` and proxy `/api/*` to an env-driven backend URL.
  - [x] Install and initialize Tailwind CSS and shadcn/ui with `src/components/ui/`.
  - [x] Add CES design tokens and set root document class to `light`.
  - [x] Add minimal `App.tsx` shell that proves the app boots without adding auth, upload, table, or dashboard logic.
- [x] Scaffold Python backend (AC: 3)
  - [x] Create `ces-backend-python/pyproject.toml`, `app/main.py`, `app/config.py`, `app/api/health.py`, `app/exceptions.py`, and `tests/api/test_health.py`.
  - [x] Use `decouple` plus `BackendBaseSettings`; do not use `os.environ.get`, `os.getenv`, or direct environment reads in business logic.
  - [x] Expose `GET /health` returning exactly `{ "status": "ok" }`.
  - [x] Ensure any future sync SDK calls are intended to run through `asyncio.to_thread()`; this story should not add SDK calls.
- [x] Scaffold Go backend (AC: 4)
  - [x] Create `ces-backend-go/go.mod`, `main.go`, `internal/config/config.go`, `internal/api/router.go`, `internal/api/health.go`, and `internal/api/health_test.go`.
  - [x] Centralize env loading in `internal/config.Config`; no scattered `os.Getenv()` outside config package.
  - [x] Expose `GET /health` returning exactly `{ "status": "ok" }`.
- [x] Add env and secret safety (AC: 5)
  - [x] Add `.env.example` at every required level with placeholder values only.
  - [x] Ignore `.env`, `.env.*`, generated build output, virtualenvs, node modules, coverage, and local DB/vector data.
  - [x] Verify no real secret values are copied from the current workspace `.env`.
- [x] Add smoke tests and validation commands (AC: 1-5)
  - [x] Frontend: run install, dev/build or equivalent scaffold verification.
  - [x] Python: activate UV virtualenv before running files/tests when applicable: `source .venv/bin/activate`.
  - [x] Python: run `pytest`.
  - [x] Go: run `go test ./...`.
  - [x] Infrastructure: run `docker compose up -d` and `docker compose ps`; cleanly document any local Docker limitation.

### Review Findings

- [x] [Review][Patch] Compose requires external Postgres password before exact AC command can work [ces-ddr-platform/docker-compose.yml:7]
- [x] [Review][Patch] Qdrant image tag is floating and weakens reproducible infrastructure [ces-ddr-platform/docker-compose.yml:19]
- [x] [Review][Patch] Tailwind config does not contain required CES token values [ces-ddr-platform/ces-frontend/tailwind.config.js:5]
- [x] [Review][Patch] shadcn/ui primitive appears handmade instead of initialized shadcn component [ces-ddr-platform/ces-frontend/src/components/ui/button.tsx:5]
- [x] [Review][Patch] Python backend allows Python 3.11 despite 3.12+ stack requirement [ces-ddr-platform/ces-backend-python/pyproject.toml:4]
- [x] [Review][Patch] Go backend local config ignores `.env` files and silently falls back [ces-ddr-platform/ces-backend-go/internal/config/config.go:27]

## Dev Notes

### Project Scope

This is a greenfield scaffold story. Do not implement authentication flows, database migrations, DDR upload, extraction, occurrence generation, correction store, export, query, or monitoring features. Create only the stable foundation later stories depend on. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]

CES product scope is internal-only: employees upload Pason DDR PDFs, extract structured data, analyze occurrences, edit/correct results, and generate reports. Do not add public/client-facing surfaces, RBAC, marketing pages, external analytics, or non-DDR product capabilities. [Source: AGENTS.md#Project Overview] [Source: _bmad-output/planning-artifacts/prd.md#Product Scope]

### Required Stack

- Frontend: React + Vite + TypeScript + Tailwind CSS + shadcn/ui. [Source: _bmad-output/planning-artifacts/architecture.md#Technical Constraints & Dependencies]
- Frontend table dependency for later stories: TanStack Table v8, but this story should only install baseline dependencies if needed for scaffold parity. [Source: _bmad-output/planning-artifacts/architecture.md#Stack Summary]
- Python backend: FastAPI + uvicorn, Python 3.12+, Pydantic v2 family settings. [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Decisions Established]
- Go backend: Go 1.22+ + Gin. [Source: _bmad-output/planning-artifacts/architecture.md#Stack Summary]
- Storage services: PostgreSQL 16 and Qdrant through Docker Compose. [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]

### File Structure Requirements

Create this structure as the target scaffold:

```text
ces-ddr-platform/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
├── nginx/
│   └── nginx.conf
├── .github/
│   └── workflows/
├── shared/
│   ├── keywords.json
│   ├── schema/
│   └── test-fixtures/
├── ces-frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/ui/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── lib/
│       └── types/
├── ces-backend-python/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── api/
│   │       └── health.py
│   └── tests/
│       └── api/
│           └── test_health.py
└── ces-backend-go/
    ├── go.mod
    ├── main.go
    ├── .env.example
    └── internal/
        ├── config/
        │   └── config.go
        └── api/
            ├── router.go
            └── health.go
```

Full future tree includes `pipeline/`, `occurrence/`, `search/`, `export/`, `corrections/`, `keywords/`, `auth/`, `models/`, and `db/`, but this story should not fill those modules with placeholder logic unless needed to keep imports/builds clean. [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]

### Backend Guardrails From AGENTS.md

- Python config must use `decouple + BackendBaseSettings`; never use `os.environ.get` or `os.getenv`.
- Keep implementation class/service oriented. Avoid loose global functions and standalone utility clutter except constants/config and framework-required route registration.
- No file comments unless absolutely necessary. Prefer self-documenting names.
- Before running Python files or tests, activate UV virtualenv with `source .venv/bin/activate` when a repo-level `.venv` is present.
- Async correctness: future sync SDK calls must be wrapped with `asyncio.to_thread()`; do not block the async event loop. This scaffold should avoid sync SDK calls entirely.

### Configuration Rules

- All config comes from environment variables. No committed config files with secrets. [Source: _bmad-output/planning-artifacts/architecture.md#Configuration]
- Root env examples should include placeholders for `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `POSTGRES_DSN`, `QDRANT_HOST`, `QDRANT_PORT`, and `JWT_SECRET`. [Source: _bmad-output/planning-artifacts/architecture.md#Environment configuration]
- Python has `app/config.py` with a settings class. Project-specific override: use `BackendBaseSettings` with `decouple` integration per `AGENTS.md`.
- Go has `internal/config/config.go` with a `Config` struct; direct `os.Getenv()` is allowed only inside that config package.
- Frontend reads API base URL from `VITE_API_URL`; `vite.config.ts` proxy should use env/default backend URL and never hardcode a production origin. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]

### API And Health Contract

- Health endpoint path is `GET /health` in both backends. [Source: _bmad-output/planning-artifacts/architecture.md#Monitoring]
- Response body must be exactly `{ "status": "ok" }` with HTTP 200 in both implementations. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- Do not add `/api/health` unless reverse proxy routing needs it later; app-level contract remains `/health`.
- Use direct success object responses. Do not wrap success responses in `{ data: ... }`. [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

### Docker Compose Requirements

- `postgres` uses `postgres:16-alpine`, persisted `postgres_data`, host port `5432`, and password from `${POSTGRES_PASSWORD}`. [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- `qdrant` uses `qdrant/qdrant`, persisted `qdrant_data` mounted to `/qdrant/storage`, host port `6333`, and optionally `6334` for gRPC. [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- PostgreSQL and Qdrant must not be designed as public production endpoints; external host port mapping is acceptable for local development only. [Source: _bmad-output/planning-artifacts/architecture.md#Network Security]

### Frontend Design Foundation

- UX is desktop-first, data-dense, internal-ops focused. Avoid marketing layout, hero screens, decorative gradients, and broad public-site language. [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design Philosophy]
- CES brand tokens must be present now because later auth and table stories depend on them: deep navy/white surfaces with CES red and amber edit indicator. [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Visual Design System]
- shadcn/ui primitives belong in `src/components/ui/` and should not be directly modified after generation. [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- This story only needs a bootable shell. Protected routing starts in Story 1.4.

### Latest Technical Information

- Vite latest stable major is Vite 8 as of the official March 12, 2026 release; it uses Rolldown as the unified bundler. If adopting Vite 8, verify plugin compatibility during scaffold. Source: https://vite.dev/blog/announcing-vite8
- Vite release guidance says supported stable versions and security support move by semver; pin exact major/minor in `package.json` rather than relying on unreviewed floating upgrades. Source: https://vite.dev/releases
- Current Tailwind docs install Tailwind for Vite through `tailwindcss` and `@tailwindcss/vite`, importing `@import "tailwindcss";`. Architecture still explicitly requires `tailwind.config.js` tokens, so preserve that acceptance criterion even if using modern Tailwind setup. Source: https://tailwindcss.com/docs/installation
- shadcn/ui Vite docs now support `shadcn@latest init -t vite` and require `@/*` path alias configuration for Vite projects. Source: https://ui.shadcn.com/docs/installation/vite
- FastAPI release notes show 0.135.1 on March 1, 2026, with built-in SSE support added in 0.135.0. SSE is later-story relevant; this scaffold only needs FastAPI app and health endpoint. Source: https://fastapi.tiangolo.com/release-notes/
- Pydantic Settings remains the correct settings mechanism for environment-driven config and works with Docker/12-factor style deployments. Source: https://docs.pydantic.dev/latest/api/pydantic_settings/
- Qdrant official quickstart exposes REST on `6333`, dashboard on `6333/dashboard`, and gRPC on `6334`; default local config has no auth, so production must keep it behind Docker network/reverse proxy controls. Source: https://qdrant.tech/documentation/quick-start/

### Testing Requirements

- Frontend: install dependencies and run the project’s scaffold verification command. If tests are not yet configured, run `npm run build` as minimum proof that Vite/TypeScript compile.
- Python: run `pytest` for `GET /health`; activate `.venv` first if present. Keep tests under `ces-backend-python/tests/`. [Source: AGENTS.md#Backend Guidelines]
- Go: run `go test ./...`; keep tests co-located with packages. [Source: _bmad-output/planning-artifacts/architecture.md#Test Location]
- Infrastructure: run `docker compose up -d`, `docker compose ps`, and confirm `postgres` and `qdrant` are running/healthy.
- Secret check: search created scaffold for `GEMINI_API_KEY=`, `JWT_SECRET=`, and real password values; only placeholder examples may exist.

### Current Repository State

- This workspace currently contains planning artifacts and sample/P.O.C. files, not an initialized application scaffold.
- No Git repository was detected, so recent commit intelligence is unavailable.
- No previous story exists for Epic 1, so there are no prior implementation learnings.
- Existing `extras/poc/` code is proof-of-concept material only. Do not copy it wholesale into production scaffold; use it later only when pipeline stories explicitly call for PDF extraction behavior.

## References

- [Source: AGENTS.md#Project Overview]
- [Source: AGENTS.md#Backend Guidelines]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System]
- [Source: _bmad-output/planning-artifacts/prd.md#Product Scope]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Red phase: Python `pytest` failed with `ModuleNotFoundError: No module named 'app'`.
- Red phase: Go `go test ./...` failed because no Go module existed.
- Green phase: added Python FastAPI health scaffold and Go Gin health scaffold.
- Frontend build initially failed on TypeScript 6 `baseUrl` deprecation and missing Vite CSS ambient types; fixed through `ignoreDeprecations` and `types`.
- Docker validation initially showed Qdrant ready by host HTTP but healthcheck stuck because `wget` was absent in the Qdrant image; replaced with Bash TCP healthcheck.
- Secret validation found a generated local `.env` containing a real Gemini key; removed it and verified no real secret remains in scaffold files.
- Final validation passed: `source .venv/bin/activate && pytest`, `GOTOOLCHAIN=local go test ./...`, `npm install && npm run build`, `npm run dev` on port `5173`, Python `/health`, Go `/health`, and `docker compose ps`.

### Completion Notes List

- Created `ces-ddr-platform/` monorepo scaffold with root docs, ignored local artifacts, placeholder environment examples, shared folders, nginx placeholder, and workflow folder placeholders.
- Added Docker Compose services for PostgreSQL 16 and Qdrant with persisted volumes, local ports, and working healthchecks.
- Added Vite 8 React TypeScript frontend with Tailwind 4, CES tokens, root light mode, `/api` proxy to `VITE_API_URL`, and minimal internal operations shell.
- Added Python FastAPI backend using `decouple` plus `BackendBaseSettings`, class-based app/router setup, and exact `GET /health` contract with pytest coverage.
- Added Go Gin backend with central config package, health router/handler, and Go unit test for exact `GET /health` contract.
- Verified no real secrets remain in scaffold files; only placeholder `.env.example` values exist.

### File List

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/1-1-project-scaffold-development-infrastructure.md`
- `ces-ddr-platform/.env.example`
- `ces-ddr-platform/.github/workflows/.gitkeep`
- `ces-ddr-platform/.gitignore`
- `ces-ddr-platform/README.md`
- `ces-ddr-platform/docker-compose.prod.yml`
- `ces-ddr-platform/docker-compose.yml`
- `ces-ddr-platform/nginx/nginx.conf`
- `ces-ddr-platform/shared/keywords.json`
- `ces-ddr-platform/shared/schema/.gitkeep`
- `ces-ddr-platform/shared/test-fixtures/.gitkeep`
- `ces-ddr-platform/ces-frontend/.env.example`
- `ces-ddr-platform/ces-frontend/index.html`
- `ces-ddr-platform/ces-frontend/package-lock.json`
- `ces-ddr-platform/ces-frontend/package.json`
- `ces-ddr-platform/ces-frontend/src/App.tsx`
- `ces-ddr-platform/ces-frontend/src/components/.gitkeep`
- `ces-ddr-platform/ces-frontend/src/components/ui/button.tsx`
- `ces-ddr-platform/ces-frontend/src/components/ui/index.ts`
- `ces-ddr-platform/ces-frontend/src/hooks/.gitkeep`
- `ces-ddr-platform/ces-frontend/src/lib/.gitkeep`
- `ces-ddr-platform/ces-frontend/src/lib/utils.ts`
- `ces-ddr-platform/ces-frontend/src/main.tsx`
- `ces-ddr-platform/ces-frontend/src/pages/.gitkeep`
- `ces-ddr-platform/ces-frontend/src/styles.css`
- `ces-ddr-platform/ces-frontend/src/types/.gitkeep`
- `ces-ddr-platform/ces-frontend/tailwind.config.js`
- `ces-ddr-platform/ces-frontend/tsconfig.json`
- `ces-ddr-platform/ces-frontend/vite.config.ts`
- `ces-ddr-platform/ces-backend-python/.env.example`
- `ces-ddr-platform/ces-backend-python/app/__init__.py`
- `ces-ddr-platform/ces-backend-python/app/api/__init__.py`
- `ces-ddr-platform/ces-backend-python/app/api/health.py`
- `ces-ddr-platform/ces-backend-python/app/config.py`
- `ces-ddr-platform/ces-backend-python/app/exceptions.py`
- `ces-ddr-platform/ces-backend-python/app/main.py`
- `ces-ddr-platform/ces-backend-python/pyproject.toml`
- `ces-ddr-platform/ces-backend-python/tests/api/test_health.py`
- `ces-ddr-platform/ces-backend-python/uv.lock`
- `ces-ddr-platform/ces-backend-go/.env.example`
- `ces-ddr-platform/ces-backend-go/go.mod`
- `ces-ddr-platform/ces-backend-go/go.sum`
- `ces-ddr-platform/ces-backend-go/internal/api/health.go`
- `ces-ddr-platform/ces-backend-go/internal/api/health_test.go`
- `ces-ddr-platform/ces-backend-go/internal/api/router.go`
- `ces-ddr-platform/ces-backend-go/internal/config/config.go`
- `ces-ddr-platform/ces-backend-go/main.go`

## Change Log

- 2026-05-06: Implemented Story 1.1 project scaffold and development infrastructure; status moved to review.
