# Story 7.4: Monitor Dashboard & Keyword Editor UI

Status: ready-for-dev

## Story

As a CES staff member,
I want a pipeline monitor dashboard with metric cards and queue view, plus a keyword editor page,
so that I can track pipeline health, diagnose failures, review corrections, and fix keyword rules from the UI.

## Acceptance Criteria

1. Given `MonitorPage.tsx` loads at `/monitor`, then metric cards show: DDRs processed, occurrences extracted, AI cost (weekly), failed date count, corrections count — values sourced from `/monitor/metrics` (unchanged endpoint).
2. Given MonitorPage loads the processing queue section, then it calls `GET /api/pipeline/queue` (Story 7-1 endpoint, nested `date_counts` shape) — NOT the old `/monitor/queue`. Existing backend `/monitor/queue` remains for backward compatibility but MonitorPage switches to the new endpoint.
3. Given DDR jobs exist in the queue, then each row renders: status dot + filename + `date_counts.success/warning/failed` + "View" link for complete DDRs. In-progress rows show "Processing date N of M…" progress bar.
4. Given user clicks on a failed date count badge on a queue row, then a per-date drill-down panel expands beneath the row showing each date's status as a pill (success/warning/failed). Failed dates show an inline error summary (first `error_log` key/value) and a "Re-run" button.
5. Given user clicks "Re-run" on a failed date, then `POST /api/ddrs/{id}/dates/{date}/rerun` is called with empty body `{}`. The button shows a loading state and the date pill updates optimistically or after refresh.
6. Given correction store section, then table shows field, original, corrected, DDR id, timestamp — sourced from `/monitor/corrections` (existing endpoint, unchanged).
7. Given `KeywordsPage.tsx` loads at `/settings/keywords`, then the existing grouped keyword editor renders (already implemented). The "Save" button calls `PUT /api/keywords` and handles the new full-map response (not `{ updated: N }`). Success toast shows "Keyword rules updated". Error response shows error toast.
8. Given OpenAPI and existing API contracts: `/monitor/metrics`, `/monitor/corrections`, `/monitor/queue` (old), `/pipeline/cost` remain untouched. Only MonitorPage's data source for the queue section changes.

## Tasks / Subtasks

- [ ] Add `PipelineQueueItem` type and `getPipelineQueue()` to `api.ts` (AC: 2)
  - [ ] In `ces-frontend/src/lib/api.ts`, add type:
    ```ts
    export type PipelineQueueItem = {
      id: string;
      file_path: string;
      status: DDRStatus;
      well_name?: string | null;
      created_at: number;
      date_counts: { success: number; warning: number; failed: number; total: number };
    };
    ```
  - [ ] Add method `getPipelineQueue()` that calls `GET /api/pipeline/queue` (new 7-1 endpoint): `return this.request<PipelineQueueItem[]>("/pipeline/queue")`.
  - [ ] Add method `getDDRDateStatuses(ddrId: string)` → `GET /api/ddrs/{id}/dates` (7-1 endpoint, lean list): returns `DDRDateListItem[]` typed as `{ date: string; status: DDRDateStatus; created_at: number }[]`.
  - [ ] Add method `rerunDate(ddrId: string, date: string, manualDateOverride?: string)` → `POST /api/ddrs/{id}/dates/{date}/rerun` with body `{ manual_date_override: manualDateOverride ?? undefined }`.
  - [ ] Add method `getDDRDateDetail(ddrId: string, date: string)` → `GET /api/ddrs/{id}/dates/{date}` (7-2 endpoint), returns `DDRDateDetail` (type already exists in api.ts with `error_log`).
  - [ ] Do NOT remove `getMonitorQueue()`, `QueueItem`, or `retryDate()` — still used by other code.
- [ ] Migrate MonitorPage queue data source from `/monitor/queue` to `/pipeline/queue` (AC: 2, 3)
  - [ ] In `MonitorPage.tsx`, replace `apiClient.getMonitorQueue()` call with `apiClient.getPipelineQueue()`.
  - [ ] Replace `QueueItem` state type with `PipelineQueueItem`.
  - [ ] Update `PipelineQueue` sub-component signature to accept `PipelineQueueItem[]` instead of `QueueItem[]`.
  - [ ] Update field references: `q.date_counts.success/warning/failed/total` instead of `q.date_success/date_warning/date_failed/date_total`. `q.operator` and `q.area` no longer available from this endpoint — use `q.well_name ?? q.file_path.split("/").pop()` for display name.
  - [ ] Keep `getDisplayStatus()` logic — adapt to `date_counts` fields.
  - [ ] Keep all existing UI structure (StatusDot, StatusPill, progress bar, "View" link) — only data source changes.
- [ ] Add per-date drill-down panel to ProcessingQueueRow (AC: 4, 5)
  - [ ] In `MonitorPage.tsx`, add expand state per DDR row: `const [expandedId, setExpandedId] = useState<string | null>(null)`.
  - [ ] Failed date count badge becomes a clickable button that toggles `expandedId`.
  - [ ] When `expandedId === q.id`, render a `DateDrillDown` sub-component beneath the row in the table.
  - [ ] `DateDrillDown` component:
    - Calls `apiClient.getDDRDateStatuses(ddrId)` on mount.
    - Renders per-date status pills (success/warning/failed).
    - For failed dates: shows first `error_log` key/value as inline text.
    - Shows "Re-run" button adjacent to each failed date.
    - "Re-run" button calls `apiClient.rerunDate(ddrId, date)`, disables during call.
    - After rerun call completes, re-fetch date statuses or call parent's refresh.
  - [ ] To get error detail for failed dates: either include it in `getDDRDateStatuses` response (it already has `error_log` in `DDRDateDetail`) OR call `getDDRDateDetail(ddrId, date)` lazily per failed date. Prefer the lazy approach to avoid N+1 on expand — fetch error_log only for failed dates.
  - [ ] Do NOT remove existing "Re-run" button on `ReportDetailPage` — that uses `retryDate` on individual date rows. This is a separate UI location.
- [ ] Fix KeywordsPage to handle new PUT response (AC: 7)
  - [ ] In `KeywordsPage.tsx`, find where `apiClient.updateKeywords(...)` is called and its result is used.
  - [ ] The current return type will change (Story 7-3) from `{ updated: number }` to `Record<string, string>`. If the result is used to update local state, use the returned map directly to refresh the local keyword state.
  - [ ] If no result value is used (just side effect + toast), no change needed.
  - [ ] Verify success toast text is "Keyword rules updated" (3-second auto-dismiss).
  - [ ] Verify error response shows an error toast (manual dismiss).
  - [ ] Check existing toast implementation in KeywordsPage — if already present, just verify; if missing, add minimal toast state.
- [ ] Run frontend quality gates (AC: 8)
  - [ ] `cd ces-ddr-platform/ces-frontend && npm run build` — no TypeScript errors.
  - [ ] `cd ces-ddr-platform/ces-frontend && npm run test` if test suite exists.

## Dev Notes

### Critical Context

- Story 7-4 is frontend-only (plus minimal api.ts additions).
- Depends on Story 7-1 (`/pipeline/queue`, `/ddrs/{id}/dates`) and 7-2 (`/ddrs/{id}/dates/{date}`, `/ddrs/{id}/dates/{date}/rerun`) being implemented first.
- `MonitorPage.tsx` is 535 lines with significant existing implementation. Reuse everything; only change the queue data source and add the drill-down.
- `KeywordsPage.tsx` is already substantially implemented. Only verify/fix the PUT response handling.

### DO NOT REIMPLEMENT — Reuse These

| Existing thing | Where | How to use in 7-4 |
|---|---|---|
| `BigMetric` component | `MonitorPage.tsx` | Keep as-is; metrics still come from `/monitor/metrics` |
| `StatusDot`, `StatusPill` | `MonitorPage.tsx` | Reuse in drill-down date pills |
| `PipelineQueue` component | `MonitorPage.tsx` | Extend to use `PipelineQueueItem`; do NOT rewrite |
| `getDisplayStatus()` | `MonitorPage.tsx` | Keep; adapt to `date_counts` fields |
| `CorrectionStore` section | `MonitorPage.tsx` | Unchanged; still calls `/monitor/corrections` |
| `fmtTs()`, `fmtMoney()` | `MonitorPage.tsx` | Keep helpers |
| `Correction` type | `api.ts` | Unchanged |
| `QueueItem`, `getMonitorQueue()` | `api.ts` | Keep for backward compat; MonitorPage migrates away but don't delete |
| `retryDate()` | `api.ts` | Still used by ReportDetailPage — do NOT remove |
| `useRetryDate` hook | `src/hooks/useRetryDate.ts` | Used by ReportDetailPage; not needed in MonitorPage drill-down |
| `DDRDateDetail` type | `api.ts` | Already has `error_log` — use for drill-down detail |
| `KeywordsPage.tsx` grouped editor | `src/pages/KeywordsPage.tsx` | Already implemented; only fix PUT response handling |
| `groupKeywords()`, `flattenRules()` | `KeywordsPage.tsx` | Keep as-is |

### New `PipelineQueueItem` vs Existing `QueueItem`

`QueueItem` (old `/monitor/queue`):
```ts
{ id, file_path, well_name, operator, area, status, date_total, date_success, date_failed, date_warning, created_at, updated_at }
```

`PipelineQueueItem` (new `/pipeline/queue`):
```ts
{ id, file_path, well_name, status, created_at, date_counts: { success, warning, failed, total } }
```

In `PipelineQueue` component, replace `q.date_success` → `q.date_counts.success`, etc. Remove `operator`/`area` column (or hide with `q.well_name ?? file_path` fallback).

### DateDrillDown Component Pattern

```tsx
function DateDrillDown({ ddrId }: { ddrId: string }) {
  const [dates, setDates] = useState<DDRDateListItem[]>([]);
  const [rerunning, setRerunning] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getDDRDateStatuses(ddrId).then(setDates).catch(() => {});
  }, [ddrId]);

  async function handleRerun(date: string) {
    setRerunning(date);
    try {
      await apiClient.rerunDate(ddrId, date);
      const refreshed = await apiClient.getDDRDateStatuses(ddrId);
      setDates(refreshed);
    } finally {
      setRerunning(null);
    }
  }

  return (/* date pills, error summary, Re-run buttons */);
}
```

### Error Log Display

For failed dates in drill-down:
- Call `getDDRDateDetail(ddrId, date)` to get `error_log`.
- Display `error_log` as first key: value pair, e.g. `code: EXTRACTION_FAILED` or `reason: No date boundaries`.
- Keep it compact — single line of text, not raw JSON dump.
- Fetch lazily: call `getDDRDateDetail` only for dates with `status === "failed"` when drill-down opens.

### Toast for KeywordsPage

If `setToast` state already exists in `KeywordsPage.tsx` (check for `toast` state), just verify it's wired:
- Success: `setToast("Keyword rules updated")` after PUT succeeds, clear after 3 seconds.
- Error: `setToast("Failed to save keyword rules")` (or similar) with manual dismiss.

The page already has `const [toast, setToast] = useState<string | null>(null)` — verify toast renders and clears.

### Architecture Compliance

- No direct fetch/axios — all calls through `apiClient` methods.
- New `PipelineQueueItem` type defined in `api.ts`, not inline.
- No `border-l-*` decorative accents on cards (CLAUDE.md rule).
- All API calls through existing `apiClient.request<T>()` pattern.

### Regression Guardrails

- `getMonitorQueue()` and `QueueItem` type stay in `api.ts` — don't remove.
- `/monitor/metrics`, `/monitor/corrections`, `/monitor/queue` backend endpoints unchanged.
- `retryDate()` and `useRetryDate` hook unchanged — used by ReportDetailPage.
- `KeywordsPage.tsx` existing grouped editor structure unchanged — only fix response handling.
- `DDRDetailResponse` type (DDRDetail in api.ts) unchanged.
- Do NOT add `border-l-*` styling to any cards or status indicators.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md#Story-7.4`
- MonitorPage: `ces-ddr-platform/ces-frontend/src/pages/MonitorPage.tsx`
- KeywordsPage: `ces-ddr-platform/ces-frontend/src/pages/KeywordsPage.tsx`
- API client: `ces-ddr-platform/ces-frontend/src/lib/api.ts`
- useRetryDate hook: `ces-ddr-platform/ces-frontend/src/hooks/useRetryDate.ts`
- AppShell: `ces-ddr-platform/ces-frontend/src/components/AppShell.tsx`
- TopNav: `ces-ddr-platform/ces-frontend/src/components/TopNav.tsx`

## Story Context Completion

Ultimate context engine analysis completed — comprehensive developer guide focused on extending existing 535-line MonitorPage and existing KeywordsPage without reimplementation.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
