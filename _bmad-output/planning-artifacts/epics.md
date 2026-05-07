---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# Canadian Energy Service Internal Tool - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the CES DDR Intelligence Platform, decomposing the requirements from the PRD, Architecture, and UX Design Specification into implementable stories.

## Current Backend Standard

Stories and epics from 2026-05-07 forward use the Python FastAPI project backend standard: `src/` package layout, `decouple + BackendBaseSettings`, async SQLAlchemy repository pattern, Alembic in `src/repository/migrations`, `pytest`, and `ruff`. Older dual-backend or root `app/` wording is superseded.

## Requirements Inventory

### Functional Requirements

**Document Ingestion & Processing**
- FR1: Users can upload a DDR PDF to the platform for processing
- FR2: System can detect date boundaries within a DDR PDF and split it into per-date chunks
- FR3: System can extract structured drilling data from each per-date chunk using an AI model (Gemini 2.5 Flash-Lite)
- FR4: System can validate extracted data against a defined schema (Pydantic v2) and record validation errors
- FR5: Users can view real-time processing status for an in-progress or completed DDR ingestion

**Occurrence Generation & Management**
- FR6: System can generate an occurrence table from validated extracted data
- FR7: System can classify each occurrence by type using a rule-based keyword engine (~250 keywords → 15–17 parent types)
- FR8: System can infer measured depth (mMD) for each occurrence from time log data (problem-line depth first, backward scan fallback)
- FR9: System can determine mud density for each occurrence from the mud record using nearest-timestamp proximity
- FR10: System can deduplicate occurrences within a report by (type, mMD) pair
- FR11: Users can view the occurrence table for a DDR filtered by type, section, well, and date range

**Inline Editing & Correction Store**
- FR12: Users can edit any field of any occurrence row before export
- FR13: System can capture reason and metadata (field name, original value, corrected value, user, timestamp, DDR source) when a user edits an occurrence
- FR14: System can store all occurrence edits and associated metadata in a persistent correction store (PostgreSQL)
- FR15: System can inject a summarized subset of correction history (last 20, capped) as context when generating occurrences for future DDRs
- FR16: Users can review all stored corrections across all DDRs

**Data Export**
- FR17: Users can export occurrences for a single DDR as a formatted Excel file (.xlsx, dark header row)
- FR18: Exported Excel files include an edit history sheet when corrections were made to that DDR's occurrences
- FR19: Users can export all occurrences across all processed DDRs as a single master Excel file (occurrences_all.xlsx)
- FR20: Users can export time log data for a well as a CSV file

**Query & History**
- FR21: Users can search occurrence and time log data using natural language queries (BM25 + Qdrant vector)
- FR22: Users can filter occurrence history across all DDRs by well, area, operator, type, and date range
- FR23: Users can view structured time log data for any processed well
- FR24: Users can view deviation survey data for any processed well
- FR25: Users can view bit record data for any processed well

**Pipeline Operations & Monitoring**
- FR26: Users can view a processing queue showing status of all DDR ingestion jobs
- FR27: Users can view per-date extraction status (success / warning / failed) for any processed DDR
- FR28: Users can view error logs including raw AI response and schema validation errors for any failed date
- FR29: Users can re-run extraction for a specific failed date, with an optional manual date boundary override
- FR30: System marks failed extraction dates visibly in the occurrence view — they are not silently omitted from aggregates or counts
- FR31: Users can view AI compute cost tracking for the processing pipeline

**System Configuration & Access**
- FR32: Users can update keyword-to-type mappings in the classification engine without a code deployment
- FR33: System retains the raw AI response and validated JSON for every processed date chunk (no TTL)
- FR34: System requires authentication before granting access to any feature or data
- FR35: All authenticated users have identical full access to all system capabilities

### NonFunctional Requirements

**Performance**
- NFR-P1: Natural language query results returned within 3 seconds end-to-end
- NFR-P2: Full 30-day DDR (100–300 pages) completes extraction in < 90s sequential / < 30s parallel async
- NFR-P3: Occurrence table renders within 500ms for datasets up to 100 rows
- NFR-P4: Initial application page load completes within 2 seconds on internal network
- NFR-P5: PDF upload acknowledged (processing started) within 1 second of submission
- NFR-P6: Excel export completes within 30 seconds for a full DDR occurrence set

**Security**
- NFR-S1: All application routes and API endpoints reject unauthenticated requests — no public surface
- NFR-S2: Gemini API key stored as environment variable; never in logs, error messages, or source code
- NFR-S3: User credentials stored hashed — no plaintext passwords at any layer
- NFR-S4: No outbound network calls except to Gemini API and Qdrant

**Reliability**
- NFR-R1: Extraction failure for one date chunk must not block other date chunks in the same DDR
- NFR-R2: System must not silently discard occurrences — any extraction failure flagged with error reason
- NFR-R3: Raw Gemini responses and validated JSON retained with no TTL
- NFR-R4: Processing queue durable across application restarts

**Integration**
- NFR-I1: Gemini API rate limit errors (HTTP 429) handled with exponential backoff (1s→2s→4s→8s, max 3 retries), surfaced as per-date warning
- NFR-I2: NL query degrades gracefully to BM25 keyword search if Qdrant is unavailable
- NFR-I3: All PostgreSQL writes during extraction must be transactional — no partial state committed
- NFR-I4: Excel exports compatible with Excel 2016+ and LibreOffice Calc

### Additional Requirements

**Architecture-derived technical requirements:**

- ARCH-1: Project initialized as monorepo — ces-frontend (React/Vite/TS) and ces-backend (FastAPI). Docker Compose brings up PostgreSQL 16 + Qdrant at start.
- ARCH-2: DB schema uses Alembic as the sole migration authority. Tables: users, ddrs, ddr_dates, occurrences, corrections, keywords, processing_queue, pipeline_runs — all UUID v4 PKs, snake_case, epoch timestamps.
- ARCH-3: Auth via JWT (HS256), 8-hour expiry, static credentials stored bcrypt-hashed. All routes except `/auth/login` require Bearer JWT. Frontend stores token in localStorage.
- ARCH-4: Processing status transport is SSE — `GET /ddrs/:id/status/stream`. Events: `date_complete`, `date_failed`, `processing_complete`. Frontend uses EventSource with 3s polling fallback.
- ARCH-5: All API responses use standard shapes: direct object/array for success, `{ items, total, page, page_size }` for paginated, `{ error, code, details }` for errors. HTTP status codes standardized (200/201/400/401/404/429/500).
- ARCH-6: Gemini 429 handling: exponential backoff (1s→2s→4s→8s), max 3 retries, then mark date as `warning` with code `RATE_LIMITED`.
- ARCH-7: Frontend routing via React Router v6. Routes: `/login`, `/`, `/reports/:id`, `/history`, `/query`, `/monitor`, `/settings/keywords`. Auth guard `<ProtectedRoute>` redirects to `/login` if no valid token.
- ARCH-8: All frontend API calls through `src/lib/api.ts` — never raw fetch in components. 401 response → clear token + redirect to `/login`.
- ARCH-9: Keyword store is `ces-backend/src/resources/keywords.json` or equivalent backend resource module — single source of truth read by the Python backend. `PUT /keywords` writes file + triggers in-memory reload without restart.
- ARCH-10: Correction context injection cap — last 20 corrections, summarized format: `"Field '{field}': '{original}' corrected to '{corrected}' ({count} times). Reason: {most_recent_reason}"`.
- ARCH-11: Embedding model `text-embedding-004` (Google AI, same API key). Called from `search/qdrant` post-extraction. Qdrant collection: `ddr_time_logs`.
- ARCH-12: PDF storage — `pdfs` Docker volume at `/app/uploads`. Path stored in `ddrs.file_path`.
- ARCH-13: Python background tasks via FastAPI `BackgroundTasks`. Upload returns 201 immediately; pipeline dispatched as background task.
- ARCH-14: Deployment target: single AWS EC2 instance (t3.medium/large), Docker Compose in production, Nginx reverse proxy + SSL termination. One Python backend container runs behind Nginx.
- ARCH-15: Python backend test coverage: pytest fixtures live in `ces-backend/tests/fixtures/`.
- ARCH-16: OpenAPI spec auto-generated by FastAPI `/docs`.
- ARCH-17: Structured JSON logging pattern with `request_id` threading. Never log GEMINI_API_KEY, JWT_SECRET, POSTGRES_PASSWORD, Authorization header.
- ARCH-18: AI cost tracked in `pipeline_runs` table per date chunk (`gemini_input_tokens`, `gemini_output_tokens`, `cost_usd`). Weekly summary aggregated from DB.
- ARCH-19: PostgreSQL + Qdrant backups: `pg_dump` + Qdrant snapshot API → S3 (nightly cron).

### UX Design Requirements

**Design System & Tokens**
- UX-DR1: Implement CES design token system in `tailwind.config.js`: `--ces-red: #C41230`, `--edit-indicator: #D97706`, `--surface: #F9FAFB`. Dark mode disabled at root (`<html class="light">`). Primary dark: `#A31028`, Primary light: `#F8E4E8`.
- UX-DR2: Implement `TYPE_COLOURS` map for 15–17 occurrence type badge colors; implement `SECTION_COLOURS`: Surface=emerald-600 (#059669), Int.=sky-600 (#0284C7), Main=indigo-600 (#4F46E5). `TypeBadge` and `SectionBadge` components derive color from these maps.
- UX-DR3: Typography system — Inter/system-ui stack. Display: 24px/bold, Heading: 18px/semibold, Subheading: 14px/medium, Body: 14px/normal, Caption: 12px/normal, Mono: 13px/font-mono for depth values. Column headers: 12px uppercase/semibold. Table cell: 14px/1.2 line-height.
- UX-DR4: Spacing — base unit 4px. Table row height: 40px compact (~20 rows visible above fold at 1080p). Sidebar width: 220px expanded. Card padding: 16px.

**Custom Components (6 required)**
- UX-DR5: `OccurrenceTable` — TanStack Table with sticky header, single-click inline cell edit, amber edit-dot column (22px), action column (56px). States: default | row-hover (slate-50) | row-edited (amber left border + dot) | row-failed (red-50 bg + #C41230 left border 4px) | cell-editing. Keyboard: Arrow keys navigate cells, Enter opens inline edit, Tab next cell. `role="grid"`, `aria-rowcount`. No pagination — all rows visible.
- UX-DR6: `ReasonCaptureModal` — row-anchored (`position:absolute` near triggering row, never center-screen), no backdrop. Auto-focus on text field on open. Enter submits, Escape cancels. Pre-filled header shows "Field: original → corrected". 2 fields: reason text (required) + submit. `role="dialog"`, focus trap, focus returns to triggering cell on close.
- UX-DR7: `CollapsibleSidebar` — 220px expanded (icon+label) ↔ 48px collapsed (icon only). Toggle via chevron at bottom. State persisted in `localStorage` key `ces-sidebar-collapsed`. At ≥1280px: expanded default; 1024–1279px: collapsed default; 768–1023px: hidden behind hamburger.
- UX-DR8: `ProcessingQueueRow` — status dot (green/amber/red/grey) + filename + sub-status text + progress bar (active only) + date count badges + View link. States: Queued | Processing (with % progress) | Complete-clean | Complete-warnings | Complete-failed. `aria-live="polite"` region for status updates.
- UX-DR9: `NLQueryBar` — full-width search input, Enter or search icon submits. Example query chips rendered below input (e.g. "stuck pipe events on ARC last quarter"). Last 5 queries via ↑ key. Inline error below bar on failure. × clear button when field has content.
- UX-DR10: `MetricCard` — dashboard stat card (value + label + optional color treatment). Used for: DDR count, occurrence count, AI cost, failed count, correction count.

**Navigation & Layout Patterns**
- UX-DR11: Sidebar navigation active item style: `#FEF2F2` bg + `#C41230` left border 3px + red label. All nav items: icon + label always visible when expanded (no icon-only nav). Collapsed: tooltip on hover shows label.
- UX-DR12: Breadcrumbs on Report Detail view only (Reports › DDR-name). Tab navigation within Report Detail: Occurrences | Failed Dates | Edit History | Export — active tab = `--ces-red` 2px underline.
- UX-DR13: Button hierarchy — Primary: `bg-[--ces-red] text-white`, one per view max. Secondary: `border-[--ces-red] text-[--ces-red]`. Ghost: `text-muted-foreground hover:bg-accent`. Destructive: `bg-red-600 text-white`, always requires confirmation step. Loading state: spinner replaces label, width fixed.

**Feedback Patterns**
- UX-DR14: Toast notifications (Sonner) — bottom-right, max 3 stacked. Success: green 3s auto-dismiss. Info: blue 4s auto-dismiss. Warning: amber 6s manual-dismiss. Error: red manual-dismiss only. Toast container: `aria-live="assertive"` for errors, `aria-live="polite"` for success/info.
- UX-DR15: Inline feedback — amber dot on edited OccurrenceTable rows. `FailedDateRow`: red-tinted background `#FEF2F2` + left border `#C41230` 4px. `DateStatusIndicator` badge: green=resolved, amber=pending, red=failed. Failed date notices persistent (not transient toasts).
- UX-DR16: Processing status specificity — display "Processing date N of M..." not generic spinner during 90s DDR processing. Non-blocking — user can navigate while DDR processes in background.

**Search & Filtering**
- UX-DR17: OccurrenceTable filters — column-level dropdowns (Type, Section, Status) + global text search above table. Active filters shown as pill chips with × to remove. Filter state preserved in URL params. Debounced 300ms update, no full-page reload.
- UX-DR18: Sort patterns — column header click cycles ascending → descending → unsorted. Sort indicator ↑↓ in header. Default sort: Date descending. Multi-sort via Shift+click (supported, not advertised).

**Accessibility (WCAG 2.1 AA)**
- UX-DR19: Focus rings — `ring-2 ring-[--ces-red]` on all interactive elements. Never `outline-none` without ring replacement. Skip link in root layout: `<a href="#main-content" class="sr-only focus:not-sr-only">Skip to main content</a>`.
- UX-DR20: Edit indicator dual encoding — amber dot + column header label "Edited" + `aria-label="Cell manually corrected"`. (Amber dot alone fails contrast for small elements.)
- UX-DR21: Screen reader support — OccurrenceTable `role="grid"` with `rowheader`/`columnheader`. Edited cells: `aria-label="[column]: [value]. Manually corrected."`. Failed date rows: `aria-label="Date resolution failed. Action required."`. TypeBadge/SectionBadge: `aria-label` not color-only.
- UX-DR22: Run `@axe-core/react` in CI — fail build on new violations. Responsive testing at md (768px) and xl (1280px) breakpoints minimum.

**Upload UX**
- UX-DR23: Upload form — drag-and-drop zone + "Browse files" secondary button. Accepts `.pdf`/`.PDF` only — rejected files show inline error (not toast). Upload progress: inline progress bar replaces zone during upload.

**Empty & Loading States**
- UX-DR24: Skeleton loading for OccurrenceTable initial load (5 rows × 4 columns grey bars). NLQueryBar results: spinner + "Searching…" text. Export button: spinner + "Preparing export…", button disabled during generation. ProcessingQueueRow shows spinner + "Processing…".
- UX-DR25: Empty states with contextual messages and actions — No reports: "No DDR reports yet" + Upload CTA. No filter results: "No occurrences match your filters" + Clear Filters. No failed dates: "All dates resolved" (positive). Processing queue empty: "No active processing jobs".

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 2 | PDF upload endpoint |
| FR2 | Epic 2 | Date boundary detection / pre-splitter |
| FR3 | Epic 2 | Per-date Gemini extraction |
| FR4 | Epic 2 | Pydantic schema validation + error recording |
| FR5 | Epic 2 | Real-time processing status (SSE) |
| FR6 | Epic 3 | Occurrence table generation from validated data |
| FR7 | Epic 3 | Keyword engine type classification |
| FR8 | Epic 3 | mMD inference (problem-line first, backward scan) |
| FR9 | Epic 3 | Density nearest-timestamp join |
| FR10 | Epic 3 | Dedup by (type, mMD) |
| FR11 | Epic 3 | Filterable occurrence table view |
| FR12 | Epic 4 | Inline any-field edit before export |
| FR13 | Epic 4 | Reason + metadata capture on edit |
| FR14 | Epic 4 | Persistent correction store |
| FR15 | Epic 4 | Correction context injection on future runs |
| FR16 | Epic 4 | Correction store review dashboard |
| FR17 | Epic 5 | Per-DDR .xlsx export |
| FR18 | Epic 5 | Edit history sheet in export when corrections exist |
| FR19 | Epic 5 | Master occurrences_all.xlsx export |
| FR20 | Epic 5 | Time log CSV export |
| FR21 | Epic 6 | NL query (BM25 + Qdrant vector) |
| FR22 | Epic 6 | Cross-DDR filter by well/area/operator/type/date |
| FR23 | Epic 6 | Time log view per well |
| FR24 | Epic 6 | Deviation survey view per well |
| FR25 | Epic 6 | Bit record view per well |
| FR26 | Epic 7 | Processing queue view |
| FR27 | Epic 7 | Per-date extraction status view |
| FR28 | Epic 7 | Error log view (raw AI response + Pydantic errors) |
| FR29 | Epic 7 | Per-date re-run with manual date override |
| FR30 | Epic 3 | Failed date flag in occurrence view (not silently omitted) |
| FR31 | Epic 7 | AI compute cost tracking view |
| FR32 | Epic 7 | Keyword-to-type mapping editor (no redeploy) |
| FR33 | Epic 2 | Raw AI response + validated JSON retention (no TTL) |
| FR34 | Epic 1 | Auth required on all routes |
| FR35 | Epic 1 | Single full-access role for all authenticated users |

## Epic List

### Epic 1: Platform Foundation & Authenticated Access
Users can securely log in and access the platform. Python FastAPI backend initialized with the project `src/` structure, DB schema migrated, Docker Compose running, frontend scaffold live with protected routing.
**FRs covered:** FR34, FR35
**Arch covered:** ARCH-1, ARCH-2, ARCH-3, ARCH-7, ARCH-8, ARCH-14, ARCH-15, ARCH-17

### Epic 2: DDR Upload & AI Extraction Pipeline
Users can upload a DDR PDF and watch it process in real-time — per-date status (success/warning/failed) streams live, failures are flagged and raw responses retained, never silently dropped.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR33
**Arch covered:** ARCH-4 (SSE), ARCH-6 (Gemini 429 backoff), ARCH-11 (embedding post-extraction), ARCH-12 (PDF volume), ARCH-13 (background tasks), ARCH-16 (OpenAPI), ARCH-18 (cost tracking rows written), ARCH-19 (backup infra)

### Epic 3: Occurrence Table & Generation
Users can view the structured occurrence table for any processed DDR — type-classified, mMD inferred, density joined, deduplicated, with failed dates flagged inline, filterable by type/section/well/date.
**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR11, FR30
**UX covered:** UX-DR2 (TypeBadge/SectionBadge), UX-DR5 (OccurrenceTable), UX-DR7 (CollapsibleSidebar), UX-DR11–12 (nav), UX-DR15 (FailedDateRow), UX-DR16–18 (processing status, filters), UX-DR19–21 (a11y), UX-DR24–25 (loading/empty states)

### Epic 4: Inline Editing & Correction Store
Users can correct any occurrence field inline — reason captured, stored with full metadata, reviewed in a dashboard, and automatically summarized into future extraction prompts so the same mistake doesn't repeat.
**FRs covered:** FR12, FR13, FR14, FR15, FR16
**UX covered:** UX-DR6 (ReasonCaptureModal), UX-DR14 (toast feedback), UX-DR15 (amber edit-dot), UX-DR20 (edit indicator a11y)
**Arch covered:** ARCH-10 (correction cap — last 20 summarized)

### Epic 5: Data Export
Users can export per-DDR occurrences to .xlsx (with edit history sheet when corrections exist), export all DDRs to master occurrences_all.xlsx, and export time log data per well as CSV — all one click, no wizard.
**FRs covered:** FR17, FR18, FR19, FR20
**UX covered:** UX-DR13 (export button hierarchy), UX-DR14 (export toast), UX-DR24 (export loading state)

### Epic 6: Query & Well History
Users can search all DDR data using natural language (BM25 + Qdrant vector, graceful degradation to BM25 if Qdrant unavailable), filter cross-DDR occurrence history, and access time log, deviation survey, and bit record data for any well.
**FRs covered:** FR21, FR22, FR23, FR24, FR25
**UX covered:** UX-DR9 (NLQueryBar + example chips), UX-DR17–18 (filter/sort patterns)
**Arch covered:** ARCH-11 (Qdrant ddr_time_logs collection), NFR-I2 (BM25 fallback)

### Epic 7: Pipeline Monitoring & System Administration
Users can monitor pipeline queue + AI costs, drill into per-date extraction status, view raw error logs, re-run failed dates with manual date override, and update keyword rules without a code deploy.
**FRs covered:** FR26, FR27, FR28, FR29, FR31, FR32
**UX covered:** UX-DR8 (ProcessingQueueRow), UX-DR10 (MetricCard), UX-DR16 (processing status specificity)
**Arch covered:** ARCH-9 (keyword reload via PUT /keywords), ARCH-18 (cost tracking from pipeline_runs table)

---

## Epic 1: Platform Foundation & Authenticated Access

Users can securely log in and access the platform. Both backend projects initialized, DB schema migrated, Docker Compose running, frontend scaffold live with protected routing.

### Story 1.1: Project Scaffold & Development Infrastructure

As an authenticated CES user,
I want the platform infrastructure initialized and running locally,
So that development can begin on a stable, reproducible foundation.

**Acceptance Criteria:**

**Given** the monorepo root `ces-ddr-platform/` is created
**When** `docker compose up -d` is run
**Then** PostgreSQL 16 container starts healthy on port 5432
**And** Qdrant container starts healthy on port 6333
**And** `docker compose ps` shows both services as `running`

**Given** the frontend scaffold exists
**When** `npm run dev` is run in `ces-frontend/`
**Then** Vite dev server starts on port 5173
**And** `vite.config.ts` proxies `/api/*` to backend URL (no CORS issues in dev)
**And** `tailwind.config.js` contains CES design tokens: `--ces-red: #C41230`, `--edit-indicator: #D97706`, `--surface: #F9FAFB`
**And** shadcn/ui is initialized with components in `src/components/ui/`
**And** `<html class="light">` is set at root (dark mode disabled)

**Given** the Python backend scaffold exists
**When** `source .venv/bin/activate && uvicorn src.main:backend_app --reload` is run in `ces-backend/`
**Then** server starts and `GET /api/health` returns `{ "status": "ok" }` with HTTP 200
**And** `src/config/settings/base.py` uses `decouple + BackendBaseSettings`
**And** SQLAlchemy async session dependencies are available through `src/api/dependencies`
**And** repository classes live under `src/repository/crud`
**And** no alternate backend files or direct DB query helper modules are required
**And** `source .venv/bin/activate && ruff check src tests` passes
**And** `source .venv/bin/activate && pytest` passes

**Given** `.env.example` files exist in repo root, `ces-frontend/`, and `ces-backend/`
**When** the `.gitignore` is reviewed
**Then** `.env` files are gitignored at all levels
**And** `GEMINI_API_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD` never appear in any committed file

### Story 1.2: Database Schema — Users Table & Migration Tooling

As a platform developer,
I want the users table created via versioned migrations on the Python backend,
So that authentication can be built on a schema the Python backend share identically.

**Acceptance Criteria:**

**Given** Python backend Alembic is configured under `ces-backend/src/repository/migrations/`
**When** migration files are created manually and `alembic upgrade head` is run
**Then** `users` table is created with: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `username VARCHAR(255) UNIQUE NOT NULL`, `password_hash TEXT NOT NULL`, `created_at BIGINT NOT NULL`, `updated_at BIGINT NOT NULL`
**And** SQLAlchemy model `src/models/db/user.py` maps the same table
**And** Alembic remains the only migration authority

**Given** migrations have run
**When** a developer inspects the DB
**Then** `\d users` shows structure matching SQLAlchemy ORM model and migration files

### Story 1.3: Authentication API — Login & JWT Middleware

As a CES staff member,
I want to log in with my username and password and receive a JWT,
So that I can access all platform features without re-authenticating for 8 hours.

**Acceptance Criteria:**

**Given** a user exists in the `users` table with bcrypt-hashed password
**When** `POST /api/auth/login` is called with valid `{ "username": "...", "password": "..." }`
**Then** HTTP 200 is returned with `{ "token": "<JWT>", "expires_at": <epoch_seconds> }`
**And** JWT is HS256-signed using `JWT_SECRET_KEY` from environment — never hardcoded
**And** JWT payload contains `user_id` and `exp` claims

**Given** `POST /api/auth/login` is called with wrong credentials
**When** username doesn't exist or password doesn't match bcrypt hash
**Then** HTTP 401 is returned with `{ "error": "Invalid credentials", "code": "UNAUTHORIZED", "details": {} }`
**And** response time is identical for both failure cases (no timing oracle)

**Given** any protected endpoint except `POST /api/auth/login` is called without `Authorization: Bearer <token>`
**When** the JWT middleware processes the request
**Then** HTTP 401 is returned with `{ "error": "Authentication required", "code": "UNAUTHORIZED", "details": {} }`

**Given** a JWT with expired `exp` claim is sent
**When** the JWT middleware validates it
**Then** HTTP 401 is returned with `UNAUTHORIZED` error code

**Given** structured logging middleware is active
**When** any request is processed
**Then** log line contains `{ "timestamp", "level", "service", "request_id", "message" }` in JSON format
**And** `Authorization` header value, `JWT_SECRET`, and `POSTGRES_PASSWORD` never appear in any log line
**And** `request_id` (UUID) is generated per request and present on all log lines for that request

**Given** the Python backend implements the login endpoint
**When** a seeded SQL user logs in through `/api/auth/login`
**Then** the API returns a valid JWT and epoch expiry
**And** backend tests, Ruff, and an HTTP login smoke test pass before story completion

### Story 1.4: Frontend Authentication Shell & Protected Routing

As a CES staff member,
I want a login page and protected app shell,
So that unauthenticated users are redirected to login and authenticated users can navigate the platform.

**Acceptance Criteria:**

**Given** a user navigates to any route other than `/login` without a valid token in `localStorage`
**When** `<ProtectedRoute>` evaluates the token
**Then** user is redirected to `/login`

**Given** a user submits valid credentials on `LoginPage.tsx`
**When** `POST /auth/login` succeeds
**Then** JWT is stored in `localStorage` via `src/lib/auth.ts` helper
**And** user is redirected to `/` (dashboard placeholder)
**And** page loads within 2 seconds on internal network (NFR-P4)

**Given** a user submits invalid credentials on `LoginPage.tsx`
**When** API returns HTTP 401
**Then** inline error message displays below the form: "Invalid username or password"
**And** password field is cleared; username field retains value

**Given** `src/lib/api.ts` typed API client is in use
**When** any API call returns HTTP 401
**Then** `localStorage` token is cleared and user is redirected to `/login`
**And** all API calls from any component or hook include `Authorization: Bearer <token>` header automatically — never raw `fetch()` in components

**Given** `App.tsx` uses React Router v6
**When** routes are inspected
**Then** routes `/login`, `/`, `/reports/:id`, `/history`, `/query`, `/monitor`, `/settings/keywords` are declared
**And** all routes except `/login` are wrapped in `<ProtectedRoute>`
**And** API base URL is read from `VITE_API_URL` env var — never hardcoded

**Given** `LoginPage.tsx` renders
**When** a user inspects interactive elements
**Then** primary button uses `bg-[--ces-red] text-white` styling (UX-DR1, UX-DR13)
**And** all interactive elements have `ring-2 ring-[--ces-red]` focus rings (UX-DR19)

---

## Epic 2: DDR Upload & AI Extraction Pipeline

Users can upload a DDR PDF and watch it process in real-time — per-date status streams live, failures flagged and raw responses retained, never silently dropped.

### Story 2.1: DDR & Pipeline Database Schema

As a platform developer,
I want DDR, pipeline, and cost tracking tables created via migrations on the Python backend,
So that all extraction pipeline data has a durable, structured home before any pipeline code runs.

**Acceptance Criteria:**

**Given** migration `002_ddr_schema` runs on the Python backend
**When** schema is inspected
**Then** `ddrs` table exists: `id UUID PK`, `file_path TEXT NOT NULL`, `status VARCHAR(20) NOT NULL DEFAULT 'queued'`, `well_name TEXT`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`
**And** `ddr_dates` table exists: `id UUID PK`, `ddr_id UUID REFERENCES ddrs(id)`, `date VARCHAR(8) NOT NULL`, `status VARCHAR(20) NOT NULL`, `raw_response JSONB`, `final_json JSONB`, `error_log JSONB`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`
**And** `processing_queue` table exists: `id UUID PK`, `ddr_id UUID REFERENCES ddrs(id)`, `position INT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`
**And** `pipeline_runs` table exists: `id UUID PK`, `ddr_date_id UUID REFERENCES ddr_dates(id)`, `gemini_input_tokens INT`, `gemini_output_tokens INT`, `cost_usd NUMERIC(10,6)`, `created_at TIMESTAMPTZ NOT NULL`
**And** indexes `idx_ddr_dates_ddr_id` and `idx_processing_queue_ddr_id` are created
**And** Alembic is the sole migration source for this schema

**Given** `ddrs.status` column
**When** valid status strings are reviewed
**Then** only `queued | processing | complete | failed` are valid values (application-enforced)

**Given** `ddr_dates.status` column
**When** valid status strings are reviewed
**Then** only `success | warning | failed` are valid values

**Given** `pdfs` Docker volume declared in `docker-compose.yml`
**When** Docker Compose runs
**Then** volume is mounted at `/app/uploads` in the backend container

### Story 2.2: PDF Upload Endpoint & Processing Queue

As a CES staff member,
I want to upload a DDR PDF and have it immediately queued for processing,
So that extraction starts without waiting and I get acknowledgement within 1 second.

**Acceptance Criteria:**

**Given** an authenticated user submits a PDF via `POST /ddrs/upload` (multipart form-data)
**When** the request is received
**Then** PDF is saved to `/app/uploads/{uuid}.pdf` on the Docker volume
**And** a `ddrs` row is created with `status: "queued"` and `file_path` set
**And** a `processing_queue` row is inserted for this DDR
**And** HTTP 201 is returned within 1 second with `{ "id": "<uuid>", "status": "queued" }` (NFR-P5)
**And** background pipeline task is dispatched using FastAPI/asyncio background processing — does not block response

**Given** a non-PDF file is uploaded
**When** the upload endpoint validates the file
**Then** HTTP 400 is returned with `{ "error": "Only PDF files accepted", "code": "VALIDATION_ERROR", "details": {} }`
**And** no file is saved to disk

**Given** `GET /ddrs` is called by an authenticated user
**When** the response is returned
**Then** list of all DDRs is returned with `id`, `file_path`, `status`, `well_name`, `created_at`
**And** sorted by `created_at` descending

**Given** `GET /ddrs/:id` is called with a valid DDR id
**When** the DDR exists
**Then** DDR detail is returned including `id`, `status`, `file_path`, `well_name`, `created_at`

**Given** `GET /ddrs/:id` is called with a non-existent id
**When** the query finds no row
**Then** HTTP 404 is returned with `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`

**Given** OpenAPI spec auto-generation is active
**When** `GET /docs` is accessed
**Then** `/auth/login`, `/ddrs`, `/ddrs/upload`, `/ddrs/:id` endpoints are documented

### Story 2.3: PDF Pre-Splitter — Date Boundary Detection

As a platform developer,
I want the pipeline to split a Pason DDR PDF into per-date chunks using native text extraction,
So that each date's data can be independently extracted and validated.

**Acceptance Criteria:**

**Given** a Pason DDR PDF with native text layer (not scanned)
**When** `pipeline/pre_split` processes it using pdfplumber
**Then** Tour Sheet Serial Number format `XXXXXX_YYYYMMDD_XA` is detected as date boundary signal
**And** pages are grouped into `dict[date_string → pdf_bytes]` — one entry per detected date
**And** multi-date overflow is handled: if Tour 3 of date X spills onto a page containing date Y header, pages are assigned to the correct date

**Given** a page has no detectable text layer (scanned image PDF)
**When** pdfplumber reads it
**Then** empty text result is logged as a warning with page number
**And** processing continues for remaining pages — not a fatal error

**Given** a non-standard contractor layout where Tour Sheet Serial is missing
**When** pre-splitter finds no date boundaries
**Then** a `ddr_dates` row is created with `status: "failed"` and `error_log` containing `{ "reason": "No date boundaries detected", "raw_page_content": "<first 500 chars>" }`
**And** DDR overall status is set to `"failed"` with the error surfaced

**Given** the 109-page and 229-page sample PDFs in `ces-backend/tests/fixtures/`
**When** pre-splitter test suite runs
**Then** 100% of date boundaries are correctly detected for both samples
**And** same fixture test passes on Python implementations

**Given** pdfplumber successfully splits a PDF into N date chunks
**When** the result is returned to the pipeline orchestrator
**Then** a `ddr_dates` row is created for each detected date with `status: "queued"`
**And** `ddrs.status` is updated to `"processing"`

### Story 2.4: Per-Date Gemini Extraction & Pydantic Validation

As a platform developer,
I want each date chunk sent to Gemini 2.5 Flash-Lite for structured extraction and validated against the DDR schema,
So that structured drilling data is available for occurrence generation with full audit trail and no silent failures.

**Acceptance Criteria:**

**Given** a date chunk (pdf_bytes) is ready for extraction
**When** pipeline extraction service calls Gemini 2.5 Flash-Lite with `responseSchema` from `ces-backend/src/resources/ddr_schema.json` or equivalent resource module
**Then** response is structured JSON matching the DDRDate schema (time_logs, mud_records, deviation_surveys, bit_records)
**And** `GEMINI_API_KEY` is loaded from environment only — never appears in logs or error messages (NFR-S2)
**And** backend raises typed extraction errors from `src/utilities/exceptions/` or service-specific exceptions — no raw exception strings to client

**Given** Gemini API returns HTTP 429 (rate limit)
**When** `pipeline/extract` handles the error
**Then** exponential backoff is applied: 1s → 2s → 4s → 8s, max 3 retries
**And** after exhausting retries, `ddr_dates.status` is set to `"warning"` with `error_log: { "code": "RATE_LIMITED" }`
**And** other dates in the same DDR continue processing — not aborted (NFR-R1)

**Given** Gemini returns a response
**When** `pipeline/validate` runs Pydantic v2 validation against `DDRDate` model
**Then** on success: `ddr_dates.final_json` populated, `raw_response` stored, `status` set to `"success"` — all in one transaction (NFR-I3)
**And** on validation failure: `ddr_dates.error_log` populated with Pydantic error details, `raw_response` stored, `status` set to `"failed"` — transactional (NFR-I3)
**And** raw response is retained indefinitely — no TTL (NFR-R3, FR33)

**Given** extraction failure on one date
**When** pipeline continues
**Then** other dates in the same DDR are not aborted — each date independently processed (NFR-R1)
**And** DDR overall `status` is `"complete"` if any dates succeeded, `"failed"` if all dates failed

**Given** shared test fixtures in `ces-backend/tests/fixtures/expected_timelogs.json`
**When** extraction test suite runs against sample DDR fixture
**Then** same test passes on both Python backend (test coverage validation)

### Story 2.5: SSE Processing Status Stream & Frontend Status Hook

As a CES staff member,
I want real-time per-date extraction status streamed to my browser while a DDR processes,
So that I can see exactly which dates succeeded or failed without refreshing or navigating away.

**Acceptance Criteria:**

**Given** `GET /ddrs/:id/status/stream` is called by an authenticated client
**When** the DDR is processing
**Then** server returns `Content-Type: text/event-stream`
**And** `date_complete` event emitted per successful date: `{ "date": "20241031", "status": "success", "occurrences_count": 3 }`
**And** `date_failed` event emitted per failed date: `{ "date": "20241031", "error": "Tour Sheet Serial not detected", "raw_response_id": "<uuid>" }`
**And** `processing_complete` event emitted when all dates finish: `{ "total_dates": 30, "failed_dates": 2, "warning_dates": 1, "total_occurrences": 0 }`

**Given** backend restarts while a DDR is still processing
**When** the pipeline resumes
**Then** in-progress DDR state is re-queried from `processing_queue` table — not lost (NFR-R4)

**Given** `useProcessingStatus` hook is created in `ces-frontend/src/hooks/`
**When** a DDR upload completes
**Then** hook opens `EventSource` to `/ddrs/:id/status/stream`
**And** on `date_complete`/`date_failed` events, per-date status updates in component state
**And** on `processing_complete` event, `EventSource` connection is closed
**And** if SSE connection drops, hook falls back to polling `/ddrs/:id` every 3 seconds

**Given** `ReportsPage.tsx` shows the list of DDRs
**When** a DDR is processing
**Then** processing state is visible: "Processing date N of M…" with per-date success/warning/failed counts
**And** user can navigate to other pages while processing continues in background (non-blocking)
**And** upload progress bar replaces the drag-and-drop zone during upload (UX-DR23)

**Given** processing completes with failures
**When** `ReportsPage` updates
**Then** toast notification appears: "Processing complete — N dates extracted, M failed" (UX-DR14)

### Story 2.6: Extraction Cost Tracking & Time Log Embedding

As a CES staff member,
I want AI compute costs recorded per extraction and time log text indexed into Qdrant,
So that pipeline costs are trackable and natural language search has data to query.

**Acceptance Criteria:**

**Given** a date chunk is successfully extracted by Gemini
**When** the response is processed
**Then** `pipeline_runs` row is written with `gemini_input_tokens`, `gemini_output_tokens`, `cost_usd`
**And** write is part of the same transaction as the `ddr_dates` update (NFR-I3)

**Given** a `ddr_dates` row has `status: "success"` with `final_json` populated
**When** time log embedding runs post-extraction
**Then** each time log row's `details` text is embedded using `text-embedding-004` (same Google AI API key)
**And** vector is upserted into Qdrant `ddr_time_logs` collection with metadata: `{ "ddr_id", "date", "time_from", "time_to", "code" }`
**And** if Qdrant is unreachable, embedding failure is logged as warning — extraction is not rolled back

**Given** `GET /pipeline/cost` is called with valid JWT
**When** the request is made
**Then** HTTP 200 returns aggregated data from `pipeline_runs`: `{ "total_cost_usd": N, "total_runs": N, "period": "all_time" }`

**Given** all migrations from Epic 1 and Epic 2 have run
**When** `Alembic migrations` is reviewed
**Then** file reflects current canonical schema: users, ddrs, ddr_dates, processing_queue, pipeline_runs tables

---

## Epic 3: Occurrence Table & Generation

Users can view the structured occurrence table for any processed DDR — type-classified, mMD inferred, density joined, deduplicated, with failed dates flagged inline, filterable by type/section/well/date.

### Story 3.1: Occurrences Database Schema

As a platform developer,
I want the occurrences table and initial keyword store created via migrations,
So that occurrence generation has a schema to write to and the keyword engine has a source of truth to load from.

**Acceptance Criteria:**

**Given** migration `003_occurrences` runs on the Python backend
**When** schema is inspected
**Then** `occurrences` table exists: `id UUID PK`, `ddr_id UUID REFERENCES ddrs(id)`, `ddr_date_id UUID REFERENCES ddr_dates(id)`, `well_name TEXT`, `surface_location TEXT`, `type VARCHAR(100) NOT NULL`, `section VARCHAR(20)`, `mmd FLOAT`, `density FLOAT`, `notes TEXT`, `date VARCHAR(8)`, `is_exported BOOLEAN NOT NULL DEFAULT false`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`
**And** indexes `idx_occurrences_ddr_id`, `idx_occurrences_type`, `idx_occurrences_date` are created
**And** Alembic is the sole migration source for this schema

**Given** `ces-backend/src/resources/keywords.json` or equivalent backend resource module is created
**When** file structure is reviewed
**Then** file contains `{ "<keyword>": "<type_name>", ... }` — at least one entry per occurrence type covering all 15–17 parent types
**And** the Python backend load it at startup via `keywords/loader`
**And** `Alembic migrations` is updated to include occurrences table

### Story 3.2: Keyword Classification Engine — Type & Section

As a platform developer,
I want the occurrence engine to classify each occurrence by type and section using the keyword rule engine,
So that extracted problem-line text is mapped to one of the 15–17 standard occurrence types and a casing section.

**Acceptance Criteria:**

**Given** `ces-backend/src/resources/keywords.json` or equivalent backend resource module is loaded at backend startup
**When** `occurrence/classify` processes a problem-line text string
**Then** keyword matching is case-insensitive substring match — "backreamed to free" matches keyword "backreamed"
**And** first matching keyword's mapped type is assigned (first-match wins; keyword order in file is authoritative)
**And** if no keyword matches, type is assigned `"Unclassified"`

**Given** a classified occurrence with an inferred depth (mMD)
**When** `occurrence/classify` determines section
**Then** section is `"Surface"` if mMD ≤ inferred surface casing shoe depth (fallback: 600m)
**And** section is `"Int."` if mMD ≤ inferred intermediate casing shoe depth (fallback: 2500m)
**And** section is `"Main"` if mMD > intermediate shoe depth

**Given** `ces-backend/tests/fixtures/expected_occurrences.json` contains known input→type mappings
**When** keyword classification test suite runs
**Then** ≥ 90% of expected type classifications match (FR7 success criterion)
**And** same test passes on both Python backend

**Given** keyword file is reloaded at runtime via `PUT /keywords`
**When** `occurrence/classify` is called after reload
**Then** new keyword mappings are used immediately — no restart required (ARCH-9 pattern established here)

### Story 3.3: mMD Inference, Density Join & Dedup Engine

As a platform developer,
I want the occurrence engine to infer depth, join mud density, and deduplicate occurrences,
So that each occurrence row has accurate depth, correct density from the nearest mud record, and no duplicates.

**Acceptance Criteria:**

**Given** a time log row with an explicit depth value on the problem line
**When** `occurrence/infer_mmd` processes it
**Then** problem-line stated depth is used as mMD — backward scan is NOT performed
**And** `mmd` field is set to the stated depth value as `float`

**Given** a time log row with no explicit depth on the problem line
**When** `occurrence/infer_mmd` performs backward scan
**Then** time log rows are scanned backward from the problem row to find the most recent row with a depth value
**And** that depth value is assigned as mMD
**And** if no depth found in backward scan, `mmd` is `null`

**Given** an occurrence with an inferred timestamp
**When** `occurrence/density_join` runs
**Then** the mud record with nearest timestamp to the occurrence within the same tour is selected
**And** that mud record's density value (kg/m³) is assigned to the occurrence's `density` field
**And** cross-tour density lookup is never performed — same-tour constraint enforced

**Given** multiple occurrences generated for the same DDR
**When** `occurrence/dedup` runs
**Then** occurrences sharing identical `(type, mmd)` pair within the same DDR are deduplicated — only one row kept
**And** dedup preserves the first occurrence encountered
**And** zero occurrences are silently dropped — dedup count is logged

**Given** `ces-backend/tests/fixtures/expected_occurrences.json` contains known mMD values
**When** mMD inference test suite runs
**Then** ≥ 85% of inferred mMD values are within ±10m of expected values
**And** same test passes on both Python backend

### Story 3.4: Occurrence Generation API & Pipeline Integration

As a CES staff member,
I want occurrences automatically generated after DDR extraction completes and accessible via API,
So that the occurrence table is ready to view as soon as processing finishes.

**Acceptance Criteria:**

**Given** a DDR's extraction pipeline finishes (all `ddr_dates` processed)
**When** the pipeline orchestrator triggers occurrence generation
**Then** `occurrence/classify` → `occurrence/infer_mmd` → `occurrence/density_join` → `occurrence/dedup` run in sequence over all successful `ddr_dates.final_json` records
**And** resulting occurrence rows are written to the `occurrences` table with all fields populated
**And** `ddrs.status` is updated to `"complete"` after occurrences are stored

**Given** failed `ddr_dates` rows exist in the same DDR
**When** occurrence generation runs
**Then** failed dates are skipped — occurrences generated only from successful dates
**And** failed dates remain flagged in `ddr_dates` — not silently omitted (FR30, NFR-R2)

**Given** `GET /ddrs/:id/occurrences` is called with a valid DDR id
**When** occurrences exist
**Then** HTTP 200 returns list: `[ { id, ddr_id, well_name, surface_location, type, section, mmd, density, notes, date }, ... ]`
**And** response time < 500ms for up to 100 rows (NFR-P3)
**And** supports query params `?type=`, `?section=`, `?date_from=`, `?date_to=` for server-side filtering (FR11)

**Given** `GET /ddrs/:id/occurrences` is called for a DDR with no occurrences yet
**When** extraction is still in progress or failed entirely
**Then** HTTP 200 returns empty array `[]`

### Story 3.5: OccurrenceTable UI — Full Frontend Component

As a CES staff member,
I want to view the structured occurrence table for any DDR with type badges, failed date indicators, and column filters,
So that I can scan all occurrences at a glance and immediately identify rows needing review.

**Acceptance Criteria:**

**Given** `ReportDetailPage.tsx` loads for a processed DDR
**When** `useOccurrences` hook fetches `/ddrs/:id/occurrences`
**Then** `OccurrenceTable` renders within 500ms for up to 100 rows (NFR-P3)
**And** skeleton loading state (5 rows × 4 columns grey bars) shows during fetch (UX-DR24)
**And** table columns: Well Name | Surface Location | Type | Section | mMD | Density | Notes
**And** sticky header is visible when scrolling vertically

**Given** `OccurrenceTable` renders occurrence rows
**When** a user inspects type and section values
**Then** `TypeBadge` maps each type to its `TYPE_COLOURS` color — 15–17 distinct badge colors (UX-DR2)
**And** `SectionBadge` uses emerald-600 for Surface, sky-600 for Int., indigo-600 for Main (UX-DR2)
**And** each badge has `aria-label` attribute — not color-only (UX-DR21)

**Given** a DDR has failed date extractions
**When** `OccurrenceTable` renders
**Then** `FailedDateRow` shows failed dates inline: red-50 background + `#C41230` left border 4px (UX-DR15)
**And** each failed row displays specific error reason inline — not only in a log view (FR30)
**And** failed date rows are not silently omitted from counts or view (NFR-R2)

**Given** `CollapsibleSidebar` renders at viewport ≥ 1280px
**When** sidebar state is checked
**Then** sidebar defaults to 220px expanded (icon + label per nav item)
**And** chevron toggle collapses to 48px icon-only
**And** state persists in `localStorage` key `ces-sidebar-collapsed` (UX-DR7)
**And** active nav item shows `#FEF2F2` bg + `#C41230` left border 3px + red label (UX-DR11)

**Given** column-level filter dropdowns and global text search are visible above table
**When** a user applies a filter (Type, Section, or free text)
**Then** table updates within 300ms (debounced) without full-page reload (UX-DR17)
**And** active filter shown as pill chip with × to remove
**And** filter state preserved in URL query params — shareable and back-navigable
**And** default sort is Date descending; column header click cycles ascending → descending → unsorted (UX-DR18)

**Given** no occurrences exist for the DDR
**When** `OccurrenceTable` renders
**Then** empty state shows: icon + "No occurrences found for this DDR" (UX-DR25)

**Given** `OccurrenceTable` is rendered
**When** keyboard navigation is used
**Then** Arrow keys navigate between cells, Tab moves to next cell (UX-DR5)
**And** table has `role="grid"` with `aria-rowcount` (UX-DR5, UX-DR21)
**And** skip-to-main-content link is present in root layout (UX-DR19)

---

## Epic 4: Inline Editing & Correction Store

Users can correct any occurrence field inline — reason captured, stored with full metadata, reviewed in a dashboard, and automatically summarized into future extraction prompts so the same mistake doesn't repeat.

### Story 4.1: Corrections Database Schema

As a platform developer,
I want the corrections table created via migrations on the Python backend,
So that every occurrence edit can be durably stored with full metadata in an append-only audit trail.

**Acceptance Criteria:**

**Given** migration `004_corrections` runs on the Python backend
**When** schema is inspected
**Then** `corrections` table exists: `id UUID PK`, `occurrence_id UUID REFERENCES occurrences(id)`, `ddr_id UUID REFERENCES ddrs(id)`, `field_name VARCHAR(100) NOT NULL`, `original_value TEXT NOT NULL`, `corrected_value TEXT NOT NULL`, `reason TEXT NOT NULL`, `user_id UUID REFERENCES users(id)`, `created_at TIMESTAMPTZ NOT NULL`
**And** indexes `idx_corrections_ddr_id` and `idx_corrections_occurrence_id` are created
**And** `corrections` table has no `updated_at` — append-only, never updated or deleted
**And** Alembic is the sole migration source for this schema
**And** `Alembic migrations` updated to include corrections table

### Story 4.2: Occurrence Edit API & Correction Store Write

As a CES staff member,
I want to edit any field of an occurrence row and have my correction stored with full metadata,
So that every change is auditable and the system knows what was corrected, why, and by whom.

**Acceptance Criteria:**

**Given** an authenticated user sends `PATCH /occurrences/:id` with body `{ "field_name": "type", "corrected_value": "Back Ream", "reason": "Text said backreamed to free" }`
**When** the request is processed
**Then** the `occurrences` row is updated with the new field value
**And** a `corrections` row is inserted with: `occurrence_id`, `ddr_id`, `field_name`, `original_value` (read from row before update), `corrected_value`, `reason`, `user_id` (from JWT), `created_at`
**And** both occurrence update and correction insert are in a single transaction (NFR-I3)
**And** HTTP 200 returns the updated occurrence row

**Given** `PATCH /occurrences/:id` is called with a non-existent occurrence id
**When** the query finds no row
**Then** HTTP 404 is returned with `{ "error": "Occurrence not found", "code": "NOT_FOUND", "details": {} }`

**Given** `PATCH /occurrences/:id` is called with missing required fields (`field_name`, `corrected_value`, or `reason`)
**When** request body validation runs
**Then** HTTP 400 is returned with `{ "error": "...", "code": "VALIDATION_ERROR", "details": { "missing_fields": [...] } }`

**Given** both Python backend implement `PATCH /occurrences/:id`
**When** the same edit is sent to each
**Then** both produce identical `corrections` row structure and identical updated occurrence response

### Story 4.3: Correction Context Builder & Pipeline Injection

As a CES staff member,
I want previous corrections automatically injected as context into future DDR extractions,
So that the same misclassification is not repeated after it has been corrected once.

**Acceptance Criteria:**

**Given** the `corrections` table has entries
**When** `corrections/context_builder` runs before a new DDR extraction
**Then** the last 20 corrections are retrieved, ordered by `created_at` descending
**And** each correction is summarized as: `"Field '{field_name}': '{original_value}' corrected to '{corrected_value}' ({count} times). Reason: {most_recent_reason}"` — grouped by `(field_name, original_value, corrected_value)`
**And** if fewer than 20 corrections exist, all available corrections are used
**And** if no corrections exist, context string is empty — extraction proceeds without injection

**Given** corrections context string is built
**When** `pipeline/extract` sends the Gemini API call
**Then** corrections context is prepended to the extraction prompt as a "here's what was wrong last time" note
**And** context string is capped — never exceeds 20 summarized entries (ARCH-10)
**And** same cap and same summary format applied on both Python backend

**Given** `corrections/context_builder` test suite runs with 25 correction fixtures
**When** context is built
**Then** only 20 are injected — oldest 5 excluded
**And** same test passes on both Python backend

### Story 4.4: Correction Store Review API

As a CES staff member,
I want to view all stored corrections across all DDRs,
So that I can identify systemic misclassification patterns and decide which keyword rules to update.

**Acceptance Criteria:**

**Given** `GET /corrections` is called with a valid JWT
**When** corrections exist
**Then** HTTP 200 returns paginated response: `{ "items": [...], "total": N, "page": 1, "page_size": 50 }`
**And** each item includes: `id`, `occurrence_id`, `ddr_id`, `field_name`, `original_value`, `corrected_value`, `reason`, `created_at`
**And** sorted by `created_at` descending

**Given** `GET /corrections` is called with `?field_name=type`
**When** filter is applied
**Then** only corrections where `field_name = "type"` are returned

**Given** `GET /corrections` is called with `?ddr_id=<uuid>`
**When** filter is applied
**Then** only corrections for that specific DDR are returned

**Given** no corrections exist
**When** `GET /corrections` is called
**Then** HTTP 200 returns `{ "items": [], "total": 0, "page": 1, "page_size": 50 }`

### Story 4.5: Inline Edit UI & ReasonCaptureModal

As a CES staff member,
I want to click any cell in the occurrence table to edit it inline and capture my reason in a lightweight modal,
So that correcting a wrong classification takes under 5 seconds and leaves a clear audit trail.

**Acceptance Criteria:**

**Given** `OccurrenceTable` renders occurrence rows
**When** a user single-clicks an editable cell (Type, Section, mMD, Density, Notes)
**Then** cell enters edit mode immediately — no double-click, no Edit button required
**And** for Type field: dropdown opens showing all approved types, filtered as user types
**And** for other fields: inline text input appears with current value pre-filled

**Given** user selects a new value from the Type dropdown or inputs a new value
**When** selection/input is confirmed
**Then** `ReasonCaptureModal` appears anchored below or above the edited row (whichever has more screen space) — never center-screen (UX-DR6)
**And** modal shows pre-filled context: "Type: Ream → Back Ream" (original and corrected values as read-only labels)
**And** single text input with placeholder "Why was this changed?" receives auto-focus immediately
**And** no backdrop is rendered — rest of table remains visible

**Given** `ReasonCaptureModal` is open
**When** user types reason and presses Enter
**Then** `PATCH /occurrences/:id` is called with `{ field_name, corrected_value, reason }`
**And** modal closes instantly on API success
**And** amber dot (`#D97706`) appears on the corrected row immediately (UX-DR15)
**And** table scroll position is unchanged throughout the entire interaction
**And** toast notification appears bottom-right: "Correction saved — will inform future extractions" for 3 seconds (UX-DR14)

**Given** `ReasonCaptureModal` is open
**When** user presses Escape
**Then** modal closes with no change saved — occurrence value reverts to original
**And** focus returns to the triggering cell (UX-DR6)

**Given** a row has an amber edit dot
**When** a screen reader inspects it
**Then** dot element has `aria-label="Cell manually corrected"` (UX-DR20)
**And** column header "Edited" label supplements the amber dot (dual-encoding, UX-DR20)

**Given** `useCorrections` hook exists in `src/hooks/`
**When** a correction is saved
**Then** hook performs optimistic update — row shows new value immediately
**And** on API error, row reverts to original value with inline error message

---

## Epic 5: Data Export

Users can export per-DDR occurrences to .xlsx (with edit history sheet when corrections exist), export all DDRs to master occurrences_all.xlsx, and export time log data per well as CSV — all one click, no wizard.

### Story 5.1: Per-DDR Excel Export Backend

As a CES staff member,
I want to export all occurrences for a single DDR as a formatted .xlsx file with an edit history sheet when corrections exist,
So that I have a client-ready deliverable that is auditable and opens cleanly in Excel and LibreOffice.

**Acceptance Criteria:**

**Given** `GET /export/ddr/:id` is called with a valid JWT for a DDR with occurrences
**When** the export is generated
**Then** response is a streaming `.xlsx` download with `Content-Disposition: attachment; filename="<ddr_id>_occurrences.xlsx"`
**And** Sheet 1 named "Occurrences" with columns: Well Name | Surface Location | Type | Section | mMD | Density | Notes
**And** header row has dark background (`#111827`) with white text
**And** export completes within 30 seconds for a full DDR occurrence set (NFR-P6)
**And** file opens without errors in Excel 2016+ and LibreOffice Calc (NFR-I4)

**Given** the DDR has corrections in the `corrections` table
**When** the export is generated
**Then** Sheet 2 named "Edit History" is included with columns: Field | Original Value | Corrected Value | Reason | User | Timestamp | DDR Source
**And** if no corrections exist, Sheet 2 is omitted entirely

**Given** `GET /export/ddr/:id` is called for a non-existent DDR
**When** the query finds no row
**Then** HTTP 404 is returned with `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }`

**Given** the Python backend implements the export with `openpyxl`
**When** the same DDR is exported from each
**Then** both produce `.xlsx` files with identical column structure, header styling, and sheet names

### Story 5.2: Master Excel Export Backend

As a CES staff member,
I want to export all occurrences across all processed DDRs into a single occurrences_all.xlsx file,
So that I can share a comprehensive dataset with clients or analyze patterns across jobs.

**Acceptance Criteria:**

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
**Then** response starts streaming within 5 seconds — not buffered in full before sending

### Story 5.3: Time Log CSV Export Backend

As a CES staff member,
I want to export structured time log data for any processed well as a CSV file,
So that I can analyze ROP, depth, and event data in Excel without opening the source PDF.

**Acceptance Criteria:**

**Given** `GET /export/timelogs/:well_id` is called with a valid JWT
**When** time log data exists for that well
**Then** response is a streaming CSV download named `<well_id>_timelogs.csv`
**And** CSV columns: date | time_from | time_to | code | details | depth
**And** sorted by `date` ascending, then `time_from` ascending

**Given** `GET /export/timelogs/:well_id` is called for a well with no processed data
**When** no matching records exist
**Then** HTTP 404 is returned with `{ "error": "Well data not found", "code": "NOT_FOUND", "details": {} }`

**Given** CSV is opened in Excel
**When** file encoding is inspected
**Then** file is UTF-8 with BOM — Excel opens without encoding dialog on Windows

### Story 5.4: Export UI — One-Click Download Flow

As a CES staff member,
I want export buttons available directly on the occurrence table, history page, and well history view,
So that I can download a formatted file in one click from wherever I am without navigating away.

**Acceptance Criteria:**

**Given** `ReportDetailPage.tsx` shows a processed DDR's occurrences
**When** user inspects the page
**Then** "Export .xlsx" secondary button (`border-[--ces-red] text-[--ces-red]`) is visible above the table (UX-DR13)
**And** single click triggers `GET /export/ddr/:id` via `api.ts` and initiates browser download

**Given** the export button is clicked
**When** the request is in-flight
**Then** button shows spinner + "Preparing export…" and is disabled (UX-DR24)
**And** button width is fixed — no layout shift

**Given** export request completes successfully
**When** the file is received
**Then** browser download initiates with correct filename
**And** success toast: "Export ready — file downloading" for 3 seconds (UX-DR14)
**And** button returns to normal state

**Given** `HistoryPage.tsx` shows cross-DDR filtered occurrences
**When** user clicks "Export .xlsx"
**Then** `GET /export/master` is called with current active filter params
**And** downloaded file reflects only filtered results

**Given** well history view shows time log data
**When** user clicks "Export CSV"
**Then** `GET /export/timelogs/:well_id` is called and CSV downloads
**And** same loading state and toast pattern applies

**Given** export request fails
**When** error response is received
**Then** error toast: "Export failed — please try again" with manual dismiss (UX-DR14 error pattern)
**And** button returns to normal state

---

## Epic 6: Query & Well History

Users can search all DDR data using natural language (BM25 + Qdrant vector, graceful degradation to BM25 if Qdrant unavailable), filter cross-DDR occurrence history, and access time log, deviation survey, and bit record data for any well.

### Story 6.1: BM25 Keyword Search Backend

As a CES staff member,
I want keyword-based search over time log and occurrence data,
So that natural language queries return relevant results even when Qdrant is unavailable.

**Acceptance Criteria:**

**Given** search service is implemented using Python `rank-bm25`
**When** `POST /occurrences/query` is called with `{ "query": "lost circulation events on ARC Resources" }`
**Then** BM25 ranks time log rows whose `details` text scores highest against the query
**And** results include: `ddr_id`, `date`, `time_from`, `time_to`, `code`, `details`, matched occurrence if any
**And** results ranked by BM25 score descending, max 50 results
**And** response time < 3 seconds end-to-end (NFR-P1)
**And** response includes `"search_mode": "bm25"`

**Given** query returns no matches above threshold
**When** BM25 search completes
**Then** HTTP 200 returns `{ "items": [], "total": 0, "search_mode": "bm25" }`

**Given** BM25 test suite runs against `ces-backend/tests/fixtures/`
**When** known queries are run
**Then** same ranked results returned on both Python backend

### Story 6.2: Qdrant Vector Search & NL Query API

As a CES staff member,
I want semantic vector search with automatic fallback to keyword search,
So that natural language queries find contextually relevant results even when wording doesn't match exactly.

**Acceptance Criteria:**

**Given** `search/qdrant` module queries the `ddr_time_logs` collection (populated by Epic 2 Story 2.6)
**When** `POST /occurrences/query` is called
**Then** query text is embedded using `text-embedding-004` (same Google AI API key)
**And** Qdrant returns top-K nearest vectors with metadata: `ddr_id`, `date`, `time_from`, `time_to`, `code`
**And** Qdrant results and BM25 results are merged and re-ranked by `search/query_handler`
**And** response includes `"search_mode": "vector+bm25"`
**And** total response time < 3 seconds end-to-end (NFR-P1)

**Given** Qdrant is unreachable
**When** `search/query_handler` detects the failure
**Then** query falls back to BM25-only automatically — no error returned to user (NFR-I2)
**And** response includes `"search_mode": "bm25"`
**And** fallback logged as `warn` level

**Given** `POST /occurrences/query` is called with additional filter params `?operator=&date_from=&date_to=`
**When** filters are present alongside the query
**Then** vector/BM25 results are filtered post-search by those params before returning
**And** filter params work independently — query can be empty (filter-only mode)

### Story 6.3: Cross-DDR Filter & Well History API

As a CES staff member,
I want to filter all occurrence history across every processed DDR and view time log, deviation, and bit record data for any well,
So that I can research offset wells and identify patterns without opening source PDFs.

**Acceptance Criteria:**

**Given** `GET /occurrences` is called with filter params `?well_name=`, `?area=`, `?operator=`, `?type=`, `?section=`, `?date_from=`, `?date_to=`
**When** the query runs
**Then** HTTP 200 returns paginated response: `{ "items": [...], "total": N, "page": 1, "page_size": 50 }` (FR22)
**And** each item includes all occurrence fields plus `ddr_id` and `ddr_source`
**And** params are combinable — multiple filters ANDed together

**Given** `GET /wells/:id/timelogs` is called
**When** time log data exists for that well
**Then** HTTP 200 returns all time log rows: `date`, `time_from`, `time_to`, `code`, `details`, `depth` sorted by date asc then time_from asc (FR23)

**Given** `GET /wells/:id/deviations` is called
**When** deviation survey data exists
**Then** HTTP 200 returns: `date`, `depth`, `inclination`, `azimuth` (FR24)

**Given** `GET /wells/:id/bits` is called
**When** bit record data exists
**Then** HTTP 200 returns: `date`, `bit_size`, `bit_run`, `depth_in`, `depth_out`, `hours` (FR25)

**Given** any well endpoint is called for a well with no data
**When** query returns no records
**Then** HTTP 200 returns empty array `[]` — not 404

### Story 6.4: Query & History UI

As a CES staff member,
I want a natural language query interface and cross-DDR history page with filters,
So that I can find any drilling event across all CES wells in seconds using plain English or structured filters.

**Acceptance Criteria:**

**Given** `QueryPage.tsx` loads at `/query`
**When** the page renders
**Then** `NLQueryBar` renders full-width with placeholder "Ask a question about your DDR data…" (UX-DR9)
**And** example query chips below input: e.g. "stuck pipe events on ARC Resources last quarter"
**And** clicking a chip populates the input and auto-submits
**And** last 5 queries accessible via ↑ key in the input

**Given** a user submits a query
**When** `POST /occurrences/query` is in-flight
**Then** spinner + "Searching…" replaces results area (UX-DR24)
**And** response arrives within 3 seconds (NFR-P1)

**Given** query returns results
**When** results render
**Then** `OccurrenceTable` component populates with matched rows
**And** active filter chips below the bar show what the query resolved to
**And** user can edit filter chips or type a new query to refine

**Given** query returns no results
**When** empty state renders
**Then** message: "No results found — try a different query" (UX-DR25)

**Given** `HistoryPage.tsx` loads at `/history`
**When** the page renders
**Then** filter sidebar always visible (no "open filter" button): Type checkboxes, Section, Date range, Well/Area/Operator inputs (UX-DR17)
**And** filter changes update the occurrence table within 300ms debounced
**And** filter state preserved in URL params

**Given** a well name is clicked in any occurrence row
**When** user navigates to well detail
**Then** tabs show: Time Logs | Deviation Surveys | Bit Records — each backed by the respective well API
**And** "Export CSV" on Time Logs tab triggers `GET /export/timelogs/:well_id`

---

## Epic 7: Pipeline Monitoring & System Administration

Users can monitor pipeline queue + AI costs, drill into per-date extraction status, view raw error logs, re-run failed dates with manual date override, and update keyword rules without a code deploy.

### Story 7.1: Pipeline Queue & Per-Date Status API

As a CES staff member,
I want to view the processing queue showing all DDR jobs and per-date extraction status for any DDR,
So that I can track what's running, what completed, and what needs attention at a glance.

**Acceptance Criteria:**

**Given** `GET /pipeline/queue` is called with a valid JWT
**When** DDR jobs exist
**Then** HTTP 200 returns list of all DDRs with: `id`, `file_path`, `status`, `well_name`, `created_at`, `date_counts` (`{ success, warning, failed, total }`) (FR26)
**And** sorted by `created_at` descending
**And** `date_counts` derived from aggregating `ddr_dates.status` per DDR

**Given** `GET /ddrs/:id/dates` is called
**When** ddr_dates rows exist for that DDR
**Then** HTTP 200 returns per-date list: `date`, `status`, `created_at` for each date chunk (FR27)
**And** sorted by `date` ascending

**Given** no DDRs are in the system
**When** `GET /pipeline/queue` is called
**Then** HTTP 200 returns empty array `[]`

### Story 7.2: Error Log & Per-Date Re-run API

As a CES staff member,
I want to view the raw error log for any failed date and re-run extraction with an optional manual date override,
So that extraction failures are diagnosable and recoverable without a code deploy.

**Acceptance Criteria:**

**Given** `GET /ddrs/:id/dates/:date` is called for a failed date
**When** the `ddr_dates` row exists
**Then** HTTP 200 returns: `date`, `status`, `error_log` (full JSONB including raw Gemini response excerpt and Pydantic errors), `raw_response` (full JSONB), `created_at` (FR28)

**Given** `POST /ddrs/:id/dates/:date/rerun` is called with body `{}`
**When** no override provided
**Then** extraction re-triggers for that specific date using the same PDF chunk (FR29)
**And** existing `ddr_dates` row status resets to `"queued"` before re-run begins
**And** HTTP 202 returned immediately — re-run is async

**Given** `POST /ddrs/:id/dates/:date/rerun` is called with `{ "manual_date_override": "20241031" }`
**When** manual override is provided
**Then** pipeline uses overridden date string instead of auto-detected boundary (FR29)
**And** manual override logged in `error_log` for audit trail

**Given** re-run completes successfully
**When** extraction and occurrence generation finish
**Then** `ddr_dates.status` updates to `"success"` and new occurrences are written
**And** SSE stream emits `date_complete` event if client still connected

**Given** `GET /ddrs/:id/dates/:date` is called for a non-existent date
**When** no matching row exists
**Then** HTTP 404 returned with `NOT_FOUND` error code

### Story 7.3: Keyword Management API

As a CES staff member,
I want to view and update keyword-to-type mappings via API without restarting the server,
So that I can fix systematic misclassification immediately after spotting a pattern in the correction store.

**Acceptance Criteria:**

**Given** `GET /keywords` is called with a valid JWT
**When** `ces-backend/src/resources/keywords.json` or equivalent backend resource module exists
**Then** HTTP 200 returns the full keyword map: `{ "<keyword>": "<type>", ... }` (FR32)

**Given** `PUT /keywords` is called with body `{ "<keyword>": "<type>", ... }`
**When** the new keyword map is valid JSON
**Then** `ces-backend/src/resources/keywords.json` or equivalent backend resource module is overwritten with new content (ARCH-9)
**And** in-memory keyword map on the Python backend reloads immediately — no restart required
**And** HTTP 200 returns the updated keyword map
**And** subsequent `occurrence/classify` calls use new mappings

**Given** `PUT /keywords` is called with malformed JSON
**When** body validation fails
**Then** HTTP 400 returned with `{ "error": "...", "code": "KEYWORD_UPDATE_FAILED", "details": {} }`
**And** existing `keywords.json` is not modified

**Given** same `GET /keywords` request sent to Python backend
**When** both respond
**Then** both return identical keyword map from the shared file (test coverage validation)

### Story 7.4: Monitor Dashboard & Keyword Editor UI

As a CES staff member,
I want a pipeline monitor dashboard with metric cards and queue view, plus a keyword editor page,
So that I can track pipeline health, diagnose failures, review corrections, and fix keyword rules from the UI.

**Acceptance Criteria:**

**Given** `MonitorPage.tsx` loads at `/monitor`
**When** the page renders
**Then** `MetricCard` components show: total DDRs processed, total occurrences, AI cost this week, failed date count, correction count (UX-DR10)
**And** values sourced from `GET /pipeline/queue`, `GET /corrections`, `GET /pipeline/cost`

**Given** MonitorPage loads the processing queue section
**When** DDR jobs exist
**Then** `ProcessingQueueRow` renders per DDR: status dot (green/amber/red/grey) + filename + date success/warning/failed counts + View link for complete DDRs (UX-DR8)
**And** in-progress DDR rows update live via SSE (`useProcessingStatus` hook)
**And** processing state shows "Processing date N of M…" — not a generic spinner (UX-DR16)

**Given** user clicks a failed date count on a `ProcessingQueueRow`
**When** the drill-down expands
**Then** per-date status list renders using `DateStatusIndicator` pills (success/warning/failed)
**And** failed dates show inline error summary from `error_log`
**And** "Re-run" button adjacent to each failed date triggers `POST /ddrs/:id/dates/:date/rerun`

**Given** correction store section on MonitorPage
**When** corrections exist
**Then** table shows: Field | Original | Corrected | DDR | Timestamp — sourced from `GET /corrections`
**And** `?field_name=type` filter chip pre-applied by default

**Given** `KeywordsPage.tsx` loads at `/settings/keywords`
**When** the page renders
**Then** table shows all keyword→type rows from `GET /keywords`
**And** each row is inline-editable (keyword and type columns)
**And** "Add row" button appends a new empty keyword→type row
**And** "Delete" icon removes a row with inline ghost confirm
**And** "Save" primary button calls `PUT /keywords` with full updated map
**And** success toast: "Keyword rules updated" for 3 seconds (UX-DR14)
**And** error response shows error toast with manual dismiss
