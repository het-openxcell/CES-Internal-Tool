# Story 7.6: Admin User Management UI

Status: ready-for-dev

## Story

As a platform admin,
I want a User Management tab and page,
so that I can create and deactivate users from the app.

## Acceptance Criteria

1. Given authenticated user's JWT contains `roles: ["ADMIN"]`, then TopNav renders a "Users" tab linking to `/users`.
2. Given authenticated user's JWT contains `roles: ["USER"]` or no roles, then "Users" tab is NOT rendered in TopNav.
3. Given ADMIN opens `/users`, then a table shows: username, roles, active status, created_at (formatted). Password is never shown.
4. Given ADMIN submits the create-user form with username and password, then `POST /api/users` is called through `apiClient`. Created user appears in the table with `USER` role and active status.
5. Given ADMIN clicks "Deactivate" on an active user row (with inline confirmation), then `PATCH /api/users/{id}/deactivate` is called. Row updates to show inactive status. Admin user cannot deactivate themselves.
6. Given a USER navigates directly to `/users`, then the page shows a "forbidden" empty state (API will return 403 for any data fetch).
7. Given auth context, then `authToken.getRoles()` reads `roles` from JWT payload. Role is decoded client-side for navigation only — backend is the security boundary.
8. Given UI route at `/users`, then it is registered in `routes.ts` as a protected route.

## Tasks / Subtasks

- [ ] Add `getRoles()` to `AuthToken` in `auth.ts` (AC: 7)
  - [ ] In `ces-frontend/src/lib/auth.ts`, update `JwtPayload` type to include `roles?: unknown`.
  - [ ] Add method `getRoles(): string[]` to `AuthToken` class:
    ```ts
    getRoles(): string[] {
      const token = this.get();
      if (!token) return [];
      const payload = this.decodePayload(token);
      if (!Array.isArray(payload?.roles)) return [];
      return payload.roles.filter((r): r is string => typeof r === "string");
    }
    ```
  - [ ] `decodePayload` already exists and handles JWT decode — no change needed there.
- [ ] Add user management API methods and types to `api.ts` (AC: 3, 4, 5)
  - [ ] Add types:
    ```ts
    export type User = {
      id: string;
      username: string;
      is_active: boolean;
      roles: string[];
      created_at: number;
      updated_at: number;
    };

    export type CreateUserRequest = {
      username: string;
      password: string;
    };
    ```
  - [ ] Add methods to `apiClient`:
    - `getUsers()` → `GET /api/users` → returns `User[]`.
    - `createUser(req: CreateUserRequest)` → `POST /api/users` → returns `User`.
    - `deactivateUser(userId: string)` → `PATCH /api/users/{id}/deactivate` → returns `User`.
- [ ] Update `TopNav.tsx` to accept and render `roles` prop (AC: 1, 2)
  - [ ] Add `roles?: string[]` to TopNav props: `{ onLogout: () => void; username?: string | null; roles?: string[] }`.
  - [ ] Add `isAdmin` derived value: `const isAdmin = roles?.includes("ADMIN") ?? false`.
  - [ ] Add "Users" tab entry to `TABS` array conditionally — filter it out if not admin:
    ```ts
    const visibleTabs = isAdmin
      ? [...TABS, { key: "users", label: "Users", path: "/users", Icon: Users }]
      : TABS;
    ```
    Use `Users` icon from `lucide-react` (already a dependency).
  - [ ] Replace `TABS.map(...)` in JSX with `visibleTabs.map(...)`. No other TopNav changes.
  - [ ] Do NOT add any role-based logic elsewhere in TopNav.
- [ ] Update `AppShell.tsx` to pass `roles` to `TopNav` (AC: 1, 2)
  - [ ] In `AppShellInner`, add: `const roles = authToken.getRoles()`.
  - [ ] Pass `roles={roles}` to `<TopNav onLogout={handleLogout} username={username} roles={roles} />`.
  - [ ] No other AppShell changes.
- [ ] Create `UserManagementPage.tsx` (AC: 3, 4, 5, 6)
  - [ ] New file: `ces-frontend/src/pages/UserManagementPage.tsx`.
  - [ ] On mount: call `apiClient.getUsers()`. If 403, show forbidden empty state ("You do not have permission to view this page").
  - [ ] Table columns: Username, Roles (comma-separated role names), Status (Active/Inactive badge), Created, Actions.
  - [ ] "Create User" button opens an inline form or modal with `username` and `password` fields. Submits `apiClient.createUser(...)`. On success: adds user to table, clears form.
  - [ ] "Deactivate" button in Actions column — only shows for active users. Inline confirmation ("Confirm deactivate?"). On confirm: calls `apiClient.deactivateUser(user.id)`. Updates row to inactive.
  - [ ] Prevent self-deactivation: compare `user.id` against JWT payload `user_id` (add `getUserId()` to `AuthToken` or decode inline) — hide/disable Deactivate for own row.
  - [ ] Status badge: Active = green badge, Inactive = gray badge. No `border-l-*` styling.
  - [ ] Error states: show inline error text for create/deactivate failures. Do not crash the page.
- [ ] Register `/users` route in `routes.ts` (AC: 8)
  - [ ] Import `UserManagementPage` from `@/pages/UserManagementPage`.
  - [ ] Add to `APP_ROUTES`: `{ path: "/users", protected: true, Component: UserManagementPage }`.
  - [ ] No route guard beyond `ProtectedRoute` (which checks auth token) — forbidden state is handled by 403 from backend.
- [ ] Run frontend quality gates (AC: 1–8)
  - [ ] `cd ces-ddr-platform/ces-frontend && npm run build` — no TypeScript errors.
  - [ ] `cd ces-ddr-platform/ces-frontend && npm run test` if test suite exists.

## Dev Notes

### Critical Context

- Frontend-only story. Depends on Story 7-5 backend being complete.
- Story 7-5 adds `roles: [string]` to JWT payload — frontend reads it via `authToken.getRoles()`.
- `AppShell.tsx` currently calls `authToken.getUsername()` — extend to also call `authToken.getRoles()`.
- Backend is the security boundary. Frontend nav hiding is convenience only.

### DO NOT REIMPLEMENT — Reuse These

| Existing thing | Where | How to use in 7-6 |
|---|---|---|
| `authToken` class | `src/lib/auth.ts` | Extend with `getRoles()` — do not create new auth utility |
| `authToken.getUsername()` | `src/lib/auth.ts` | Keep unchanged |
| `authToken.get()` + `decodePayload()` | `src/lib/auth.ts` | `getRoles()` calls same `decodePayload()` internally |
| `AppShellInner` | `src/components/AppShell.tsx` | Just add `getRoles()` call + pass to TopNav |
| `TopNav` TABS array | `src/components/TopNav.tsx` | Extend conditionally; do not rewrite nav rendering logic |
| `ProtectedRoute` | `src/components/ProtectedRoute.tsx` | No change — all protected routes go through it |
| `APP_ROUTES` array | `src/routes.ts` | Append new route; do not rewrite |
| `apiClient.request<T>()` | `src/lib/api.ts` | All new API calls use same pattern |
| `fmtTs()` from MonitorPage | Use inline or import | For `created_at` epoch formatting — copy the helper or create shared util |
| Badge/pill styling patterns | MonitorPage, TopNav | Reuse existing CSS class patterns |

### `getUserId()` for Self-Deactivation Guard

Add to `AuthToken` in `auth.ts`:
```ts
getUserId(): string | null {
  const token = this.get();
  if (!token) return null;
  const payload = this.decodePayload(token);
  return typeof payload?.user_id === "string" ? payload.user_id : null;
}
```
Update `JwtPayload` type to include `user_id?: unknown`. Then in `UserManagementPage`:
```ts
const myId = authToken.getUserId();
// In row Actions: disabled={user.id === myId}
```

### TopNav Roles-Conditional Tab

Current `TABS` is a const array — to conditionally add "Users" tab:
```ts
export default function TopNav({ onLogout, username, roles }: { onLogout: () => void; username?: string | null; roles?: string[] }) {
  const isAdmin = roles?.includes("ADMIN") ?? false;
  const visibleTabs = isAdmin
    ? [...TABS, { key: "users", label: "Users", path: "/users", Icon: Users }]
    : TABS;
  // ...use visibleTabs instead of TABS
}
```
Import `Users` from `"lucide-react"` — already a dependency. No other changes to TopNav.

### Forbidden State on `/users` for USER Role

```tsx
if (forbidden) {
  return (
    <main className="flex-1 flex items-center justify-center">
      <div className="text-center text-gray-500">
        <p className="text-[16px] font-medium">Access denied</p>
        <p className="text-[14px] mt-1">You do not have permission to manage users.</p>
      </div>
    </main>
  );
}
```
Set `forbidden = true` when `apiClient.getUsers()` throws/rejects with 403.

### Table Date Formatting

`created_at` is an epoch int. Reuse or copy `fmtTs()` from MonitorPage for consistent date display.

### Architecture Compliance

- No `border-l-*` decorative accents on status badges or table rows (CLAUDE.md rule).
- Status badge: use rounded pill with background, e.g. `bg-emerald-50 text-emerald-800` for active, `bg-gray-100 text-gray-600` for inactive.
- All API calls through `apiClient` methods — no direct fetch.
- No inline `style={}` attributes — use Tailwind classes.
- No comments unless code is non-obvious.

### Regression Guardrails

- Do NOT change `authToken.getUsername()`, `authToken.get()`, `authToken.clear()`, `authToken.isAuthenticated()` — all existing auth flows depend on them.
- Do NOT change TopNav `TABS` const — compute `visibleTabs` at render time.
- Do NOT modify `ProtectedRoute` — it only checks authentication (token present and valid), not roles.
- Do NOT remove any existing routes from `APP_ROUTES`.
- Do NOT change `AppShell` layout or `DDRUploadModal` integration.
- Existing `TopNav` tests (if any) must still pass — the component remains usable without `roles` prop (default to no admin tab).

### References

- Story source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md`
- auth.ts: `ces-ddr-platform/ces-frontend/src/lib/auth.ts`
- AppShell: `ces-ddr-platform/ces-frontend/src/components/AppShell.tsx`
- TopNav: `ces-ddr-platform/ces-frontend/src/components/TopNav.tsx`
- routes.ts: `ces-ddr-platform/ces-frontend/src/routes.ts`
- api.ts: `ces-ddr-platform/ces-frontend/src/lib/api.ts`
- ProtectedRoute: `ces-ddr-platform/ces-frontend/src/components/ProtectedRoute.tsx`
- MonitorPage (fmtTs helper): `ces-ddr-platform/ces-frontend/src/pages/MonitorPage.tsx`

## Story Context Completion

Ultimate context engine analysis completed — minimal extension of `AuthToken`, `TopNav`, `AppShell`, `routes.ts`, and `api.ts`; new `UserManagementPage` follows existing page patterns.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
