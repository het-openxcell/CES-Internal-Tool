# Story 2.5: SSE Processing Status Stream & Frontend Status Hook

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want real-time per-date extraction status streamed to my browser while a DDR processes,
so that I can see exactly which dates succeeded or failed without refreshing or navigating away.

## Acceptance Criteria

1. Given `GET /api/ddrs/{ddr_id}/status/stream` is called by an authenticated client, when the DDR is processing, then backend returns `Content-Type: text/event-stream` and streams named SSE events for that DDR only.
2. Given a date succeeds, when pipeline persistence marks the date successful, then SSE emits `date_complete` with `{ "date": "20241031", "status": "success", "occurrences_count": 3 }`; use `0` for `occurrences_count` until occurrence generation lands.
3. Given a date fails, when pipeline persistence marks the date failed, then SSE emits `date_failed` with `{ "date": "20241031", "error": "Tour Sheet Serial not detected", "raw_response_id": "<uuid>" }`; if no raw-response id exists yet, use the `ddr_dates.id`.
4. Given all dates finish, when DDR final status is computed, then SSE emits `processing_complete` with `{ "total_dates": 30, "failed_dates": 2, "warning_dates": 1, "total_occurrences": 0 }` and closes the stream.
5. Given backend restarts while DDRs are still queued or processing, when startup completes, then in-progress work is discovered from `processing_queue` and/or `ddrs.status in ("queued", "processing")` and dispatched through the same pipeline path instead of being silently lost.
6. Given `useProcessingStatus` exists in `ces-frontend/src/hooks/useProcessingStatus.ts`, when called with a DDR id, then it opens `EventSource` to `/api/ddrs/{ddr_id}/status/stream`, updates per-date status for `date_complete` and `date_failed`, closes on `processing_complete`, and cleans up on unmount or id change.
7. Given the SSE connection errors or closes before `processing_complete`, when the hook detects the failure, then it falls back to polling `GET /api/ddrs/{ddr_id}` every 3 seconds through the shared API client until processing reaches `complete` or `failed`.
8. Given `ReportsPage.tsx` renders a processing DDR, when live status updates arrive, then the page shows `Processing date N of M...`, per-date success/warning/failed counts, and no generic silent spinner.
9. Given upload is in progress on the reports surface, when the file is being submitted, then the upload progress bar replaces the drag-and-drop/upload zone.
10. Given processing completes with failures, when the final event or polling fallback sees completion, then a toast/status notification appears with `Processing complete - N dates extracted, M failed`.

## Tasks / Subtasks

- [ ] Add backend SSE event contracts and schemas (AC: 1-4)
  - [ ] Add Pydantic response/event payload models under `ces-ddr-platform/ces-backend/src/models/schemas/ddr.py`.
  - [ ] Keep exact event names: `date_complete`, `date_failed`, `processing_complete`.
  - [ ] Keep exact DDR status strings `queued | processing | complete | failed` and date status strings `queued | success | warning | failed`.
- [ ] Implement class-owned processing status stream service (AC: 1-4)
  - [ ] Create a service such as `ProcessingStatusStreamService` under `src/services/`.
  - [ ] Use `fastapi.responses.StreamingResponse` with an async generator and `media_type="text/event-stream"`.
  - [ ] Format SSE frames as `event: <name>\ndata: <json>\n\n`.
  - [ ] Include `Cache-Control: no-cache` and avoid buffering headers where practical.
  - [ ] Check client disconnects from the request object and release any per-client queue/subscription.
  - [ ] Do not create loose module-level mutable globals; encapsulate connection state in a service/manager attached through app state or dependency wiring.
- [ ] Add authenticated stream route (AC: 1)
  - [ ] Extend `ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py` with `GET /{ddr_id}/status/stream`.
  - [ ] Reuse `jwt_authentication`; unauthenticated stream requests must return existing auth errors.
  - [ ] Return 404 with `{ "error": "DDR not found", "code": "NOT_FOUND", "details": {} }` for unknown DDR ids.
  - [ ] Do not break existing `POST /api/ddrs/upload`, `GET /api/ddrs`, or `GET /api/ddrs/{ddr_id}` contracts.
- [ ] Emit events from the existing pipeline path (AC: 2-4)
  - [ ] Wire event publishing into `PreSplitPipelineService._process_one_date()` after repository writes complete.
  - [ ] Emit success for `mark_success`, failed for `mark_failed`, and treat warnings as completed date state while keeping warning count for final payload.
  - [ ] Emit `processing_complete` after `DDRCRUDRepository.finalize_status_from_dates()` computes parent status.
  - [ ] Do not fork a second pipeline or bypass `DDRDateCRUDRepository` / `DDRCRUDRepository`.
  - [ ] Verify Story 2.4 extraction is actually enabled in `DDRProcessingTask` or equivalent; current code has `extract_after_split=False` by default, so a pure SSE route without extraction events is incomplete.
- [ ] Add durable resume on startup (AC: 5)
  - [ ] Add a startup service using `src/config/events.py` and existing async DB session factory.
  - [ ] Query queued/processing DDRs and processing_queue rows through repository classes.
  - [ ] Dispatch the same `DDRProcessingTask.process(ddr_id)` path for resumable items.
  - [ ] Avoid duplicate concurrent processing for the same DDR within one process.
  - [ ] Leave queue deletion/completion behavior explicit; do not let completed queue rows cause endless reprocessing.
- [ ] Extend frontend API typing and EventSource URL support (AC: 6-7)
  - [ ] Add typed DDR detail/status types in `ces-ddr-platform/ces-frontend/src/lib/api.ts` or a local types module.
  - [ ] Add an API client method for `GET /ddrs/{id}` polling.
  - [ ] Add a safe way to build an authenticated SSE URL. Native `EventSource` cannot set custom `Authorization` headers, so either pass a token query parameter only if backend validates it safely, or use same-origin cookie/auth approach if already available. Do not pretend `EventSource` can send bearer headers.
  - [ ] Keep all normal fetch calls through `apiClient`; do not raw-fetch in components.
- [ ] Create `useProcessingStatus` hook (AC: 6-7)
  - [ ] Place it at `ces-ddr-platform/ces-frontend/src/hooks/useProcessingStatus.ts`.
  - [ ] Use `useEffect` cleanup to close `EventSource` and clear polling intervals on unmount/id change.
  - [ ] Use functional state updates for event-driven counts to avoid stale closures.
  - [ ] Use `addEventListener` for the three custom event names.
  - [ ] On SSE error before completion, close the stream and start 3-second polling through `apiClient`.
  - [ ] Expose state needed by pages: connection mode, DDR status, per-date rows, success/warning/failed counts, total dates, current processed count, final summary, and error state.
- [ ] Replace ReportsPage placeholder with upload/status UI (AC: 8-10)
  - [ ] Update `ces-ddr-platform/ces-frontend/src/pages/ReportsPage.tsx`.
  - [ ] Preserve protected routing and existing route path `/reports/:id`.
  - [ ] Show processing copy as `Processing date N of M...`.
  - [ ] Show success/warning/failed counts in compact, scannable status UI.
  - [ ] Provide a visible completion notification/status. If no toast system exists yet, implement a small page-local notification component instead of adding a large dependency.
  - [ ] Keep the user able to navigate away during processing; the hook must clean up and polling must not leak.
- [ ] Add focused tests (AC: 1-10)
  - [ ] Backend tests for auth required, 404, `text/event-stream`, event frame formatting, and final stream close.
  - [ ] Backend service tests proving events publish only after repository writes and warning/failure counts are correct.
  - [ ] Backend startup/resume tests using fake repositories/session factory; no real Gemini, Qdrant, or network.
  - [ ] Frontend tests for hook EventSource listeners, cleanup, fallback polling every 3 seconds, and final close.
  - [ ] Frontend tests for ReportsPage processing copy, counts, upload progress replacement, and completion failure notification.
  - [ ] Run backend `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/`.
  - [ ] Run frontend `npm test -- --runInBand` if supported or `npm test`, then `npm run build`, from `ces-ddr-platform/ces-frontend/`.
- [ ] Preserve non-story behavior (AC: all)
  - [ ] Do not change login/JWT contracts, existing upload/list/detail response bodies, Gemini extraction schema, PDF pre-split logic, occurrence generation, Qdrant, corrections, exports, or keyword management except where directly needed for status visibility.
  - [ ] Do not add source-file comments.

## Dev Notes

### Current Sprint State

Epic 2 is in progress. Story 2.3 and Story 2.4 are in review, not done, and the working tree contains their uncommitted backend pipeline changes. Treat those files as active project work: extend them carefully and do not revert them. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: git status --short]

Story 2.5 depends on the pipeline actually producing per-date extraction outcomes. Current code has `PreSplitPipelineService(extract_after_split=False)` by default in `DDRProcessingTask`, so a dev must verify Story 2.4 is wired before claiming this stream works. [Source: ces-ddr-platform/ces-backend/src/services/ddr.py] [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]

### Existing Backend State To Preserve

Backend root is `ces-ddr-platform/ces-backend/`. Existing DDR routes live in `src/api/routes/v1/ddr.py` with `/ddrs` router prefix and global `/api` prefix, so the external stream URL is `/api/ddrs/{ddr_id}/status/stream`. [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py] [Source: ces-ddr-platform/ces-backend/src/main.py]

Upload orchestration lives in `DDRUploadService` and dispatches `DDRProcessingTask.process()` via FastAPI `BackgroundTasks`. Keep upload acknowledgement fast; never run stream or extraction work inside the upload request path. [Source: ces-ddr-platform/ces-backend/src/services/ddr.py] [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

Pipeline orchestration lives in `src/services/pipeline_service.py`. It creates queued date rows, marks parent DDR processing, processes dates through `GeminiDDRExtractor` and `DDRExtractionValidator`, updates date rows through `DDRDateCRUDRepository`, then finalizes parent status through `DDRCRUDRepository.finalize_status_from_dates()`. Publish status events from this path instead of adding a parallel watcher that can drift from persistence. [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]

Repository methods already use epoch seconds through `int(time.time())`. New timestamps or response fields must stay epoch integers if added. [Source: AGENTS.md] [Source: ces-ddr-platform/ces-backend/src/repository/crud/ddr.py]

### Existing Frontend State To Preserve

Frontend root is `ces-ddr-platform/ces-frontend/`. Stack is React 19.2.5, React Router 7.15.0, Vite 8, TypeScript 6, Tailwind CSS 4. Current `ReportsPage.tsx` is only a placeholder; this story is the first real reports/status surface. [Source: ces-ddr-platform/ces-frontend/package.json] [Source: ces-ddr-platform/ces-frontend/src/pages/ReportsPage.tsx]

All normal HTTP calls must go through `src/lib/api.ts`, which injects bearer auth and handles 401 redirect. Extend it instead of raw fetch in pages/hooks. [Source: ces-ddr-platform/ces-frontend/src/lib/api.ts] [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]

Native `EventSource` only accepts URL/options and does not allow arbitrary request headers. Since current auth uses bearer tokens in `Authorization`, the dev must design stream auth explicitly. Acceptable options are: same-origin cookie/session if introduced intentionally, short-lived stream token issued by an authenticated API call, or a query token validated by backend with logging redaction. Do not implement `new EventSource(url, { headers: ... })`; it will not work. [Source: MDN EventSource docs]

### Architecture Compliance

Use Python-only FastAPI backend. No Go backend, no WebSocket, no Celery/Redis/message broker for this story. Architecture locks status transport to SSE with 3-second polling fallback. [Source: _bmad-output/planning-artifacts/architecture.md#Definitive Tech Stack] [Source: _bmad-output/planning-artifacts/architecture.md#Processing Status Transport]

Maintain route/dependency to service class to repository class flow. No loose variables/functions and no module-level mutable event bus. If shared runtime state is needed, encapsulate it in a class and attach it through application state or dependency wiring. [Source: AGENTS.md] [Source: _bmad-output/planning-artifacts/architecture.md#Backend Standards]

Use `asyncio.to_thread()` for sync SDK/file work. SSE generators and queue reads must not block the async event loop. [Source: AGENTS.md]

### SSE Protocol Guardrails

FastAPI `StreamingResponse` accepts async generators and streams yielded chunks. Long-lived generators need awaits so cancellation/disconnect can be handled. [Source: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse]

SSE responses must use `text/event-stream`; each event block ends with a blank line. Custom event names are consumed by `EventSource.addEventListener(eventName, handler)`. [Source: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events]

SSE is one-way server-to-client. Keep upload, retry, and polling as normal HTTP requests. Do not switch to WebSockets. [Source: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events] [Source: _bmad-output/planning-artifacts/prd.md#Technical Assumptions]

### React Hook Guardrails

`useProcessingStatus` is a synchronization hook with an external system, so `useEffect` is appropriate. Cleanup must close the `EventSource` and clear timers; React development can run setup/cleanup more than once. [Source: https://react.dev/reference/react/useEffect]

Polling fallback must guard against race conditions and stale updates after unmount. Use cleanup flags, `AbortController`, or equivalent patterns. [Source: https://react.dev/reference/react/useEffect]

### UX Requirements

Processing status must be specific and calm: `Processing date N of M...`, counts, and failed-date visibility. Avoid silent spinners. Users must be able to navigate away while processing continues. [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design Principles] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Loading States]

`ProcessingQueueRow` and future monitor views also depend on this hook, so keep the hook reusable and page-agnostic. [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Inventory] [Source: _bmad-output/planning-artifacts/epics.md#Story 7.4]

### Previous Story Intelligence

Story 2.1 established DDR tables, status constants, repositories, and epoch timestamp rules. Reuse `DDRStatus` and `DDRDateStatus`; do not scatter raw strings. [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]

Story 2.2 established upload route contracts, queue insertion, and background dispatch. Review notes flagged queue concurrency risks; this story must not add duplicate background workers for one DDR. [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]

Story 2.3 created the pre-splitter under `src/services/pipeline/pre_split.py`, not the originally planned `src/pipeline/` path. Continue the implemented layout. Do not create another splitter or pipeline package. [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]

Story 2.4 created extraction under `src/services/pipeline/extract.py` and validation under `src/services/pipeline/validate.py`. It also added repository methods `mark_success`, `mark_failed`, and `mark_warning`; publish events after those methods succeed. [Source: _bmad-output/implementation-artifacts/stories/2-4-per-date-gemini-extraction-pydantic-validation.md]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py
ces-ddr-platform/ces-backend/src/config/events.py
ces-ddr-platform/ces-backend/src/models/schemas/ddr.py
ces-ddr-platform/ces-backend/src/repository/crud/ddr.py
ces-ddr-platform/ces-backend/src/services/ddr.py
ces-ddr-platform/ces-backend/src/services/pipeline_service.py
ces-ddr-platform/ces-backend/src/services/processing_status.py
ces-ddr-platform/ces-backend/tests/test_ddr_status_stream.py
ces-ddr-platform/ces-backend/tests/test_ddr_processing_resume.py
ces-ddr-platform/ces-frontend/src/lib/api.ts
ces-ddr-platform/ces-frontend/src/hooks/useProcessingStatus.ts
ces-ddr-platform/ces-frontend/src/hooks/useProcessingStatus.test.tsx
ces-ddr-platform/ces-frontend/src/pages/ReportsPage.tsx
ces-ddr-platform/ces-frontend/src/pages/ReportsPage.test.tsx
ces-ddr-platform/ces-frontend/src/styles.css
```

Adjust names only to match existing local patterns. Do not modify `src/components/ui/` primitives directly. [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]

### Testing Requirements

Backend tests must run from `ces-ddr-platform/ces-backend/`:

```bash
source .venv/bin/activate
ruff check .
pytest
```

Frontend tests/build must run from `ces-ddr-platform/ces-frontend/`:

```bash
npm test
npm run build
```

Tests must not require real Gemini, Qdrant, uploaded PDFs, network calls, or real `.env` secrets. Fake EventSource in Vitest and fake backend queues/repositories in pytest. [Source: AGENTS.md] [Source: ces-ddr-platform/ces-frontend/src/lib/api.test.ts]

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5]
- [Source: _bmad-output/planning-artifacts/prd.md#Functional Requirements]
- [Source: _bmad-output/planning-artifacts/prd.md#Technical Assumptions]
- [Source: _bmad-output/planning-artifacts/architecture.md#Processing Status Transport]
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Loading States]
- [Source: _bmad-output/implementation-artifacts/stories/2-1-ddr-pipeline-database-schema.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-2-pdf-upload-endpoint-processing-queue.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-3-pdf-pre-splitter-date-boundary-detection.md]
- [Source: _bmad-output/implementation-artifacts/stories/2-4-per-date-gemini-extraction-pydantic-validation.md]
- [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/ddr.py]
- [Source: ces-ddr-platform/ces-backend/src/services/pipeline_service.py]
- [Source: ces-ddr-platform/ces-frontend/src/lib/api.ts]
- [Source: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse]
- [Source: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events]
- [Source: https://react.dev/reference/react/useEffect]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
