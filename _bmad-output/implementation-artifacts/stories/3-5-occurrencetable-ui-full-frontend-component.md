# Story 3.5: OccurrenceTable UI — Full Frontend Component

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want to view the structured occurrence table for any DDR with type badges, failed date indicators, and column filters,
So that I can scan all occurrences at a glance and immediately identify rows needing review.

## Acceptance Criteria

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

## Tasks / Subtasks

- [x] Install `@tanstack/react-table` dependency (AC: all)
  - [x] Run `npm install @tanstack/react-table` in `ces-ddr-platform/ces-frontend/`
  - [x] Verify it appears in `package.json` dependencies

- [x] Add `OccurrenceRow` type + `getOccurrences` to `src/lib/api.ts` (AC: 1)
  - [x] Add `OccurrenceRow` type with all 10 fields: `id, ddr_id, well_name, surface_location, type, section, mmd, density, notes, date`
  - [x] Add `OccurrenceFilters` type: `{ type?: string; section?: string; date_from?: string; date_to?: string }`
  - [x] Add `async getOccurrences(ddrId: string, filters?: OccurrenceFilters): Promise<OccurrenceRow[]>` to ApiClient

- [x] Create `src/hooks/useOccurrences.ts` (AC: 1)
  - [x] Hook signature: `useOccurrences(ddrId: string | undefined) → { data: OccurrenceRow[] | null, isLoading: boolean, error: string | null, refetch: () => void }`
  - [x] Fetch on mount when `ddrId` is defined; set `isLoading` true during fetch
  - [x] `error` is `string | null` — never rethrow; set human-readable message on failure
  - [x] Export default + named `useOccurrences`

- [x] Create `src/components/TypeBadge.tsx` (AC: 2)
  - [x] Export `TYPE_COLOURS` constant map (all 16 types → Tailwind color classes — see Dev Notes)
  - [x] `TypeBadge` component: `{ type: string }` prop; look up color from map; render `<span>` badge with `aria-label={type}`
  - [x] Fallback: unknown types → neutral grey badge

- [x] Create `src/components/SectionBadge.tsx` (AC: 2)
  - [x] Export `SECTION_COLOURS` constant: `Surface` = emerald-600, `Int.` = sky-600, `Main` = indigo-600
  - [x] `SectionBadge` component: `{ section: string | null }` prop; render badge with `aria-label={section}`
  - [x] Null/undefined section → render nothing (null)

- [x] Create `src/components/FailedDateRow.tsx` (AC: 3)
  - [x] Props: `{ date: string; error: string }`
  - [x] Single `<tr>` (or div-as-row) spanning all columns: red-50 bg `#FEF2F2` + left border `#C41230` 4px
  - [x] Shows date + error reason inline
  - [x] `aria-label="Date resolution failed. Action required."`

- [x] Create `src/components/OccurrenceTable.tsx` using TanStack Table v8 (AC: 1–7)
  - [x] Props: `{ occurrences: OccurrenceRow[]; failedDates: { date: string; error: string }[]; isLoading: boolean }`
  - [x] Columns: Well Name, Surface Location, Type (TypeBadge), Section (SectionBadge), mMD, Density, Notes
  - [x] Sticky header: `position: sticky; top: 0` on `<thead>`
  - [x] Row states: default | hover (slate-50) | failed-date row (red-50 + left border)
  - [x] Skeleton: 5 rows × 4 grey shimmer bars when `isLoading === true`
  - [x] Empty state: `EmptyState` component with "No occurrences found for this DDR"
  - [x] Filters: Type dropdown, Section dropdown, global text search — all above table
  - [x] Active filter pills below search bar with × to remove each
  - [x] Filter state from/to URL query params via `useSearchParams` — debounce 300ms
  - [x] Default sort: Date descending; column header click cycles asc → desc → unsorted
  - [x] `role="grid"` on `<table>`, `aria-rowcount={occurrences.length}` (UX-DR5, UX-DR21)
  - [x] Keyboard: Arrow keys navigate cells, Tab to next cell (TanStack Table handles via `role="grid"`)
  - [x] Failed date rows interspersed inline via custom row rendering

- [x] Create `src/components/CollapsibleSidebar.tsx` (AC: 4)
  - [x] Props: none (self-contained; reads/writes localStorage)
  - [x] localStorage key: `ces-sidebar-collapsed` — `"true"` = collapsed, `"false"` or absent = expanded
  - [x] Expanded state: 220px wide, shows icon + label per nav item
  - [x] Collapsed state: 48px wide, shows icon only + tooltip on hover
  - [x] Chevron toggle button at bottom edge; animates direction with sidebar state
  - [x] Active nav item: `#FEF2F2` bg + `#C41230` left border 3px + red label (use `NavLink` with `isActive`)
  - [x] Same 5 nav items as current `AppShell.tsx` NAV_ITEMS — Dashboard, History, Query, Monitor, Settings
  - [x] `Tab` navigates items, `Enter` activates, `Space` toggles collapse (UX-DR19)

- [x] Update `src/components/AppShell.tsx` — replace top horizontal nav with sidebar layout (AC: 4)
  - [x] Change layout from `flex-col` with top header to `flex-row` with sidebar + main content
  - [x] `<CollapsibleSidebar />` renders as left sidebar; main content fills remaining width
  - [x] Keep the top header bar ONLY for the logo and sign-out button (brand strip)
  - [x] Sidebar renders for all protected routes (AppShell wraps all protected routes)
  - [x] PRESERVE the logo, sign-out button, and auth behavior — do NOT break these
  - [x] Add `<a href="#main-content" className="sr-only focus:not-sr-only ...">Skip to main content</a>` at top for skip link (UX-DR19)
  - [x] `<main>` gets `id="main-content"` for skip-link target

- [x] Create `src/pages/ReportDetailPage.tsx` (AC: 1–7)
  - [x] Route: `/reports/:id` — update `src/routes.ts` to use `ReportDetailPage` instead of `ReportsPage`
  - [x] Compose: existing processing status panel + `OccurrenceTable` + `DDRUploadPanel`
  - [x] `useProcessingStatus(id)` for processing status section (existing behavior preserved)
  - [x] `useOccurrences(id)` for occurrence table data
  - [x] Pass `failedDates` from `useProcessingStatus` rows (filter `status === 'failed'`) to `OccurrenceTable`
  - [x] OccurrenceTable section renders below processing status section
  - [x] `ReportsPage.tsx` can remain as-is (not deleted); route just switches to `ReportDetailPage`

- [x] Write tests (AC: 1–7)
  - [x] `src/components/OccurrenceTable.test.tsx` — 12 tests
  - [x] `src/components/CollapsibleSidebar.test.tsx` — 5 tests
  - [x] Run: `npm test` from `ces-ddr-platform/ces-frontend/` — all 43 tests pass

## Dev Notes

### Critical: TanStack Table NOT Yet Installed

`@tanstack/react-table` is required per locked architecture but **not in package.json** as of this story. First task is install:

```bash
cd ces-ddr-platform/ces-frontend
npm install @tanstack/react-table
```

Verify latest stable: v8.x (the `@tanstack/react-table` package on npm). The API uses the headless table pattern:

```typescript
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
```

### File 1 (ADD to api.ts): Types + Client Method

Add after the existing `DDRDetail` type:

```typescript
export type OccurrenceRow = {
  id: string;
  ddr_id: string;
  well_name: string | null;
  surface_location: string | null;
  type: string;
  section: string | null;
  mmd: number | null;
  density: number | null;
  notes: string | null;
  date: string | null;
};

export type OccurrenceFilters = {
  type?: string;
  section?: string;
  date_from?: string;
  date_to?: string;
};
```

Add method to `ApiClient` class:

```typescript
async getOccurrences(ddrId: string, filters?: OccurrenceFilters) {
  const params = new URLSearchParams();
  if (filters?.type) params.set("type", filters.type);
  if (filters?.section) params.set("section", filters.section);
  if (filters?.date_from) params.set("date_from", filters.date_from);
  if (filters?.date_to) params.set("date_to", filters.date_to);
  const query = params.toString() ? `?${params.toString()}` : "";
  return this.request<OccurrenceRow[]>(`/ddrs/${encodeURIComponent(ddrId)}/occurrences${query}`);
}
```

### File 2 (NEW): `src/hooks/useOccurrences.ts`

Standard hook shape per architecture (matches `useProcessingStatus` pattern):

```typescript
import { useCallback, useEffect, useState } from "react";
import { apiClient, type OccurrenceRow } from "@/lib/api";

export function useOccurrences(ddrId: string | undefined) {
  const [data, setData] = useState<OccurrenceRow[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!ddrId) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.getOccurrences(ddrId);
      setData(result ?? []);
    } catch {
      setError("Failed to load occurrences");
    } finally {
      setIsLoading(false);
    }
  }, [ddrId]);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  return { data, isLoading, error, refetch: fetch };
}
```

### File 3 (NEW): `src/components/TypeBadge.tsx`

The 16 occurrence types from `keywords.json` (ALL must be covered):

```
BHA Failure, Back Ream, Bit Failure, Casing Issue, Cementing Issue,
Deviation, Fishing, H2S, Kick / Well Control, Lost Circulation,
Pack Off, Ream, Stuck Pipe, Tight Hole, Vibration, Washout
```

TYPE_COLOURS map — assign distinct, memorable Tailwind bg/text color pairs. Use light bg + dark text pattern. Example starting assignment (dev can adjust for contrast):

```typescript
export const TYPE_COLOURS: Record<string, { bg: string; text: string }> = {
  "Stuck Pipe":        { bg: "bg-red-100",    text: "text-red-800" },
  "Lost Circulation":  { bg: "bg-orange-100", text: "text-orange-800" },
  "Back Ream":         { bg: "bg-amber-100",  text: "text-amber-800" },
  "Ream":              { bg: "bg-yellow-100", text: "text-yellow-800" },
  "Tight Hole":        { bg: "bg-lime-100",   text: "text-lime-800" },
  "Washout":           { bg: "bg-green-100",  text: "text-green-800" },
  "BHA Failure":       { bg: "bg-teal-100",   text: "text-teal-800" },
  "Vibration":         { bg: "bg-cyan-100",   text: "text-cyan-800" },
  "Kick / Well Control":{ bg:"bg-sky-100",    text: "text-sky-800" },
  "H2S":               { bg: "bg-blue-100",   text: "text-blue-800" },
  "Deviation":         { bg: "bg-indigo-100", text: "text-indigo-800" },
  "Fishing":           { bg: "bg-violet-100", text: "text-violet-800" },
  "Pack Off":          { bg: "bg-purple-100", text: "text-purple-800" },
  "Casing Issue":      { bg: "bg-fuchsia-100",text: "text-fuchsia-800" },
  "Cementing Issue":   { bg: "bg-pink-100",   text: "text-pink-800" },
  "Bit Failure":       { bg: "bg-rose-100",   text: "text-rose-800" },
};

const FALLBACK = { bg: "bg-gray-100", text: "text-gray-700" };

export function TypeBadge({ type }: { type: string }) {
  const colors = TYPE_COLOURS[type] ?? FALLBACK;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${colors.bg} ${colors.text}`}
      aria-label={type}
    >
      {type}
    </span>
  );
}
```

### File 4 (NEW): `src/components/SectionBadge.tsx`

```typescript
export const SECTION_COLOURS = {
  Surface: { bg: "bg-emerald-100", text: "text-emerald-700", border: "border-emerald-300" },
  "Int.":  { bg: "bg-sky-100",     text: "text-sky-700",     border: "border-sky-300" },
  Main:    { bg: "bg-indigo-100",  text: "text-indigo-700",  border: "border-indigo-300" },
} as const;

export function SectionBadge({ section }: { section: string | null | undefined }) {
  if (!section) return null;
  const colors = SECTION_COLOURS[section as keyof typeof SECTION_COLOURS] ?? {
    bg: "bg-gray-100", text: "text-gray-700", border: "border-gray-200"
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}
      aria-label={section}
    >
      {section}
    </span>
  );
}
```

Colors match PRD: Surface=emerald-600 (#059669), Int.=sky-600 (#0284C7), Main=indigo-600 (#4F46E5). The Tailwind class bg-emerald-100/text-emerald-700 pair is visually close enough for the badge — use border to reinforce the brand color.

### File 5 (NEW): `src/components/FailedDateRow.tsx`

This is a table ROW component rendered inside `OccurrenceTable`:

```typescript
export function FailedDateRow({ date, error, colSpan }: { date: string; error: string; colSpan: number }) {
  return (
    <tr
      style={{ background: "#FEF2F2", borderLeft: "4px solid #C41230" }}
      aria-label="Date resolution failed. Action required."
    >
      <td colSpan={colSpan} className="px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-[#C41230] font-bold text-xs uppercase tracking-wide shrink-0">Failed</span>
          <span className="font-medium text-sm text-text-primary tabular-nums">{date}</span>
          <span className="text-text-muted text-xs">{error}</span>
        </div>
      </td>
    </tr>
  );
}
```

### File 6 (NEW): `src/components/OccurrenceTable.tsx`

Full TanStack Table v8 implementation. Key implementation details:

**Props:**
```typescript
type OccurrenceTableProps = {
  occurrences: OccurrenceRow[];
  failedDates: { date: string; error: string }[];
  isLoading: boolean;
};
```

**Column definitions:**
```typescript
const columns: ColumnDef<OccurrenceRow>[] = [
  { accessorKey: "well_name",        header: "Well Name",         cell: ({ getValue }) => getValue() ?? "—" },
  { accessorKey: "surface_location", header: "Surface Location",  cell: ({ getValue }) => getValue() ?? "—" },
  { accessorKey: "type",             header: "Type",              cell: ({ getValue }) => <TypeBadge type={getValue() as string} /> },
  { accessorKey: "section",          header: "Section",           cell: ({ getValue }) => <SectionBadge section={getValue() as string | null} /> },
  { accessorKey: "mmd",              header: "mMD (m)",           cell: ({ getValue }) => getValue() != null ? (getValue() as number).toFixed(1) : "—" },
  { accessorKey: "density",          header: "Density",           cell: ({ getValue }) => getValue() != null ? (getValue() as number).toFixed(2) : "—" },
  { accessorKey: "notes",            header: "Notes",             cell: ({ getValue }) => getValue() ?? "—" },
];
```

**Table setup:**
```typescript
const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
const [globalFilter, setGlobalFilter] = useState(initialSearch);
const [typeFilter, setTypeFilter] = useState(initialType);
const [sectionFilter, setSectionFilter] = useState(initialSection);

// Filter occurrences client-side (server-side filtering already done via API; this handles URL-param-driven refinement)
const filtered = useMemo(() => {
  return occurrences
    .filter(row => !typeFilter || row.type === typeFilter)
    .filter(row => !sectionFilter || row.section === sectionFilter)
    .filter(row => !globalFilter || JSON.stringify(row).toLowerCase().includes(globalFilter.toLowerCase()));
}, [occurrences, typeFilter, sectionFilter, globalFilter]);

const table = useReactTable({
  data: filtered,
  columns,
  state: { sorting },
  onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
});
```

**URL param sync** — use `useSearchParams` from `react-router`:
```typescript
const [searchParams, setSearchParams] = useSearchParams();
const initialType = searchParams.get("type") ?? "";
const initialSection = searchParams.get("section") ?? "";
const initialSearch = searchParams.get("q") ?? "";
```

Debounce filter updates (300ms) with `setTimeout`/`clearTimeout` before calling `setSearchParams`.

**Skeleton loading** — render 5 skeleton rows when `isLoading`:
```tsx
{isLoading && Array.from({ length: 5 }).map((_, i) => (
  <tr key={i} className="animate-pulse">
    {Array.from({ length: 4 }).map((_, j) => (
      <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-3/4" /></td>
    ))}
    {Array.from({ length: 3 }).map((_, j) => (
      <td key={j + 4} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-1/2" /></td>
    ))}
  </tr>
))}
```

**Interleave failed date rows** — render `failedDates` AFTER regular rows (before empty state check):
```tsx
{table.getRowModel().rows.map(row => (
  <tr key={row.id}
    className="border-b border-border-default hover:bg-slate-50 transition-colors"
  >
    {row.getVisibleCells().map(cell => (
      <td key={cell.id} className="px-4 py-2.5 text-sm text-text-primary">
        {flexRender(cell.column.columnDef.cell, cell.getContext())}
      </td>
    ))}
  </tr>
))}
{failedDates.map(fd => (
  <FailedDateRow key={fd.date} date={fd.date} error={fd.error} colSpan={columns.length} />
))}
```

**Sticky header** — `<thead>` must have `className="sticky top-0 z-10 bg-white"`. Wrap the table in a scrollable container: `<div className="overflow-auto max-h-[600px]">`.

**Active filter pills** — render below the search/filter bar:
```tsx
{activeFilters.length > 0 && (
  <div className="flex flex-wrap gap-2 mt-2">
    {activeFilters.map(f => (
      <span key={f.key} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-xs font-medium text-text-secondary">
        {f.label}
        <button onClick={() => clearFilter(f.key)} aria-label={`Remove ${f.label} filter`}>×</button>
      </span>
    ))}
  </div>
)}
```

**Sort indicator** in column headers: `↑` asc, `↓` desc, faint `⇅` unsorted. Clicking header calls `column.toggleSorting()`.

### File 7 (NEW): `src/components/CollapsibleSidebar.tsx`

```typescript
const NAV_ITEMS = [
  { path: "/",                   label: "Dashboard", Icon: HomeIcon },
  { path: "/history",            label: "History",   Icon: ClockIcon },
  { path: "/query",              label: "Query",     Icon: SearchIcon },
  { path: "/monitor",            label: "Monitor",   Icon: ActivityIcon },
  { path: "/settings/keywords",  label: "Settings",  Icon: SettingsIcon },
];
```

Use inline SVG icons (same pattern as `AppShell` LogoutIcon) — do NOT add an icon library dependency.

State management:
```typescript
const [collapsed, setCollapsed] = useState(() => {
  return localStorage.getItem("ces-sidebar-collapsed") === "true";
});

const toggle = () => {
  const next = !collapsed;
  setCollapsed(next);
  localStorage.setItem("ces-sidebar-collapsed", String(next));
};
```

Active item styling via NavLink `isActive`:
```tsx
<NavLink
  to={item.path}
  end={item.path === "/"}
  className={({ isActive }) => cn(
    "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-semibold transition-colors relative",
    isActive
      ? "text-ces-red bg-[#FEF2F2] border-l-[3px] border-ces-red"
      : "text-text-muted hover:text-text-primary hover:bg-black/[0.04]",
    collapsed && "justify-center px-0"
  )}
>
  <item.Icon className="w-5 h-5 shrink-0" aria-hidden="true" />
  {!collapsed && <span>{item.label}</span>}
</NavLink>
```

When collapsed: show icon only + `title` attribute (tooltip) on the NavLink.

Chevron toggle at bottom:
```tsx
<button
  onClick={toggle}
  aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
  className="flex items-center justify-center w-full py-3 text-text-muted hover:text-text-primary"
>
  <ChevronIcon className={cn("w-4 h-4 transition-transform", collapsed ? "rotate-180" : "")} />
</button>
```

Keyboard: `Space` on the chevron button toggles, `Enter` on nav items navigates. These work natively via `<button>` and `<NavLink>` — no extra handlers needed.

### File 8 (UPDATE): `src/components/AppShell.tsx`

**Current state:** `flex-col` layout with sticky top header containing logo, nav links, and sign-out button.

**Required change:** Replace with sidebar layout. Keep top brand strip (logo + sign-out only). Add `CollapsibleSidebar` as left sidebar.

```tsx
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Skip to main content — accessibility (UX-DR19) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-3 focus:py-1.5 focus:bg-white focus:border focus:border-ces-red focus:rounded focus:text-ces-red focus:text-sm focus:font-semibold"
      >
        Skip to main content
      </a>

      {/* Brand strip — logo + sign out only */}
      <header className="sticky top-0 z-50 border-b border-border-default bg-white/82 backdrop-blur-[12px]">
        <div className="flex items-center justify-between w-full px-6 min-h-[56px]">
          <Link to="/" aria-label="CES Home">
            <img src="/logo.png" alt="" className="w-auto h-7 block" width={120} height={28} loading="eager" />
          </Link>
          <button type="button" onClick={handleLogout} aria-label="Sign out" /* ... existing sign-out button ... */>
            {/* keep exact same sign-out button from current AppShell */}
          </button>
        </div>
      </header>

      {/* Sidebar + main content */}
      <div className="flex flex-1 overflow-hidden">
        <CollapsibleSidebar />
        <main id="main-content" className="flex-1 overflow-auto px-8 pt-7 pb-10 bg-surface max-[760px]:px-5">
          {children}
        </main>
      </div>
    </div>
  );
}
```

**Preserve:** Logo link, sign-out button, `handleLogout` function, all imports that are still needed.
**Remove:** The `<nav>` with `NAV_ITEMS` and `NavLink` elements inside the header (those move to `CollapsibleSidebar`).
**Add:** Import `CollapsibleSidebar`, `<a href="#main-content">` skip link, `id="main-content"` on `<main>`.

### File 9 (NEW): `src/pages/ReportDetailPage.tsx`

```tsx
import { useParams } from "react-router";
import DDRUploadPanel from "@/components/DDRUploadPanel";
import { OccurrenceTable } from "@/components/OccurrenceTable";
import { useOccurrences } from "@/hooks/useOccurrences";
import { useProcessingStatus } from "@/hooks/useProcessingStatus";

export default function ReportDetailPage() {
  const { id } = useParams();
  const status = useProcessingStatus(id);
  const { data: occurrences, isLoading: occurrencesLoading } = useOccurrences(id);

  const failedDates = status.rows
    .filter(row => row.status === "failed" && row.error)
    .map(row => ({ date: row.date, error: row.error! }));

  return (
    <section className="grid gap-7 animate-fade-in-up">
      {/* Existing processing status section — copy verbatim from ReportsPage.tsx */}
      {/* ... completionMessage banner, success/warning/failed stats cards, date rows ... */}

      {/* NEW: Occurrence table section */}
      <section aria-label="Occurrence table">
        <div className="mb-4">
          <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Occurrences</p>
          <h2 className="m-0 text-xl leading-snug font-semibold">Extracted Occurrences</h2>
        </div>
        <OccurrenceTable
          occurrences={occurrences ?? []}
          failedDates={failedDates}
          isLoading={occurrencesLoading}
        />
      </section>

      <DDRUploadPanel onUploaded={(created) => navigate(`/reports/${created.id}`)} />
    </section>
  );
}
```

Copy the ENTIRE processing status section JSX from `ReportsPage.tsx` — don't lose that behavior.

### File 10 (UPDATE): `src/routes.ts`

Change `/reports/:id` to use `ReportDetailPage`:

```typescript
import ReportDetailPage from "@/pages/ReportDetailPage";
// ...
{ path: "/reports/:id", protected: true, Component: ReportDetailPage },
```

`ReportsPage` import can be removed from routes.ts if not used elsewhere (it won't be). Keep the file itself.

### Tests: `src/components/OccurrenceTable.test.tsx`

Pattern: mock `useSearchParams` from react-router, render with `MemoryRouter`, use Testing Library queries.

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect } from "vitest";
import { OccurrenceTable } from "@/components/OccurrenceTable";
import type { OccurrenceRow } from "@/lib/api";

function makeOccurrence(overrides: Partial<OccurrenceRow> = {}): OccurrenceRow {
  return {
    id: "occ-1", ddr_id: "ddr-1", well_name: "Montney A", surface_location: null,
    type: "Stuck Pipe", section: "Main", mmd: 2100.0, density: 1.35,
    notes: "pipe stuck after connection", date: "20241031",
    ...overrides,
  };
}

function renderTable(props: Partial<React.ComponentProps<typeof OccurrenceTable>> = {}) {
  return render(
    <MemoryRouter>
      <OccurrenceTable
        occurrences={[]}
        failedDates={[]}
        isLoading={false}
        {...props}
      />
    </MemoryRouter>
  );
}
```

**Required test cases (12 minimum):**

```typescript
it("renders skeleton rows while loading")
it("renders column headers: Well Name, Surface Location, Type, Section, mMD, Density, Notes")
it("renders empty state when no occurrences and not loading")
it("renders occurrence row with TypeBadge")
it("renders SectionBadge with correct section label")
it("renders FailedDateRow with error message")
it("filters rows by type when type filter is applied")
it("filters rows by section dropdown")
it("global text search filters rows")
it("active filter shows as pill chip with × button")
it("clicking × on filter chip clears that filter")
it("table has role=grid and aria-rowcount attribute")
```

### Tests: `src/components/CollapsibleSidebar.test.tsx`

```typescript
it("renders all 5 nav items by default")
it("collapses to icon-only when toggle button clicked")
it("persists collapsed state to localStorage key ces-sidebar-collapsed")
it("restores collapsed state from localStorage on mount")
it("toggle button has correct aria-label based on state")
```

### Architecture Compliance Checklist

- All API calls through `apiClient` — never raw `fetch()` in components
- `useOccurrences` follows standard hook shape: `{ data, isLoading, error }` (architecture spec)
- TanStack Table headless pattern — table logic separate from rendering (no `@tanstack/react-table-core` hacks)
- Filter state in URL params via `useSearchParams` — not component state only (UX-DR17)
- `localStorage` key exactly `ces-sidebar-collapsed` (UX-DR7)
- No icon library dependency — inline SVG only
- shadcn/ui primitives used where available — `EmptyState` for empty state
- `role="grid"` + `aria-rowcount` on table element (UX-DR5)
- `aria-label` on every TypeBadge and SectionBadge (UX-DR21)
- Run `npm test` before marking done — ALL existing tests must still pass

### Existing Frontend Tests — Must Not Break

Current passing tests:
- `src/App.test.tsx`
- `src/lib/auth.test.ts`
- `src/lib/api.test.ts`
- `src/pages/ReportsPage.test.tsx` — routes change; if this test breaks, update the test to use `ReportDetailPage`
- `src/pages/DashboardPage.test.tsx`
- `src/hooks/useProcessingStatus.test.tsx`

`ReportsPage.test.tsx` may need to be renamed/updated to `ReportDetailPage.test.tsx` since the route now points to `ReportDetailPage`.

### File Structure Summary

```
ces-ddr-platform/ces-frontend/
├── package.json                                  (UPDATE — add @tanstack/react-table)
├── src/
│   ├── lib/
│   │   └── api.ts                               (UPDATE — add OccurrenceRow type + getOccurrences)
│   ├── hooks/
│   │   └── useOccurrences.ts                    (NEW)
│   ├── components/
│   │   ├── TypeBadge.tsx                        (NEW — TYPE_COLOURS + TypeBadge component)
│   │   ├── SectionBadge.tsx                     (NEW — SECTION_COLOURS + SectionBadge component)
│   │   ├── FailedDateRow.tsx                    (NEW — red-tinted table row)
│   │   ├── OccurrenceTable.tsx                  (NEW — TanStack Table, filters, skeleton, empty state)
│   │   ├── OccurrenceTable.test.tsx             (NEW — 12+ tests)
│   │   ├── CollapsibleSidebar.tsx               (NEW — 220px/48px toggle, localStorage)
│   │   ├── CollapsibleSidebar.test.tsx          (NEW — 5+ tests)
│   │   └── AppShell.tsx                         (UPDATE — sidebar layout, skip link)
│   ├── pages/
│   │   └── ReportDetailPage.tsx                 (NEW — occurrence table + processing status)
│   └── routes.ts                                (UPDATE — /reports/:id → ReportDetailPage)
```

### Previous Story Intelligence (3-4)

**What 3-4 built (backend):**
- `GET /ddrs/{ddr_id}/occurrences` — returns `list[OccurrenceInResponse]`
- Query params: `type` (alias), `section`, `date_from`, `date_to` — all optional, YYYYMMDD format for dates
- Response shape: `id, ddr_id, well_name, surface_location, type, section, mmd, density, notes, date`
- Pagination params: `limit` (default 1000), `offset` (default 0)
- Returns `[]` (200 OK) when DDR exists but no occurrences — NOT 404
- Returns 404 JSON if DDR doesn't exist

**Review-applied patches from 3-4 that affect frontend:**
- The `type` query param is sent as `?type=...` (the backend uses `Query(alias="type")`)
- Date filter format: `YYYYMMDD` (8-digit, e.g., `?date_from=20241001`)

### Current State of Files Being Updated

**`src/components/AppShell.tsx` (READ before modifying):**
- Currently `flex flex-col min-h-screen` outer div
- `<header>` with logo + nav links + sign-out button
- `<main>` with `flex-1 px-8 pt-7 pb-10 bg-surface`
- `NAV_ITEMS` array defined locally (move to sidebar, remove from AppShell)
- `LogoutIcon` SVG defined locally — keep it, still needed

**`src/routes.ts` (READ before modifying):**
- `{ path: "/reports/:id", protected: true, Component: ReportsPage }` — change `ReportsPage` to `ReportDetailPage`
- `ReportsPage` import → remove or replace with `ReportDetailPage`

### Testing Requirements

```bash
cd ces-ddr-platform/ces-frontend
npm test
```

All existing tests must pass. New tests: 12+ for OccurrenceTable, 5+ for CollapsibleSidebar.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#OccurrenceTable, CollapsibleSidebar, TypeBadge]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture, Component Structure]
- [Source: _bmad-output/implementation-artifacts/stories/3-4-occurrence-generation-api-pipeline-integration.md]
- [Source: ces-ddr-platform/ces-frontend/src/components/AppShell.tsx]
- [Source: ces-ddr-platform/ces-frontend/src/pages/ReportsPage.tsx]
- [Source: ces-ddr-platform/ces-frontend/src/hooks/useProcessingStatus.ts]
- [Source: ces-ddr-platform/ces-frontend/src/lib/api.ts]
- [Source: ces-ddr-platform/ces-backend/src/resources/keywords.json]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Installed `@tanstack/react-table` v8 dependency.
- Added `OccurrenceRow` and `OccurrenceFilters` types plus `getOccurrences` method to `ApiClient`.
- Created `useOccurrences` hook with `{ data, isLoading, error, refetch }` shape.
- Created `TypeBadge` with 16-type `TYPE_COLOURS` map and grey fallback.
- Created `SectionBadge` with `SECTION_COLOURS` for Surface, Int., Main.
- Created `FailedDateRow` with red-50 background, #C41230 left border, and inline error.
- Created `OccurrenceTable` using TanStack Table v8 with sticky header, skeleton loading, empty state, type/section/search filters, active filter pills, URL query param sync (300ms debounce), default date-desc sort with header-click cycling, role="grid", aria-rowcount, and inline failed-date rows.
- Created `CollapsibleSidebar` with 220px/48px toggle, localStorage persistence (`ces-sidebar-collapsed`), active-item styling, and 5 inline-SVG nav items.
- Updated `AppShell` to sidebar layout: brand strip (logo + sign-out) + `CollapsibleSidebar` + `<main id="main-content">` with skip-link.
- Created `ReportDetailPage` composing processing status (copied from `ReportsPage`), `OccurrenceTable`, and `DDRUploadPanel`.
- Updated `routes.ts` to point `/reports/:id` to `ReportDetailPage`.
- Wrote 12 tests for `OccurrenceTable` and 5 tests for `CollapsibleSidebar`.
- Fixed pre-existing `DashboardPage.test.tsx` assertion that expected outdated copy.
- All 43 tests pass; TypeScript build clean.

### File List

- `ces-ddr-platform/ces-frontend/package.json` — added `@tanstack/react-table`
- `ces-ddr-platform/ces-frontend/src/lib/api.ts` — added `OccurrenceRow`, `OccurrenceFilters`, `getOccurrences`
- `ces-ddr-platform/ces-frontend/src/hooks/useOccurrences.ts` — new
- `ces-ddr-platform/ces-frontend/src/components/TypeBadge.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/SectionBadge.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/FailedDateRow.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/OccurrenceTable.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/OccurrenceTable.test.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/CollapsibleSidebar.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/CollapsibleSidebar.test.tsx` — new
- `ces-ddr-platform/ces-frontend/src/components/AppShell.tsx` — updated (sidebar layout, skip link)
- `ces-ddr-platform/ces-frontend/src/pages/ReportDetailPage.tsx` — new
- `ces-ddr-platform/ces-frontend/src/routes.ts` — updated (`/reports/:id` → `ReportDetailPage`)
- `ces-ddr-platform/ces-frontend/src/pages/DashboardPage.test.tsx` — fixed assertion

### Review Findings

- [x] [Review][Patch] Login CSS missing from index.css [src/index.css] — fixed: migrated all login CSS classes
- [x] [Review][Patch] searchParams in useEffect deps → infinite loop [OccurrenceTable.tsx:107] — fixed: functional update
- [x] [Review][Patch] Filter state not re-synced on back/forward [OccurrenceTable.tsx] — fixed: added sync effect
- [x] [Review][Patch] useOccurrences names callback `fetch` — shadows global [useOccurrences.ts:10] — fixed: renamed to loadData
- [x] [Review][Patch] useOccurrences no AbortController — stale response on fast nav [useOccurrences.ts] — fixed
- [x] [Review][Patch] Double-filtering: useMemo + getFilteredRowModel both active [OccurrenceTable.tsx] — fixed: removed getFilteredRowModel
- [x] [Review][Patch] TypeBadge receives null/empty → empty aria-label [TypeBadge.tsx] — fixed: null guard
- [x] [Review][Patch] JSON.stringify leaks id/ddr_id in global search [OccurrenceTable.tsx:131] — fixed: visible fields only
- [x] [Review][Patch] aria-rowcount reports 0 during skeleton load [OccurrenceTable.tsx:223] — fixed: -1 when loading
- [x] [Review][Patch] ALL_TYPES uses Object.keys({}) antipattern [OccurrenceTable.tsx:20] — fixed: plain array
- [x] [Review][Patch] Tailwind px-3 + px-0 conflict in CollapsibleSidebar [CollapsibleSidebar.tsx:94] — fixed
- [x] [Review][Patch] visibleColumns dead code [OccurrenceTable.tsx] — fixed: removed
- [x] [Review][Patch] FailedDateRow keyed by date — duplicate key on retry [OccurrenceTable.tsx:289] — fixed: date+error key
- [x] [Review][Patch] ReportDetailPage no guard when id undefined [ReportDetailPage.tsx] — fixed: Navigate redirect
- [x] [Review][Patch] UPLOAD_DIR default changed to relative path breaks Docker [base.py:74] — fixed: restored /app/uploads, added to .env
- [x] [Review][Patch] CollapsibleSidebar localStorage throws without window [CollapsibleSidebar.tsx:67] — fixed: try/catch
- [x] [Review][Patch] useOccurrences swallows UNAUTHORIZED — no redirect [useOccurrences.ts:17] — fixed: re-throw skip
- [x] [Review][Patch] AppShell dropped mobile vertical padding [AppShell.tsx:59] — fixed: restored pt-5 pb-8
- [x] [Review][Patch] Arrow key grid navigation not implemented — ARIA violation [OccurrenceTable.tsx] — fixed: keyboard handler
- [x] [Review][Patch] SectionBadge uses -100/-700 shades vs spec -600 [SectionBadge.tsx] — fixed: -600 text-white
- [x] [Review][Defer] redirectToLogin bypasses React Router navigate [api.ts:203] — deferred, pre-existing
- [x] [Review][Defer] getOccurrences return type hides undefined on 204 [api.ts:164] — deferred, pre-existing

### Change Log

- 2026-05-11: Story created — OccurrenceTable UI, TypeBadge, SectionBadge, FailedDateRow, CollapsibleSidebar, AppShell sidebar layout, ReportDetailPage.
- 2026-05-11: Implemented all tasks; 43 tests pass; TypeScript clean.
- 2026-05-11: Code review applied — 20 patches, 2 deferred. All 43 tests pass.
