---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
lastStep: 8
status: 'complete'
completedAt: '2026-05-06'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/product-brief-Canadian Energy Service Internal Tool.md'
  - '_bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md'
workflowType: 'architecture'
project_name: 'Canadian Energy Service Internal Tool'
user_name: 'Het'
date: '2026-05-06'
---

# Architecture Decision Document — CES DDR Intelligence Platform

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Current Backend Standard

The backend standard from 2026-05-07 forward is Python FastAPI using the project `src/` structure, `decouple + BackendBaseSettings`, async SQLAlchemy repositories, Alembic under `src/repository/migrations`, `pytest`, and `ruff`. This supersedes older dual-backend or root `app/` references in historical notes.

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

35 FRs across 7 categories:
- **Document Ingestion & Processing (FR1–FR5):** PDF upload, date-boundary detection, per-date AI extraction, Pydantic schema validation, real-time processing status
- **Occurrence Generation (FR6–FR11):** Occurrence table from validated data, keyword-engine type classification (~250 keywords → 15–17 types), mMD inference (problem-line first, backward scan fallback), density nearest-timestamp join, dedup by (type, mMD), filterable occurrence view
- **Inline Editing & Correction Store (FR12–FR16):** Any-field inline edit before export, structured reason capture (field/original/corrected/user/timestamp/source), persistent correction store, summarized correction context injection on future runs, correction store review dashboard
- **Data Export (FR17–FR20):** Per-report .xlsx (occurrences + optional edit history sheet), master occurrences_all.xlsx, filtered export, time log CSV export
- **Query & History (FR21–FR25):** NL query (BM25 + Qdrant vector), cross-DDR filter (well/area/operator/type/date), time log + deviation survey + bit record views
- **Pipeline Operations & Monitoring (FR26–FR31):** Processing queue, per-date status (success/warning/failed), error log with raw AI response + Pydantic errors, per-date re-run with manual date override, failed-date flag (no silent omission), AI cost tracking
- **System Config & Access (FR32–FR35):** Runtime keyword-type mapping management (no redeploy), raw AI response + validated JSON retention (no TTL), auth on all routes, single role (all authenticated users = full access)

**Non-Functional Requirements:**

| Category | Key Drivers |
|---|---|
| Performance | NL query < 3s; DDR processing < 90s sequential / < 30s parallel; occurrence table render < 500ms; page load < 2s; upload ack < 1s; Excel export < 30s |
| Security | No unauthenticated routes; API key never in logs/code; passwords hashed; no outbound except Gemini + Qdrant |
| Reliability | Per-date failure isolation; no silent occurrence drops; raw response retention (no TTL); processing queue durable across restarts |
| Integration | Gemini 429 → exponential backoff + warning; Qdrant unavailable → BM25 fallback; PostgreSQL writes transactional; Excel compatible with Excel 2016+ and LibreOffice |

**Scale & Complexity:**

- **Complexity level:** High
- **Primary domain:** Full-stack web + AI data pipeline + search
- **Daily data volume:** 10–15 DDRs/day × ~30 dates = 300–450 Gemini API calls/day; ~500 status records/day; all raw responses retained indefinitely
- **Estimated architectural components:** Frontend SPA, Backend API, PDF Pre-splitter, AI Extraction Pipeline, Occurrence Engine, Correction Store, BM25 Search, Qdrant Vector Search, Processing Queue, Excel Export Layer, Keyword Management, PostgreSQL, Auth Layer

### Technical Constraints & Dependencies

- **Locked frontend stack:** React + Vite + Tailwind CSS + shadcn/ui + TanStack Table
- **Locked AI stack:** Gemini 2.5 Flash-Lite + pdfplumber + pypdf + Pydantic v2 + google-genai SDK
- **Locked storage:** PostgreSQL (JSONB for raw responses); Qdrant for vector search
- **Backend constraint:** Python-only FastAPI backend. No second backend and no root backend coordination layer.
- **PDF format:** Pason native-text DDR format (CAOEC tour sheet standard); non-standard contractor layouts must degrade gracefully with manual override
- **Auth:** Static credentials for V1 — no OAuth/SSO, no session refresh complexity
- **No external data at runtime:** Only Gemini API + Qdrant (self-hosted or Qdrant Cloud); no third-party analytics or CDN calls
- **Desktop-first, 1280px minimum:** TanStack Table with horizontal scroll on overflow; no mobile breakpoints required for V1

### Cross-Cutting Concerns Identified

1. **Authentication** — every route and API endpoint must reject unauthenticated requests; applies to frontend routing + every backend endpoint in Python
2. **Error logging and audit trail** — raw Gemini responses + Pydantic errors + validated JSON retained per date chunk with no TTL; applies throughout the extraction pipeline
3. **Async processing state** — PDF upload triggers background pipeline; processing queue must be DB-backed (durable across restarts); frontend reflects state via polling or SSE
4. **Python backend test coverage** — every feature, API endpoint, data schema, and integration path must be covered by Python tests
5. **Extraction failure isolation** — failure of one date chunk must not abort other dates; failed chunks flagged visibly, never silently omitted from counts or exports
6. **API key security** — Gemini API key must never appear in logs, error messages, or source code; enforced at every logging and error-handling layer in the Python backend
7. **Correction context injection** — summarized correction store injected into future occurrence generation prompts; must be capped to avoid prompt bloat
8. **Excel compatibility** — exports must work in Excel 2016+ and LibreOffice Calc through the Python `openpyxl` implementation

## Backend Structure Decision

### Primary Technology Domain

Full-stack web application + AI data pipeline. Backend implementation uses the project `src/` structure as the canonical structure, adapted to CES rules.

### Stack Summary (All Decisions Locked)

| Layer | Technology | Decision Source |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS | PRD locked |
| UI components | shadcn/ui (Radix UI primitives) | UX spec locked |
| Data table | TanStack Table v8 | UX spec locked |
| Backend | Python 3.12+ FastAPI + uvicorn | PRD locked |
| Backend structure | Project `src/` backend structure adapted to CES rules | User confirmed |
| Database layer | SQLAlchemy 2 async ORM + asyncpg | Project standard |
| AI extraction | google-genai SDK + Gemini 2.5 Flash-Lite | Research locked |
| PDF processing | pdfplumber + pypdf | Research locked |
| Schema validation | Pydantic v2 | Research locked |
| Primary DB | PostgreSQL (JSONB) | PRD locked |
| Vector search | Qdrant (Docker self-hosted) | PRD + user confirmed |
| Excel export | openpyxl | PRD locked |
| Auth | JWT + static credentials V1 | PRD locked |
| Backend quality gate | pytest + Ruff | User confirmed |

### Initialization Commands

**Frontend:**
```bash
npm create vite@latest ces-frontend -- --template react-ts
cd ces-frontend
npm install
npx tailwindcss init -p
npx shadcn-ui@latest init
npm install @tanstack/react-table
npm install sonner
npm install lucide-react
```

**Backend:**
```bash
mkdir ces-backend && cd ces-backend
uv sync
source .venv/bin/activate
ruff check src tests
pytest
uvicorn src.main:backend_app --reload
```

**Core backend dependencies:**
```bash
pip install fastapi uvicorn[standard] pydantic-settings sqlalchemy asyncpg
pip install "google-genai[aiohttp]" pdfplumber pypdf openpyxl
pip install qdrant-client rank-bm25
pip install python-jose[cryptography] passlib[bcrypt]
```

**Infrastructure (Docker Compose):**
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ces_ddr
      POSTGRES_USER: ces
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"

volumes:
  postgres_data:
  qdrant_data:
```

### Recommended Project Structure

```
ces-ddr-platform/
├── ces-frontend/
│   ├── src/
│   │   ├── components/ui/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
├── ces-backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── dependencies/
│   │   │   └── routes/
│   │   ├── config/
│   │   │   └── settings/
│   │   ├── models/
│   │   │   ├── db/
│   │   │   └── schemas/
│   │   ├── repository/
│   │   │   ├── crud/
│   │   │   └── migrations/
│   │   ├── securities/
│   │   ├── services/
│   │   ├── external/
│   │   └── utilities/
│   ├── tests/
│   └── pyproject.toml
└── docker-compose.yml
```

### Architectural Decisions Established

**Language & Runtime:**
TypeScript strict mode on frontend. Python 3.12+ on backend. Python FastAPI backend is canonical.

**Styling Solution:**
Tailwind CSS v3 + shadcn/ui. CES design tokens in `tailwind.config.js`:
`--ces-red: #C41230`, `--edit-indicator: #D97706`, `--surface: #F9FAFB`.
Dark mode disabled at root (`<html class="light">`).

**Build Tooling:**
Vite for frontend. uvicorn for backend dev server. `uv sync` manages backend dependencies.

**Testing Framework:**
Vitest + React Testing Library for frontend. pytest + Ruff for backend. Backend work is not complete until `ruff check src tests` and `pytest` pass.

**Code Organization:**
Frontend: feature-based component folders.
Backend: project `src/` structure. Route dependencies validate request/session, service classes own business workflows, repository classes own persistence, SQLAlchemy ORM models own database mapping, and Pydantic schemas own request/response shapes.

**Development Experience:**
Docker Compose brings up PostgreSQL + Qdrant locally.
Frontend proxies API calls via Vite `server.proxy` — no CORS issues in dev.
`GEMINI_API_KEY` in `.env` (gitignored).

**Note:** Project initialization using these commands is the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- DB migration strategy — Alembic only, stored under `src/repository/migrations`
- Processing status transport — SSE
- API error format — standardized shape
- Frontend routing — React Router v6
- Deployment target — AWS VPS, Docker Compose in production

**Deferred Decisions (Post-MVP):**
- API versioning — no `/v1/` prefix in V1; add when breaking changes occur
- Caching layer — no caching for V1; PostgreSQL query performance sufficient at current scale
- CDN / static asset hosting — internal tool, direct Vite build served by Nginx or Caddy
- Log aggregation (CloudWatch, Loki) — structured JSON logs written now; aggregation wired post-launch

---

### Data Architecture

**Primary Database:** PostgreSQL 16 (JSONB for raw Gemini responses + validated JSON)

**Schema Design Principles:**
- Raw extraction results stored as JSONB (`raw_response`, `final_json`, `error_log` columns) — no schema migrations required when DDR schema evolves
- Structured relational tables for: users, ddrs, ddr_dates, occurrences, corrections, keywords, processing_queue
- JSONB indexed on `final_json->>'well_name'`, `final_json->>'date'` for dashboard queries
- No TTL on raw responses — audit trail requirement

**Migration Strategy:**
- Alembic is the sole migration authority.
- Migration files live under `ces-backend/src/repository/migrations/`.
- Developers create migration files manually when schema changes are needed.
- SQLAlchemy ORM models under `src/models/db/` define runtime mappings.
- All timestamp fields use epoch integer columns.

**Vector Storage:** Qdrant (Docker self-hosted)
- Collection: `ddr_time_logs` — embeddings of time log `details` text
- Metadata stored per vector: `ddr_id`, `date`, `time_from`, `time_to`, `code`
- Graceful degradation: if Qdrant unavailable, NL query falls back to Python BM25 (`rank-bm25`)

**Keyword Store:** `ces-backend/src/resources/keywords.json` or equivalent backend resource module — single source of truth read by the Python backend at startup; reload without redeploy via API endpoint (FR32)

---

### Authentication & Security

**Method:** JWT (HS256) + static credentials stored in DB (bcrypt-hashed passwords)
- Login: POST `/api/auth/login` → returns `{ token, expires_at }`
- Token expiry: 8 hours (working day; no silent session extension)
- No refresh tokens for V1 — re-login on expiry
- All protected routes except `/api/auth/login` require `Authorization: Bearer <token>` header
- Frontend stores token in `localStorage` (internal tool; acceptable for V1)

**Python:** `python-jose[cryptography]` + bcrypt/passlib-compatible password hashing

**API Key Security:**
- `GEMINI_API_KEY` loaded from environment variable only
- Never logged — all logging middleware must scrub `Authorization` headers and env vars
- Backend structured log sanitization applied at middleware layer before any log write

**Network Security:**
- No public endpoints except through intended entry point (Nginx/Caddy reverse proxy)
- Outbound: Gemini API + Qdrant only — no other egress at application layer
- PostgreSQL and Qdrant not exposed outside Docker network

---

### API & Communication Patterns

**Style:** REST, JSON throughout. No GraphQL.

**URL conventions:**
```
POST   /api/auth/login
GET    /ddrs
POST   /ddrs/upload
GET    /ddrs/:id
GET    /ddrs/:id/dates
POST   /ddrs/:id/dates/:date/rerun
GET    /ddrs/:id/occurrences
PATCH  /occurrences/:id
GET    /occurrences
POST   /occurrences/query
GET    /corrections
GET    /keywords
PUT    /keywords
GET    /pipeline/queue
GET    /pipeline/cost
GET    /wells/:id/timelogs
GET    /wells/:id/deviations
GET    /wells/:id/bits
GET    /export/ddr/:id
GET    /export/master
GET    /export/timelogs/:well_id
```

**Processing Status Transport: SSE**
- Endpoint: `GET /ddrs/:id/status/stream` — SSE stream per DDR
- Events: `{ event: "date_complete", data: { date, status, occurrences_count } }`
- Events: `{ event: "date_failed", data: { date, error, raw_response_id } }`
- Events: `{ event: "processing_complete", data: { total_dates, failed_dates, total_occurrences } }`
- Frontend: `EventSource` API, falls back to polling if SSE connection drops
- Python: `fastapi.responses.StreamingResponse` with `text/event-stream`

**Standard Error Response (the Python backend, identical):**
```json
{
  "error": "Human-readable message",
  "code": "SNAKE_CASE_ERROR_CODE",
  "details": {}
}
```

**Standard error codes:**
```
UNAUTHORIZED          — missing or invalid JWT
VALIDATION_ERROR      — request body failed validation
NOT_FOUND             — resource does not exist
EXTRACTION_FAILED     — Gemini API call failed for a date
RATE_LIMITED          — Gemini 429 received
EXPORT_FAILED         — Excel/CSV generation error
KEYWORD_UPDATE_FAILED — keyword store write error
```

**Gemini 429 handling:** exponential backoff (1s → 2s → 4s → 8s), max 3 retries, then mark date as `warning` with code `RATE_LIMITED`

**API Documentation:** OpenAPI spec auto-generated
- Python: FastAPI generates `/docs` + `/openapi.json` automatically
- `pytest` contract tests validate documented response shapes

---

### Frontend Architecture

**Routing:** React Router v6
- Routes: `/login`, `/`, `/reports/:id`, `/history`, `/query`, `/monitor`, `/settings/keywords`
- Auth guard: `<ProtectedRoute>` wrapper — redirects to `/login` if no valid token in localStorage
- URL state: filter params persisted in URL query string (shareable, back-navigable)

**State Management:** React `useState` + `useEffect` — no external state library for V1
- Server state: custom hooks (`useOccurrences`, `useProcessingStatus`, `useCorrections`)
- Processing status: `EventSource` in `useProcessingStatus` hook with polling fallback
- Correction store: optimistic update on cell edit → confirm on API response

**Component Architecture:**
- `src/components/ui/` — shadcn/ui primitives (never modified directly)
- `src/components/` — custom domain components (`OccurrenceTable`, `ReasonCaptureModal`, etc.)
- `src/pages/` — route-level components that compose domain components
- `src/hooks/` — data-fetching and state hooks
- `src/lib/api.ts` — typed API client (fetch wrapper with auth header injection)

**Performance:**
- TanStack Table: virtual rows not required at ≤100 occurrence rows; enable if > 500 rows observed
- Code splitting: React Router lazy imports on route level
- Vite build: default chunking sufficient for V1

---

### Infrastructure & Deployment

**Target:** Single AWS EC2 instance (t3.medium or t3.large), Docker Compose in production

**Docker Compose production stack:**
```
nginx (reverse proxy + SSL termination)
ces-frontend (Vite build served by Nginx static)
ces-backend (Python FastAPI)
postgres:16-alpine
qdrant:latest
```

**Deployment approach:**
- Single `docker-compose.prod.yml` — all services on one host
- Nginx handles SSL (Let's Encrypt), proxies `/api/*` to Python backend, serves frontend static build
- One backend container is maintained forward

**Environment configuration:**
```
GEMINI_API_KEY=
POSTGRES_PASSWORD=
POSTGRES_DSN=postgresql://ces:${POSTGRES_PASSWORD}@postgres:5432/ces_ddr
QDRANT_HOST=qdrant
QDRANT_PORT=6333
JWT_SECRET=
```
`.env` file on host, mounted into containers. Never committed to git.

**Logging:**
- Structured JSON logs (the Python backend) — `{ timestamp, level, service, request_id, message, ... }`
- `request_id` generated per request, threaded through all log lines for that request
- Gemini API key scrubbed from all log output at middleware layer
- Logs written to stdout → Docker captures → `docker logs` or future CloudWatch agent

**Monitoring (V1 minimal):**
- AI cost tracked in `pipeline_runs` table: `gemini_input_tokens`, `gemini_output_tokens`, `cost_usd` per date chunk
- Weekly cost summary aggregated from DB — no external monitoring service for V1
- Application health: `GET /health` endpoint on the Python backend → Docker healthcheck

**Backups:**
- PostgreSQL: `pg_dump` cron on host → S3 bucket (nightly)
- Qdrant: Qdrant snapshot API → S3 (nightly)

---

### Decision Impact Analysis

**Implementation Sequence (order matters):**
1. Docker Compose (Postgres + Qdrant) — everything else depends on this
2. DB schema + migrations (Alembic / Alembic) — before any backend code
3. Auth endpoints + JWT middleware — gates all other endpoints
4. PDF pre-splitter + Gemini extraction pipeline — core value
5. Occurrence engine (keyword classification, mMD, density, dedup)
6. SSE processing status stream — unblocks frontend integration
7. Correction store (CRUD + context injection)
8. Excel export layer
9. BM25 search → Qdrant vector search (Qdrant can be deferred)
10. Frontend routing + occurrence table + inline edit
11. NL query interface
12. Pipeline monitor dashboard

**Cross-Component Dependencies:**
- SSE stream requires DDR processing pipeline complete first
- Correction context injection requires both correction store and Gemini extraction pipeline
- NL query (Qdrant) requires time log data stored in PostgreSQL first (embedding happens post-extraction)
- Excel export requires correction store (edit history sheet)
- Keyword management (FR32) must reload the Python backend without restart — file watch or DB-backed store

## Implementation Patterns & Consistency Rules

**Critical consistency areas:** areas where Python backend, frontend, database, and tests must stay aligned.

---

### Naming Patterns

**Database Naming (PostgreSQL):**
- Tables: `snake_case`, plural — `ddrs`, `ddr_dates`, `occurrences`, `corrections`, `keywords`, `processing_queue`, `pipeline_runs`, `users`
- Columns: `snake_case` — `well_name`, `tour_serial`, `raw_response`, `final_json`, `error_log`
- Primary keys: UUID v4, column named `id` on every table
- Foreign keys: `{table_singular}_id` — `ddr_id`, `user_id`, `occurrence_id`
- Timestamps: `created_at`, `updated_at` (timestamptz, NOT NULL) on every table
- Boolean columns: `is_` prefix — `is_failed`, `is_exported`, `is_active`
- Indexes: `idx_{table}_{column}` — `idx_occurrences_ddr_id`, `idx_ddr_dates_ddr_id`

**API Naming:**
- Endpoints: plural nouns, lowercase, hyphens for multi-word — `/ddrs`, `/ddr-dates`, `/occurrences`
- Route params: FastAPI path params use `{id}` and produce the documented URL shape
- Query params: `snake_case` — `?well_name=`, `?date_from=`, `?occurrence_type=`
- Request headers: standard casing — `Authorization`, `Content-Type`

**JSON Field Naming (API request/response bodies — the Python backend):**
- All fields: `snake_case` — `ddr_id`, `well_name`, `tour_serial`, `raw_response`
- Python: Pydantic model fields defined in `snake_case` (default serialization)
- Dates: ISO 8601 string — `"2024-10-31"` for DDR dates, `"2024-10-31T14:30:00Z"` for timestamps
- Times (HH:MM from DDR): string, preserved exactly as extracted — `"14:30"`
- Depth values (mMD): `float` — `1452.5`, never string
- Nullable fields: explicit `null` in JSON — never omit optional fields from response

**Code Naming:**
- Frontend components: `PascalCase` files and exports — `OccurrenceTable.tsx`, `ReasonCaptureModal.tsx`
- Frontend hooks: `camelCase` with `use` prefix — `useOccurrences.ts`, `useProcessingStatus.ts`
- Frontend pages: `PascalCase` — `ReportsPage.tsx`, `MonitorPage.tsx`
- Frontend API client functions: `camelCase` verbs — `fetchOccurrences`, `patchOccurrence`, `uploadDDR`
- Python: functions/variables = `snake_case`, classes = `PascalCase`, modules = `snake_case`

---

### Structure Patterns

**Test Location:**
- Frontend: co-located `*.test.tsx` files next to component — `OccurrenceTable.test.tsx`
- Python: `tests/` directory at backend root, covering `src/` behavior — `tests/test_auth_contract.py`
- Shared test coverage fixtures: `ces-backend/tests/fixtures/` — the Python backend must reference same files

**Backend Package/Module Organization:**
```
src/api/              — routes and dependencies
src/services/         — pipeline, occurrence, search, export, corrections, keywords workflows
src/repository/crud/  — SQLAlchemy repository classes
src/models/db/        — SQLAlchemy ORM mappings
src/models/schemas/   — Pydantic request/response schemas
src/securities/       — JWT and password logic
```

**Configuration:**
- All config from environment variables — no config files in codebase
- Config loaded through `decouple + BackendBaseSettings`; never `os.getenv`, `os.environ.get`, or scattered env reads
- Backend settings live under `src/config/settings/`

---

### Format Patterns

**API Response Format:**

Success — direct object or array, no wrapper:
```json
{ "id": "uuid", "well_name": "Pembina 14-25", ... }
```
```json
[{ "id": "uuid", ... }, { "id": "uuid", ... }]
```

Success with pagination (occurrence history, corrections list):
```json
{ "items": [...], "total": 47, "page": 1, "page_size": 50 }
```

Error (defined in step 4):
```json
{ "error": "string", "code": "SNAKE_CASE_CODE", "details": {} }
```

**HTTP Status Codes (standardized):**
```
200 — success (GET, PATCH)
201 — created (POST upload, POST correction)
400 — validation error (VALIDATION_ERROR)
401 — unauthenticated (UNAUTHORIZED)
404 — not found (NOT_FOUND)
429 — Gemini rate limit surfaced to client (RATE_LIMITED)
500 — internal error (unexpected failures only)
```
- Never return 200 with an error body
- Never return 500 for expected failure modes (extraction failure = 200 with status field)

**Processing/Date Status Values (exact strings — the Python backend):**
```
DDR status:       "queued" | "processing" | "complete" | "failed"
Per-date status:  "success" | "warning" | "failed"
```

**SSE Event Names (exact strings — the Python backend):**
```
"date_complete"        — one date chunk finished successfully
"date_failed"          — one date chunk failed
"processing_complete"  — all dates finished
```

---

### Communication Patterns

**SSE Payload Structure (the Python backend identical):**
```json
// date_complete
{ "date": "20241031", "status": "success", "occurrences_count": 3 }

// date_failed
{ "date": "20241031", "error": "Tour Sheet Serial not detected", "raw_response_id": "uuid" }

// processing_complete
{ "total_dates": 30, "failed_dates": 2, "warning_dates": 1, "total_occurrences": 47 }
```

**Frontend API Client Pattern:**
- All API calls go through `src/lib/api.ts` — never raw `fetch()` in components or hooks
- Auth header injected by client automatically from localStorage token
- 401 response → clear token + redirect to `/login` (client-level interceptor)
- API base URL from `VITE_API_URL` env var — never hardcoded

**Keyword Reload Pattern:**
- Backend loads `ces-backend/src/resources/keywords.json` or equivalent resource module into memory at startup
- `PUT /keywords` writes new content to file + triggers in-memory reload
- Python: reload on each request from file — same approach

---

### Process Patterns

**Error Handling:**
- Pipeline errors: caught at stage boundary, logged with `request_id` + raw Gemini response, stored in DB, never crash the process
- API handler errors: translate to standard error response + HTTP status — no raw error strings to client
- Gemini API errors: retry with backoff at pipeline layer; if exhausted, mark date `failed` with `RATE_LIMITED` or `EXTRACTION_FAILED`
- Python: domain exceptions in `src/utilities/exceptions/` or service-specific exceptions — `ExtractionError`, `ValidationError`, `RateLimitError`
- Frontend: component-level `error` state (`string | null`); inline error display adjacent to failed component

**Loading State Pattern (Frontend):**
```typescript
// Standard hook return shape
const { data, isLoading, error } = useOccurrences(ddrId)
// isLoading: boolean — not status === 'loading'
// error: string | null — human-readable message
// data: T | null
```

**Async Pattern (Python — all routes async):**
```python
# All route handlers: async def
# All DB calls: await
# Gemini calls: await client.aio.models.generate_content()
# Never mix sync and async in route handlers
```

**Logging Pattern (the Python backend):**
```json
{ "timestamp": "ISO8601", "level": "info|warn|error", "service": "ces-backend",
  "request_id": "uuid", "message": "...", "ddr_id": "uuid", "date": "20241031" }
```
- `request_id` generated at request entry and threaded through backend request state/log context
- Log levels: `info` = normal flow; `warn` = degraded but handled; `error` = requires investigation
- Never log: `GEMINI_API_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD`, `Authorization` header value

**Correction Context Injection Cap:**
- Max corrections injected per Gemini prompt: last 20 corrections, summarized — never full history
- Summary format: `"Field '{field}': '{original}' corrected to '{corrected}' ({count} times). Reason: {most_recent_reason}"`
- Backend must apply this cap and summary format

---

### Enforcement Guidelines

**All AI Agents MUST:**
- Use `snake_case` for all JSON field names
- Use UUID v4 for all primary keys — never serial/autoincrement integers
- Return the standard error shape `{ error, code, details }` for all non-2xx responses
- Use exact status strings: `queued/processing/complete/failed` (DDR), `success/warning/failed` (date)
- Thread `request_id` through all log lines for a given request
- Never log API keys, JWT secrets, or Authorization header values
- Load all config from environment variables via the central config struct
- All Python route handlers: `async def`
- Route all frontend API calls through `src/lib/api.ts`

**Anti-Patterns to Reject:**
```go
// ❌ bare error return
return nil, err
// ✅ wrapped error
return nil, fmt.Errorf("pipeline.ProcessDate: %w", err)

// ❌ inline env access
key := os.Getenv("GEMINI_API_KEY")
// ✅ config struct
key := cfg.GeminiAPIKey
```
```python
# ❌ sync route
def get_occurrences(): ...
# ✅ async route
async def get_occurrences(): ...

# ❌ non-standard error
return {"message": "something went wrong"}
# ✅ standard error shape via HTTPException
raise HTTPException(status_code=500, detail={"error": "...", "code": "...", "details": {}})
```
```typescript
// ❌ raw fetch in component
const res = await fetch('/api/occurrences', { headers: { Authorization: `Bearer ${token}` } })
// ✅ API client
const occurrences = await api.fetchOccurrences(ddrId)
```

**Python-only canonical rule:** the FastAPI backend, Alembic migrations, Pydantic schemas, and pytest suite are the source of truth.

## Project Structure & Boundaries

### Requirements to Structure Mapping

| FR Category | Location (the Python backend mirror this structure) |
|---|---|
| FR1–FR5 Document Ingestion & Processing | `pipeline/` — pre_split, extract, validate, store |
| FR6–FR11 Occurrence Generation | `occurrence/` — classify, infer_mmd, density_join, dedup |
| FR12–FR16 Inline Editing & Correction Store | `corrections/` — store, context_builder; `PATCH /occurrences/:id` |
| FR17–FR20 Data Export | `export/` — excel_report, excel_master, csv_timelogs |
| FR21–FR25 Query & History | `search/` — bm25, qdrant, query_handler; DB well queries |
| FR26–FR31 Pipeline Operations & Monitoring | `api/pipeline` — queue, cost; SSE stream endpoint |
| FR32–FR35 System Config & Access | `keywords/` + `auth/` + DB raw response retention |

---

### Complete Project Directory Structure

```
ces-ddr-platform/
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
│
├── nginx/
│   └── nginx.conf
│
├── .github/
│   └── workflows/
│       ├── test coverage-check.yml
│       └── frontend-test.yml
│
├── ces-backend/
│   ├── src/resources/
│   │   ├── keywords.json
│   │   └── ddr_schema.json
│   └── tests/fixtures/
│       ├── expected_occurrences.json
│       ├── expected_timelogs.json
│       └── sample_extraction_output.json
│
├── ces-frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.example
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── components/
│       │   ├── ui/                          # shadcn/ui (never modified directly)
│       │   │   ├── button.tsx
│       │   │   ├── dialog.tsx
│       │   │   ├── badge.tsx
│       │   │   ├── input.tsx
│       │   │   ├── toast.tsx
│       │   │   └── ...
│       │   │
│       │   ├── OccurrenceTable.tsx          # FR11 — TanStack Table, inline edit, edit dots
│       │   ├── OccurrenceTable.test.tsx
│       │   ├── ReasonCaptureModal.tsx       # FR13 — row-anchored, auto-focus, Enter submit
│       │   ├── ReasonCaptureModal.test.tsx
│       │   ├── TypeBadge.tsx                # FR7 — TYPE_COLOURS map
│       │   ├── SectionBadge.tsx             # FR6 — Surface/Int./Main colors
│       │   ├── FailedDateRow.tsx            # FR30 — red bg + inline error + re-run button
│       │   ├── ProcessingQueueRow.tsx       # FR26 — status dot + date counts + progress
│       │   ├── DateStatusIndicator.tsx      # FR27 — per-date success/warning/failed pill
│       │   ├── NLQueryBar.tsx               # FR21 — search input + example chips
│       │   ├── CollapsibleSidebar.tsx       # UX — 220px ↔ 48px, localStorage persist
│       │   ├── MetricCard.tsx               # FR31 — dashboard stat card
│       │   └── ProtectedRoute.tsx           # FR34 — auth guard wrapper
│       │
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── ReportsPage.tsx              # FR1/FR5 — upload + report list
│       │   ├── ReportDetailPage.tsx         # FR5/FR11/FR17 — occurrence table + export
│       │   ├── HistoryPage.tsx              # FR22 — cross-DDR filter
│       │   ├── QueryPage.tsx                # FR21 — NL query interface
│       │   ├── MonitorPage.tsx              # FR26/FR31 — pipeline queue + cost
│       │   └── KeywordsPage.tsx             # FR32 — keyword editor
│       │
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useDDRs.ts
│       │   ├── useOccurrences.ts
│       │   ├── useProcessingStatus.ts       # SSE EventSource + polling fallback
│       │   ├── useCorrections.ts
│       │   └── useKeywords.ts
│       │
│       ├── lib/
│       │   ├── api.ts                       # typed fetch client, auth header, 401 redirect
│       │   ├── auth.ts                      # localStorage token helpers
│       │   └── utils.ts
│       │
│       └── types/
│           └── api.ts
│
├── ces-backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── .env.example
│   ├── alembic.ini
│   │
│   ├── src/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── config/
│   │   ├── models/
│   │   ├── repository/
│   │   │   ├── crud/
│   │   │   └── migrations/
│   │   ├── securities/
│   │   ├── services/
│   │   ├── external/
│   │   └── utilities/
│   │   │   ├── pipeline.py                  # queue, cost, SSE stream
│   │   │   ├── search.py
│   │   │   ├── export.py
│   │   │   ├── wells.py
│   │   │   └── health.py
│   │   │
│   │   ├── pipeline/
│   │   │   ├── pre_split.py                 # pdfplumber + pypdf
│   │   │   ├── extract.py                   # google-genai Gemini call
│   │   │   ├── validate.py                  # Pydantic DDRReport
│   │   │   └── store.py
│   │   │
│   │   ├── occurrence/
│   │   │   ├── classify.py
│   │   │   ├── infer_mmd.py
│   │   │   ├── density_join.py
│   │   │   └── dedup.py
│   │   │
│   │   ├── search/
│   │   │   ├── bm25.py
│   │   │   ├── qdrant.py
│   │   │   └── query_handler.py
│   │   │
│   │   ├── export/
│   │   │   ├── excel_report.py              # openpyxl
│   │   │   ├── excel_master.py
│   │   │   └── csv_timelogs.py
│   │   │
│   │   ├── corrections/
│   │   │   ├── store.py
│   │   │   └── context_builder.py           # last 20 corrections summary
│   │   │
│   │   ├── keywords/
│   │   │   ├── loader.py
│   │   │   └── updater.py
│   │   │
│   │   ├── auth/
│   │   │   ├── jwt.py
│   │   │   ├── middleware.py
│   │   │   └── password.py
│   │   │
│   │   ├── models/
│   │   │   ├── ddr.py
│   │   │   ├── occurrence.py
│   │   │   ├── correction.py
│   │   │   ├── keyword.py
│   │   │   └── user.py
│   │   │
│   │   └── db/
│   │       ├── pool.py                      # asyncpg connection pool
│   │       └── queries/
│   │           ├── ddrs.py
│   │           ├── occurrences.py
│   │           └── corrections.py
│   │
│   └── tests/
│       ├── pipeline/
│       │   ├── test_pre_split.py
│       │   ├── test_extract.py
│       │   └── test_validate.py
│       ├── occurrence/
│       │   ├── test_classify.py
│       │   ├── test_infer_mmd.py
│       │   ├── test_density_join.py
│       │   └── test_dedup.py
│       ├── search/
│       │   └── test_bm25.py
│       ├── export/
│       │   └── test_excel_report.py
│       ├── corrections/
│       │   └── test_context_builder.py
│       └── api/
│           ├── test_auth.py
│           └── test_occurrences.py
│
└── ces-backend/
    ├── go.mod
    ├── go.sum
    ├── main.go
    ├── Dockerfile
    ├── .env.example
    │
    ├── migrations/
    │   ├── 001_initial_schema.up.sql
    │   ├── 001_initial_schema.down.sql
    │   ├── 002_add_corrections.up.sql
    │   └── 002_add_corrections.down.sql
    │
    └── internal/
        ├── config/
        │   └── config.go
        │
        ├── api/
        │   ├── router.go
        │   ├── auth.go
        │   ├── ddrs.go
        │   ├── occurrences.go
        │   ├── corrections.go
        │   ├── keywords.go
        │   ├── pipeline.go                  # queue, cost, SSE stream
        │   ├── search.go
        │   ├── export.go
        │   ├── wells.go
        │   └── health.go
        │
        ├── pipeline/
        │   ├── pre_split.go + _test.go
        │   ├── extract.go + _test.go        # generative-ai-go Gemini call
        │   ├── validate.go + _test.go
        │   └── store.go + _test.go
        │
        ├── occurrence/
        │   ├── classify.go + _test.go
        │   ├── infer_mmd.go + _test.go
        │   ├── density_join.go + _test.go
        │   └── dedup.go + _test.go
        │
        ├── search/
        │   ├── bm25.go + _test.go
        │   ├── qdrant.go + _test.go
        │   └── query_handler.go + _test.go
        │
        ├── export/
        │   ├── excel_report.go + _test.go   # openpyxl
        │   ├── excel_master.go + _test.go
        │   └── csv_timelogs.go + _test.go
        │
        ├── corrections/
        │   ├── store.go + _test.go
        │   └── context_builder.go + _test.go
        │
        ├── keywords/
        │   ├── loader.go
        │   └── updater.go
        │
        ├── auth/
        │   ├── jwt.go
        │   ├── middleware.go
        │   └── password.go
        │
        ├── models/
        │   ├── ddr.go
        │   ├── occurrence.go
        │   ├── correction.go
        │   ├── keyword.go
        │   └── user.go
        │
        └── db/
            ├── pool.go                      # pgx connection pool
            └── queries/
                ├── ddrs.go
                ├── occurrences.go
                └── corrections.go
```

---

### Architectural Boundaries

**API Boundaries:**
- All requests enter via Nginx reverse proxy — no direct port exposure except Nginx 443
- `/api/*` proxied to Python backend
- `/api/auth/login` only unauthenticated endpoint; all protected routes require Bearer JWT
- Gemini API called only from `pipeline/extract` — nowhere else
- Qdrant called only from `search/qdrant` — nowhere else

**Component Boundaries:**
- `src/api/` handlers: parse request, call service classes, serialize response — zero business logic
- `src/services/`: pure workflow logic, no HTTP awareness
- `src/repository/crud/`: persistence access through SQLAlchemy repository classes
- Frontend `components/`: never call API directly — always via hooks
- Frontend `hooks/`: all data fetching lives here — never in page or domain components

**Data Boundaries:**
- Raw Gemini responses + validation errors: `ddr_dates.raw_response` + `ddr_dates.error_log` (JSONB) — immutable after write
- Validated extraction: `ddr_dates.final_json` (JSONB)
- Occurrences: relational rows in `occurrences` — derived from `final_json` at generation time
- Corrections: `corrections` table — append-only, never update/delete
- Keywords: `ces-backend/src/resources/keywords.json` or equivalent resource module — in-memory at runtime, file is source of truth

---

### Data Flow

```
1. UPLOAD
   POST /ddrs/upload → multipart PDF saved to disk
   → ddrs row created (status: "queued")
   → background task dispatched

2. EXTRACTION (background, per-date parallel)
   pre_split(pdf_path) → dict[date → pdf_bytes]
   For each chunk (semaphore-bounded async task):
     → extract(pdf_bytes, ddr_schema.json, corrections_context)
     → Gemini 2.5 Flash-Lite responseSchema
     → validate() → DDRDate struct/model
     → store(raw, validated, error)
     → emit SSE event (date_complete | date_failed)
   → occurrence_engine(validated_dates)
     classify() → infer_mmd() → density_join() → dedup()
   → store occurrences
   → emit SSE (processing_complete)
   → update ddr status: "complete" | "failed"

3. QUERY
   GET /ddrs/:id/occurrences → DB → rows
   POST /occurrences/query → query_handler → BM25 + Qdrant → ranked results

4. CORRECTION
   PATCH /occurrences/:id → update occurrence row
   → insert correction row (append-only)
   → context_builder recomputes next prompt context (last 20)

5. EXPORT
   GET /export/ddr/:id → occurrences + corrections
   → excel_report() → .xlsx → streaming response
```

---

### Integration Points

**External:**
- Gemini API — `pipeline/extract` only; key from env, never logged
- Qdrant (`qdrant:6333` Docker network) — `search/qdrant` only; degrades to BM25 if unreachable

**Internal (Docker network):**
- PostgreSQL `postgres:5432` — all backends via connection pool
- Qdrant `qdrant:6333` — search package only
- Frontend static served by Nginx from `/app/dist`

**SSE:**
- Python: FastAPI `StreamingResponse` with async generator reading asyncio queue
- Frontend: `EventSource` + 3s polling fallback on connection drop

## Architecture Validation Results

### Coherence Validation ✅

All technology choices compatible. FastAPI + asyncio + google-genai[aiohttp] fully async. PostgreSQL 16 JSONB handled by SQLAlchemy async + asyncpg. JWT (HS256) handled by python-jose.

Pattern consistency confirmed: snake_case JSON via Pydantic models, UUID v4 primary keys, SSE payload structure explicitly defined, error response shape standardized, and Python-only backend rule resolves backend ambiguity.

### Requirements Coverage Validation ✅

All 35 FRs mapped to specific files. All 16 NFRs addressed architecturally. See Project Structure section for FR→file mapping.

### Gap Analysis Results

**Gap 1 — Embedding model (Minor, resolved)**
Use `text-embedding-004` (Google AI, same API key). Called from `search/qdrant` post-extraction. Embed time log `details` rows → insert into Qdrant `ddr_time_logs` collection.

**Gap 2 — PDF storage (Minor, resolved)**
Add `pdfs` Docker volume mounted at `/app/uploads`. Save uploads as `/app/uploads/{uuid}.pdf`. Store path in `ddrs.file_path` column.

**Gap 3 — Python background tasks (Minor, resolved)**
FastAPI `BackgroundTasks` sufficient at 10–15 DDRs/day. `POST /ddrs/upload` returns 201 immediately; `background_tasks.add_task(run_pipeline, ddr_id)` dispatches extraction.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
1. Complete FR→file mapping — every requirement has an exact implementation home
2. Python-only test coverage enforced structurally — mirror packages, shared fixtures, Python-only backend rule
3. All 16 NFRs addressed architecturally — not deferred to implementation
4. 3 minor gaps identified and resolved inline — no blocking unknowns remain
5. Correction store + context injection fully specified — core differentiator protected

**Areas for Future Enhancement:**
- Qdrant embedding upgradeable to dedicated service if volume grows
- Background tasks upgradeable to arq/Celery if > 50 concurrent DDRs needed
- CloudWatch log aggregation wireable without architecture changes
- DB read replica addable behind db/pool without API changes

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly — no independent stack choices
- Use implementation patterns for all naming, error handling, logging, response shapes
- `api/` handlers call domain packages — domain packages never import `api/`
- Python backend implementation is canonical for backend behavior.

**First Implementation Priority:**
```bash
docker-compose up -d
cd ces-ddr-platform/ces-backend && alembic upgrade head
npm create vite@latest ces-frontend -- --template react-ts
# Then: pipeline/pre_split — core PoC validation first
```

**Test coverage Gate (before V1 launch):** `ces-backend/tests/fixtures/` suite must pass the Python backend. Backend selection decision made. One codebase maintained forward.
