# Deferred Work

## Deferred from: code review of 3-4-occurrence-generation-api-pipeline-integration (2026-05-11)

- **W4: `infer_mmd` backward scan can return stale same-day depth** — If a time log entry has no `depth_md`, the backward scan returns the last known depth from earlier in the same day. This is intentional algorithm design but can produce an MMD that is hours stale. Requires rethinking the algorithm (e.g., max-lookback limit, or requiring depth on classified entries) before changing. Pre-existing in `infer_mmd.py`.
- **W5: No DDR ownership authorization** — Any authenticated user can read any DDR's occurrences (and other DDR data) by ID. The `DDR` model has no `user_id`/`created_by` column — cannot add ownership checks without a DB schema migration and user-DDR association story. Single-tenant internal tool for now; revisit when multi-user isolation is required.

## Deferred from: code review of 3-5-occurrencetable-ui-full-frontend-component (2026-05-11)

- **W6: `redirectToLogin` in `ApiClient` uses `window.history.pushState` + `PopStateEvent` instead of React Router `navigate`** — Bypasses React Router's internal history state, which can leave router `location` and `window.location` diverged. Safe for current single-page redirects but should be replaced with a React-boundary interceptor pattern (event bus or error boundary with `useNavigate`) when the codebase grows. Pre-existing in `api.ts`.
- **W7: `getOccurrences` return type is `OccurrenceRow[] | undefined` at runtime but typed as `OccurrenceRow[]`** — The `request<T>` method returns `undefined as T` on 204 / empty body. Currently guarded with `?? []` in `useOccurrences`. Should be fixed at the source by typing `request<T>` as `Promise<T | undefined>`. Low risk given current call sites.
