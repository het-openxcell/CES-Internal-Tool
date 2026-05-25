# Story 4.5: Inline Edit UI & ReasonCaptureModal

Status: ready-for-dev

## Story

As a CES staff member,
I want to click any cell in the occurrence table to edit it inline and capture my reason in a lightweight modal,
so that correcting a wrong classification takes under 5 seconds and leaves a clear audit trail.

## Context: Read FIRST — most of the plumbing already exists, this story is the UI layer on top of it

This is a **frontend-only** story. The backend correction loop is already complete and shipped:

- **`PATCH /occurrences/:id` is done** (story 4-2). The browser client method **already exists**: `apiClient.patchOccurrence(occurrenceId, fieldName, correctedValue, reason)` (`src/lib/api.ts:257-262`) — it POSTs `{ field_name, corrected_value, reason }` and returns the updated `OccurrenceRow`. **Reuse it. Do NOT add a new client method.**
- **`OccurrenceTable` already has the scaffolding** for this feature (`src/components/OccurrenceTable.tsx`): keyboard cell navigation (`focusedCell` state + `handleTableKeyDown` + `tbodyRef` + `data-cell-rc` focus tracking), the `ALL_TYPES` (16 entries) and `ALL_SECTIONS` lists, and a **legend that already announces the not-yet-wired behavior** — "manually corrected" amber dot, "failed extraction", and "Click any cell to edit · Esc cancels · Enter confirms" (`OccurrenceTable.tsx:386-394`). The legend is aspirational today; this story makes it real.
- **The amber CSS token exists**: `--color-edit-indicator: #D97706` (`src/index.css:7`), referenced as `bg-[var(--edit-indicator)]` in the legend. Use the **same token** for the row dot.
- **`Correction` type exists** in `src/lib/api.ts:65-75` (not needed for this story's writes, but available).

The "both Python backend" / dual-backend phrasing in `epics.md` is dead — project is Python-only (`sprint-status.yaml#approved_changes.python_only_backend_cleanup`). The backend is irrelevant to this story beyond the existing `PATCH` contract above.

## ⚠️ Hard constraints — read before writing any markup

1. **NO left borders as edit/state indicators.** `CLAUDE.md` explicitly forbids `border-l-*` decorative accents on cards/rows/badges. The UX spec (`ux-design-specification.md:589`, `:618`) describes the edited-row state as "amber left border + dot" — **ignore the left-border half.** The corrected-row indicator in this story is the **amber dot only** (plus the "Edited" column for dual-encoding). Do not add a left border to corrected rows.
2. **No new dependencies.** Only `button` and `empty-state` exist under `src/components/ui/` — there is **no Radix/shadcn Dialog installed.** Build `ReasonCaptureModal` as a plain custom component. This is also correct per UX (`:576`): Radix Dialog cannot do row-anchoring or render without a backdrop, both of which this story requires. Do **not** add `@radix-ui/*` or any toast library.
3. **No toast library exists.** `KeywordsPage` rolls a local toast (`src/pages/KeywordsPage.tsx:171-175` — a `fixed bottom-6 right-6 z-50` div driven by a `toast` state string). Match that approach; do not install `sonner`/`react-hot-toast`.
4. **All datetimes are epoch** (`CLAUDE.md`) — not relevant here (no timestamps rendered), noted for completeness.
5. **No file comments. Self-documenting names.** (`CLAUDE.md`)

## Acceptance Criteria

1. **Given** `OccurrenceTable` renders occurrence rows
   **When** a user single-clicks an editable cell (Type, Section, mMD, Density, Notes)
   **Then** the cell enters edit mode immediately — no double-click, no Edit button
   **And** for the **Type** field a dropdown opens listing all approved types (`ALL_TYPES`), filtered as the user types
   **And** for the other editable fields an inline text input appears pre-filled with the current value
   **And** non-editable cells (Incident Date, Well Name, Surface Location, Page) do **not** enter edit mode on click

2. **Given** the user selects a new value from the Type dropdown or enters a new value in a text input
   **When** the selection/input is confirmed (and the value actually changed)
   **Then** `ReasonCaptureModal` appears anchored directly below or above the edited row — whichever side has more screen space — **never center-screen** (UX-DR6)
   **And** the modal shows a read-only context label of the change: e.g. `Type: Ream → Back Ream` (original → corrected)
   **And** a single text input with placeholder `Why was this changed?` receives auto-focus immediately
   **And** **no backdrop/overlay** is rendered — the rest of the table stays visible and interactive-looking

3. **Given** `ReasonCaptureModal` is open
   **When** the user types a reason and presses Enter (reason must be non-empty — Save disabled/no-op while blank, UX `:683`)
   **Then** `apiClient.patchOccurrence(id, field_name, corrected_value, reason)` is called
   **And** the modal closes instantly on API success
   **And** an amber dot (`--edit-indicator` / `#D97706`) appears on the corrected row immediately (UX-DR15)
   **And** the table scroll position is unchanged throughout the entire interaction
   **And** a toast appears bottom-right reading `Correction saved — will inform future extractions`, auto-dismissing after 3 seconds (UX-DR14)

4. **Given** `ReasonCaptureModal` is open
   **When** the user presses Escape (or clicks Cancel)
   **Then** the modal closes with nothing saved and the cell value reverts to the original (no optimistic value lingers)
   **And** keyboard focus returns to the triggering cell (UX-DR6)

5. **Given** a row has been corrected (has an amber edit dot)
   **When** a screen reader inspects the dot
   **Then** the dot element exposes `aria-label="Cell manually corrected"` (UX-DR20)
   **And** an "Edited" column header is present so the amber dot is dual-encoded (not color-only) (UX-DR20)

6. **Given** the `useCorrections` hook exists in `src/hooks/`
   **When** a correction is saved
   **Then** the hook performs an **optimistic update** — the row shows the new value immediately, before the request resolves
   **And** on API error the row reverts to its original value and an inline error message is shown for that row
   **And** the corrected-row set / value overrides are exposed so `OccurrenceTable` can render the dot and the new value

## Tasks / Subtasks

- [ ] **Task 1: `useCorrections` hook** (AC: 3, 6) — `src/hooks/useCorrections.ts`
  - [ ] Signature: `useCorrections()` returning `{ overrides, correctedIds, errors, saveCorrection, clearError }` where `overrides: Record<string, Partial<OccurrenceRow>>` (occurrence id → changed fields), `correctedIds: Set<string>`, `errors: Record<string, string>`.
  - [ ] `saveCorrection(occurrenceId, fieldName, correctedValue, reason)`:
    - apply optimistic override immediately (`overrides[id] = { ...prev, [fieldName]: parsedValue }`) and mark `correctedIds.add(id)` so the dot shows at once;
    - `await apiClient.patchOccurrence(occurrenceId, fieldName, correctedValue, reason)`;
    - on success: keep the override (or replace it with the returned row's value) and resolve so the caller can fire the toast;
    - on error: **revert** — remove the optimistic override and the `correctedIds` entry for that id, set `errors[id] = "Couldn't save correction — try again"`, and re-throw or return a failure flag so the caller does not show a success toast.
  - [ ] `clearError(id)` to dismiss the inline error.
  - [ ] Field value parsing: `mmd`/`density` → `Number(...)` (and guard `NaN` → treat as invalid, skip save); `type`/`section`/`notes` → string. Keep this in the hook so the table stays presentational.
  - [ ] Follow the existing hook style (`useRetryDate.ts`, `useOccurrences.ts`): `useCallback`, `useState`, no external state lib.

- [ ] **Task 2: `ReasonCaptureModal` component** (AC: 2, 3, 4) — `src/components/ReasonCaptureModal.tsx`
  - [ ] Props: `{ fieldLabel, originalValue, correctedValue, anchorRect, onSubmit(reason), onCancel }`.
  - [ ] Render with `position: absolute` (or `fixed` keyed off `anchorRect` from `getBoundingClientRect()`), width **320px** (UX `:859`), anchored **below the row if there is more space below, else above** (compute from `anchorRect` vs `window.innerHeight`). **Never** center-screen. **No backdrop element.**
  - [ ] Anatomy: title, read-only context chip `"{fieldLabel}: {originalValue} → {correctedValue}"`, one text input (placeholder `Why was this changed?`), Cancel (ghost) + Save (primary `bg-[--ces-red] text-white`) — button tiers per UX `:644-650`.
  - [ ] Auto-focus the reason input on mount (`ref` + `useEffect` focus).
  - [ ] Keyboard: `Enter` → submit if reason non-empty; `Escape` → `onCancel`. Save disabled while reason empty (UX `:683`). Blur does **not** cancel (reason required — UX `:598`).
  - [ ] A11y: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at the title, simple focus trap (keep focus within Cancel/Save/input while open).
  - [ ] Reposition / keep anchored if needed, but do **not** scroll the table (AC 3 — scroll position unchanged).

- [ ] **Task 3: Wire inline editing into `OccurrenceTable`** (AC: 1, 2, 3, 4, 5) — `src/components/OccurrenceTable.tsx`
  - [ ] Add an **"Edited" leading column** (≈22px, UX `:588`) that renders the amber dot for rows in `correctedIds`: `<span aria-label="Cell manually corrected" className="h-2 w-2 rounded-full bg-[var(--edit-indicator)]" />`. Header cell text "Edited" (dual-encoding, AC 5). Update `VISIBLE_COLUMN_KEYS` / `COLUMN_LAYOUT` and the skeleton/empty `colSpan` counts accordingly.
  - [ ] Define which cells are editable: `EDITABLE_FIELDS = ["type", "section", "mmd", "density", "notes"]`. Single-click on those cells enters edit mode (`editingCell` state `{ rowId, field }`). Other columns stay read-only.
  - [ ] In edit mode: **Type** → a filter-as-you-type dropdown over `ALL_TYPES` (reuse the existing constant); **other fields** → inline `<input>` pre-filled with the current display value. Confirming the editor (Enter / select / blur-with-change) opens `ReasonCaptureModal` anchored to that row's `<tr>` (`getBoundingClientRect()`), passing original + corrected values. If the value did **not** change, just exit edit mode (no modal).
  - [ ] On modal submit: call `saveCorrection(...)` from `useCorrections`; on the returned success fire the local toast (Task 4) and close the modal; the optimistic override already shows the new value. On failure the hook reverts and sets the inline error.
  - [ ] On modal cancel/Escape: close modal, discard pending value, **return focus to the triggering cell** (reuse the existing `focusedCell` + `data-cell-rc` focus mechanism — set `focusedCell` back to the row/col that was edited).
  - [ ] Merge `overrides` onto the displayed rows so corrected values render (e.g. map `filtered` rows through `overrides[row.id]` before handing to the table, or read override in the cell). Keep TanStack `data` stable enough that **scroll position is preserved** (do not remount the table body / do not reset `data` identity unnecessarily).
  - [ ] Render the per-row inline error (from `errors[id]`) near the row with a dismiss affordance (`clearError`).
  - [ ] Remove/repurpose the placeholder "Status" filter `<select>` only if it conflicts; otherwise leave it untouched (out of scope).

- [ ] **Task 4: Success toast** (AC: 3) — local, in `OccurrenceTable` (or a tiny `src/components/ui/toast`-less local state)
  - [ ] Match `KeywordsPage` pattern: a `toast` state string + a `fixed bottom-6 right-6 z-50` element; on success set `"Correction saved — will inform future extractions"`, clear after **3000ms** (UX success = green `#16A34A`, ✓, 3s — `ux-design-specification.md:665`). Use a green success style, not the neutral gray KeywordsPage uses, to match the spec.
  - [ ] Ensure the timeout is cleared on unmount.

- [ ] **Task 5: Tests** (AC: 1–6)
  - [ ] **Hook tests** `src/hooks/useCorrections.test.tsx` (pattern: `renderHook` + `act` + `vi.mock`, like `useProcessingStatus.test.tsx`): optimistic override appears before resolve; success keeps override + resolves; failure reverts override, drops `correctedIds`, sets `errors[id]`; `mmd`/`density` parsed to number; blank/NaN rejected.
  - [ ] **Component tests** — extend `src/components/OccurrenceTable.test.tsx`:
    - single-click on a Type cell opens the type dropdown (not on Well Name / Date);
    - selecting a new Type opens `ReasonCaptureModal` with the `Type: old → new` context label and an auto-focused reason input;
    - typing a reason + Enter calls `apiClient.patchOccurrence` with `{ id, "type", newValue, reason }`, closes the modal, shows the amber dot (`aria-label="Cell manually corrected"`) and the success toast text;
    - Escape on the modal reverts the value, closes the modal, no `patchOccurrence` call;
    - "Edited" column header is present (dual-encoding);
    - error path: `patchOccurrence` rejects → row value reverts, inline error visible, no success toast.
  - [ ] Mock the network the same way existing tests do — either `vi.mock("@/lib/api")` to stub `apiClient.patchOccurrence`, or stub global `fetch` with a `Response` (see `DashboardPage.test.tsx:36,59`). Prefer mocking `apiClient.patchOccurrence` directly for clarity.
  - [ ] Run from `ces-ddr-platform/ces-frontend/`: `npm run lint && npm run test` (and `npm run build` if available) — all green, no new failures. Verify the existing 17 `OccurrenceTable` tests still pass after the column/markup changes (the added "Edited" column changes cell counts — fix any count-based assertions you break).

## Dev Notes

### Editable-field nuance (follow the AC literally, but know the data)

AC 1 says **Type → dropdown, all other editable fields → text input.** So `section` is a **text input** per the AC even though `ALL_SECTIONS` (`Surface`, `Int.`, `Main`) is a closed set. Implement it as a text input to match the AC and keep this story tight; do not gold-plate it into a second dropdown. (If you feel strongly, leave a question at the end — do not silently diverge.) `mmd`/`density` are numeric text inputs; `notes` is free text.

### How "corrected" state is tracked (there is no backend flag)

`OccurrenceRow` (`src/lib/api.ts:44-56`) has **no** "corrected" field, and `GET /ddrs/:id/occurrences` does not return one. So the amber dot is **client-side only** for this story: it appears the instant a correction is saved (driven by `useCorrections.correctedIds`) and is not expected to survive a full page reload / refetch. AC 3 only requires the dot to appear **immediately** after save — that is satisfied by the optimistic client state. Do **not** invent a backend change to persist dot state; that is out of scope.

### Optimistic update + scroll preservation (the two things a reviewer will check)

- The whole point of `useCorrections` is that the new value and dot render **before** the network resolves (AC 6). Apply the override synchronously inside `saveCorrection`, then await the request.
- Scroll position must not jump (AC 3). The table scroll container is `<div className="overflow-auto max-h-[600px] ...">` (`OccurrenceTable.tsx:295`). Do not remount it, do not reset the TanStack `data` array identity on every keystroke, and anchor the modal with `position: fixed`/`absolute` off `getBoundingClientRect()` rather than anything that reflows the table. The modal must not be a child that changes table layout.

### Modal anchoring math

Read the triggering `<tr>` rect via `getBoundingClientRect()`. If `window.innerHeight - rect.bottom >= MODAL_HEIGHT` place the modal at `top: rect.bottom`, else place it at `bottom: window.innerHeight - rect.top` (i.e. above). Fixed width 320px (UX `:859`). No backdrop. Keep it in a portal-free absolutely-positioned element or a `position: fixed` element appended in-component — either is fine as long as no overlay div covers the table.

### Focus return on cancel (AC 4)

The table already has a focus mechanism: setting `focusedCell` to `{ row, col }` triggers the `useEffect` (`OccurrenceTable.tsx:157-163`) that calls `cell.focus()` on the matching `data-cell-rc`. Reuse it — when the modal cancels, set `focusedCell` back to the edited cell's row/col so focus visibly returns there.

### Button & toast styling (match the system)

- Save = Primary tier (`bg-[--ces-red] text-white`, 8px radius), Cancel = Ghost (`text-muted-foreground hover:bg-accent`) — `ux-design-specification.md:644-650`. The existing `src/components/ui/button.tsx` may already encode these variants — **check it and reuse** rather than hand-rolling classes.
- Success toast green `#16A34A`, ✓, 3s auto-dismiss (`:665`). Reuse the KeywordsPage placement (`fixed bottom-6 right-6 z-50`).

### Reuse discipline (CLAUDE.md — checked, do NOT recreate)

- `apiClient.patchOccurrence` — exists, reuse (`api.ts:257`).
- `ALL_TYPES`, `ALL_SECTIONS` — exist in `OccurrenceTable.tsx:20-39`, reuse for the Type dropdown.
- `--edit-indicator` token + the legend dot markup — exist (`index.css:7`, `OccurrenceTable.tsx:388`), reuse the same class.
- `focusedCell` keyboard/focus infra — exists, reuse for focus-return.
- `button.tsx` variants — check before writing class strings.
- KeywordsPage toast pattern — copy the structure, don't add a lib.

### Project Structure Notes

- New files: `src/hooks/useCorrections.ts`, `src/hooks/useCorrections.test.tsx`, `src/components/ReasonCaptureModal.tsx`.
- Modified: `src/components/OccurrenceTable.tsx` (inline edit, Edited column, toast wiring), `src/components/OccurrenceTable.test.tsx` (new tests + fix cell-count assertions).
- `ReportDetailPage.tsx` mounts `<OccurrenceTable occurrences isLoading />` (`:235-238`) with `refetchOccurrences` available — but this story keeps optimistic state **inside** the table via `useCorrections`, so no prop changes to `OccurrenceTable` are strictly required. Do not refetch after each save (it would wipe the optimistic dot since the backend returns no flag). If you do choose to lift state, keep the public `OccurrenceTableProps` shape backward-compatible.
- No backend, schema, or migration changes. No new npm dependencies.

### References

- `_bmad-output/planning-artifacts/epics.md:885-928` — Story 4.5 ACs (inline edit, ReasonCaptureModal, amber dot, optimistic `useCorrections`).
- `ux-design-specification.md:585-599` — `OccurrenceTable` + `ReasonCaptureModal` anatomy/states/a11y; `:597` row-anchored never-center; `:598` Enter/Escape, blur-to-cancel disabled.
- `ux-design-specification.md:659-694` — toast spec (`:665` success green 3s), inline amber-dot feedback (`:671`), reason-modal form pattern (`:689-694`: submit→close→dot→toast).
- `ux-design-specification.md:618`, `:859` — `--edit-indicator` "never aliased to primary"; modal fixed 320px.
- `ux-design-specification.md:589` / `:618` — describes "amber left border" → **overridden** by `CLAUDE.md` (no `border-l-*`); use dot only.
- `src/lib/api.ts:257-262` — `patchOccurrence` (reuse); `:44-56` `OccurrenceRow` (no corrected flag); `:65-75` `Correction`.
- `src/components/OccurrenceTable.tsx` — `ALL_TYPES`/`ALL_SECTIONS` (`:20-39`), `focusedCell`/`handleTableKeyDown`/focus `useEffect` (`:127`, `:157-163`, `:201-215`), legend (`:386-394`), scroll container (`:295`), column config (`:99-110`).
- `src/index.css:7` — `--color-edit-indicator: #D97706`.
- `src/pages/KeywordsPage.tsx:171-175` — local toast pattern (no lib).
- `src/components/ui/button.tsx` — button variants to reuse.
- `src/hooks/useRetryDate.ts`, `src/hooks/useOccurrences.ts` — hook style.
- `src/hooks/useProcessingStatus.test.tsx` — `renderHook`/`act`/mock pattern; `src/pages/DashboardPage.test.tsx:36,59` — `fetch`/`Response` mock pattern; `src/components/OccurrenceTable.test.tsx` — component test template (`makeOccurrence`, `renderTable`, `MemoryRouter`).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-05-21: Story created — frontend inline-edit + ReasonCaptureModal + optimistic `useCorrections` hook over the existing `patchOccurrence` client. Reconciled UX "amber left border" against CLAUDE.md no-left-border rule (dot only); no new deps (custom modal, local toast).
