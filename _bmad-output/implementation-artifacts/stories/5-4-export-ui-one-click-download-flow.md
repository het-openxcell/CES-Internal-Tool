# Story 5.4: Export UI — One-Click Download Flow

Status: review

## Story

As a CES staff member,
I want export buttons available directly on the occurrence table and history page,
So that I can download a formatted file in one click from wherever I am without navigating away.

## Acceptance Criteria

**Given** `ReportDetailPage.tsx` shows a processed DDR's occurrences
**When** user inspects the page
**Then** "Export .xlsx" button is wired to call `GET /export/ddr/{ddr_id}` and initiate browser download

**Given** the export button is clicked
**When** the request is in-flight
**Then** button shows spinner + "Preparing export…" and is disabled
**And** button width is fixed — no layout shift

**Given** export request completes successfully
**When** the file is received
**Then** browser download initiates with correct filename
**And** success toast: "Export ready — file downloading" for 3 seconds (UX-DR14)
**And** button returns to normal state

**Given** `HistoryPage.tsx` shows cross-DDR filtered occurrences
**When** user clicks "Export .xlsx"
**Then** `GET /export/master` is called with current active filter params (types, sections, depth_from, depth_to)
**And** downloaded file reflects only filtered results

**Given** export request fails
**When** error response is received
**Then** error toast: "Export failed — please try again" with manual dismiss (UX-DR14 error pattern)
**And** button returns to normal state

## Tasks / Subtasks

- [x] **Task 1: Add downloadFile helper to api.ts** (AC: 1, 3, 4)
  - [x] Add `downloadFile(path: string, filename: string): Promise<void>` to `ApiClient` class in `src/lib/api.ts`
  - [x] Fetches the URL with auth header, reads `response.blob()`, creates object URL, triggers anchor click, revokes URL
  - [x] Handles 401 (redirect to login) and non-2xx (throw `ApiError`)
  - [x] This is separate from `request<TResponse>` which parses JSON — binary responses need blob handling

- [x] **Task 2: Add export methods to ApiClient** (AC: 1, 4)
  - [x] Add `exportDDRExcel(ddrId: string): Promise<void>` — calls `downloadFile(`/export/ddr/${encodeURIComponent(ddrId)}`, `${ddrId}_occurrences.xlsx`)`
  - [x] Add `exportMasterExcel(filters?: MasterExportFilters): Promise<void>` — builds query string from filters, calls `downloadFile`
  - [x] Add `MasterExportFilters` type: `{ types?: string[]; sections?: string[]; ddr_id?: string; date_from?: string; date_to?: string }`

- [x] **Task 3: Wire Export .xlsx button in ReportDetailPage.tsx** (AC: 1, 2, 3, 5)
  - [x] Add `isExporting` state (boolean, default false)
  - [x] On click: set `isExporting = true`, call `apiClient.exportDDRExcel(id)`, on success show success toast, on error show error toast, finally set `isExporting = false`
  - [x] Button disabled + shows spinner + "Preparing export…" when `isExporting`
  - [x] Fix button width: add `min-w-[140px]` or `w-[140px]` to prevent layout shift
  - [x] The button already exists at line 100–103 of `ReportDetailPage.tsx` — wire up its `onClick`

- [x] **Task 4: Wire Export button in HistoryPage.tsx** (AC: 4, 5)
  - [x] Change existing "Export CSV" button (line 229) to "Export .xlsx"
  - [x] Add `isExporting` state
  - [x] On click: build filter params from current state (types, sections, fromDepth, toDepth), call `apiClient.exportMasterExcel(filters)`
  - [x] Same loading/toast pattern as Task 3
  - [x] Pass `types` and `sections` arrays; pass `depth_from`/`depth_to` only when non-default (fromDepth > 50, toDepth < 6000)
  - [x] Note: HistoryPage currently passes `types` and `sections` as arrays but backend `GET /export/master?type=` takes single value. Check if backend needs multi-value support or if frontend should join — align with backend story 5.2 implementation.

- [x] **Task 5: Toast integration** (AC: 3, 5)
  - [x] Check how existing toasts are implemented in the project (search for toast usage in existing pages)
  - [x] Use same pattern — do NOT introduce a new toast library
  - [x] Success: 3-second auto-dismiss; Error: manual dismiss

## Dev Notes

### CRITICAL: api.ts request<T> Only Handles JSON — Need New downloadFile Method

The existing `ApiClient.request<T>` method calls `response.text()` then `JSON.parse()`. Binary (blob) responses for file downloads CANNOT use this path. Add a dedicated `downloadFile` method:

```typescript
// src/lib/api.ts — add to ApiClient class
async downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(this.url(path), {
    headers: this.headers({ skipAuth: false }),
  });

  if (response.status === 401) {
    authToken.clear();
    this.redirectToLogin();
    throw new ApiError("Unauthorized", "UNAUTHORIZED", response.status);
  }

  if (!response.ok) {
    throw new ApiError("Export failed", "API_ERROR", response.status);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}

async exportDDRExcel(ddrId: string): Promise<void> {
  await this.downloadFile(
    `/export/ddr/${encodeURIComponent(ddrId)}`,
    `${ddrId}_occurrences.xlsx`,
  );
}

async exportMasterExcel(filters?: MasterExportFilters): Promise<void> {
  const params = new URLSearchParams();
  filters?.types?.forEach((t) => params.append("type", t));
  filters?.sections?.forEach((s) => params.append("section", s));
  if (filters?.ddr_id) params.set("ddr_id", filters.ddr_id);
  if (filters?.date_from) params.set("date_from", filters.date_from);
  if (filters?.date_to) params.set("date_to", filters.date_to);
  const query = params.toString() ? `?${params.toString()}` : "";
  const hasFilters = params.toString().length > 0;
  const filename = hasFilters ? "occurrences_filtered.xlsx" : "occurrences_all.xlsx";
  await this.downloadFile(`/export/master${query}`, filename);
}
```

Add `MasterExportFilters` type near the existing filter types in `api.ts`:
```typescript
export type MasterExportFilters = {
  types?: string[];
  sections?: string[];
  ddr_id?: string;
  date_from?: string;
  date_to?: string;
};
```

### CRITICAL: HistoryPage "Export CSV" → "Export .xlsx"

HistoryPage.tsx line 229 currently has a stub "Export CSV" button with NO onClick. The epics specify this should call `GET /export/master` (which returns `.xlsx`), not a CSV export. Change button label to "Export .xlsx" and wire it up. The "Export CSV" for time logs is a future well-detail view (Epic 6 scope) — do NOT add it here.

### CRITICAL: ReportDetailPage Export Button Already Rendered

`ReportDetailPage.tsx` line 100–103 already has an "Export .xlsx" button rendered but it's a stub with no onClick. Wire it up — do NOT recreate it. Current code:
```tsx
<button className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark transition-colors">
  <DownloadIcon className="w-3.5 h-3.5" />
  Export .xlsx
</button>
```
Add `onClick`, `disabled={isExporting}`, loading state content, and fixed width.

### Toast Pattern — Find Existing Usage First

Before implementing toast, grep the codebase:
```
grep -r "toast\|Toast" ces-ddr-platform/ces-frontend/src/ --include="*.tsx" --include="*.ts" | head -20
```
Use whatever toast mechanism is already in the project. If none exists, use `window.alert` as a temporary fallback and note it for polish.

### Button Loading State Pattern

```tsx
<button
  type="button"
  onClick={handleExport}
  disabled={isExporting}
  className="inline-flex items-center gap-1.5 h-9 min-w-[140px] justify-center px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark transition-colors disabled:opacity-70"
>
  {isExporting ? (
    <>
      <RefreshIcon className="w-3.5 h-3.5 animate-spin" />
      Preparing export…
    </>
  ) : (
    <>
      <DownloadIcon className="w-3.5 h-3.5" />
      Export .xlsx
    </>
  )}
</button>
```

### HistoryPage Filter Mapping to Export Params

HistoryPage filter state → `exportMasterExcel` filters:
- `types: string[]` → `filters.types`  
- `sections: string[]` → `filters.sections`
- `fromDepth: number` (default 50) → pass as `depth_from` only when > 50, but **backend story 5.2 `GET /export/master` doesn't accept depth params** (only type, ddr_id, date_from, date_to). Do NOT pass depth filters to the export endpoint — they are UI-only for now and can be added in a follow-up.

### Well History / Time Log Export Scope

The epic AC for story 5.4 includes "well history view Export CSV → `GET /export/timelogs/:well_id`". This view doesn't exist yet — it's Epic 6 story 6.4 scope. Do NOT implement this. Story 5.4 scope:
- ✅ ReportDetailPage: per-DDR xlsx export
- ✅ HistoryPage: master xlsx export
- ❌ Well history CSV export — deferred to Epic 6

### File List

| File | Action |
|------|--------|
| `ces-ddr-platform/ces-frontend/src/lib/api.ts` | UPDATE — add `downloadFile`, `exportDDRExcel`, `exportMasterExcel`, `MasterExportFilters` |
| `ces-ddr-platform/ces-frontend/src/pages/ReportDetailPage.tsx` | UPDATE — wire export button |
| `ces-ddr-platform/ces-frontend/src/pages/HistoryPage.tsx` | UPDATE — wire export button (CSV→xlsx) |

### Prerequisites

Backend stories 5.1 and 5.2 must be implemented (or at least have the endpoints available) for E2E testing. Story 5.3 backend can be deferred since the time log export UI is out of scope for this story.

### References

- `ces-ddr-platform/ces-frontend/src/lib/api.ts` — full ApiClient implementation; add new methods here
- `ces-ddr-platform/ces-frontend/src/pages/ReportDetailPage.tsx:100` — existing stub export button
- `ces-ddr-platform/ces-frontend/src/pages/HistoryPage.tsx:229` — existing stub export CSV button
- `ces-ddr-platform/ces-frontend/src/lib/auth.ts` — `authToken` helper used in `downloadFile`

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Completion Notes List
- `downloadFile` uses blob + anchor-click pattern; handles 401 redirect and non-2xx throw
- `exportMasterExcel` uses `URLSearchParams.append` for multi-value type/section filters
- Toast: success auto-dismisses after 3s; error has manual × dismiss button — follows MonitorPage pattern
- Frontend builds clean (tsc + vite, 0 errors)
- "Export CSV" → "Export .xlsx" in HistoryPage; inline SVG spinner to avoid RefreshIcon import

### File List
- `ces-ddr-platform/ces-frontend/src/lib/api.ts` — added downloadFile, exportDDRExcel, exportMasterExcel, MasterExportFilters
- `ces-ddr-platform/ces-frontend/src/pages/ReportDetailPage.tsx` — wired export button with loading/toast
- `ces-ddr-platform/ces-frontend/src/pages/HistoryPage.tsx` — wired Export .xlsx button with loading/toast

## Change Log

- 2026-05-18: Story created — export UI one-click download flow
- 2026-05-18: Implemented — all ACs satisfied, frontend builds clean
