# Story 1.4: Frontend Authentication Shell & Protected Routing

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want a login page and protected app shell,
so that unauthenticated users are redirected to login and authenticated users can navigate the platform.

## Acceptance Criteria

1. Given a user navigates to any route other than `/login` without a valid token in `localStorage`, when `<ProtectedRoute>` evaluates the token, then user is redirected to `/login`.
2. Given a user submits valid credentials on `LoginPage.tsx`, when `POST /auth/login` succeeds, then JWT is stored in `localStorage` via `src/lib/auth.ts`, user is redirected to `/`, and page loads within 2 seconds on internal network.
3. Given a user submits invalid credentials on `LoginPage.tsx`, when API returns HTTP 401, then inline error message displays below the form as `Invalid username or password`, password field is cleared, and username field retains value.
4. Given `src/lib/api.ts` typed API client is in use, when any API call returns HTTP 401, then `localStorage` token is cleared and user is redirected to `/login`.
5. Given any component or hook calls the API, when request is sent, then `Authorization: Bearer <token>` is included automatically by `src/lib/api.ts`, and components do not call raw `fetch()`.
6. Given `App.tsx` uses React Router, when routes are inspected, then `/login`, `/`, `/reports/:id`, `/history`, `/query`, `/monitor`, and `/settings/keywords` are declared, and all routes except `/login` are wrapped in `<ProtectedRoute>`.
7. Given frontend config is inspected, when API base URL is needed, then it is read from `VITE_API_URL` and is never hardcoded in page, component, hook, or API client code.

## Tasks / Subtasks

- [ ] Add routing dependency and test dependencies (AC: 1, 6)
  - [ ] Add `react-router` using current stable v7 line; use Declarative Mode APIs compatible with existing Vite SPA.
  - [ ] Add Vitest, React Testing Library, `@testing-library/jest-dom`, `@testing-library/user-event`, and jsdom.
  - [ ] Add `test` script and Vite/Vitest config needed for React component tests.
- [ ] Add auth token helper module (AC: 1, 2, 4)
  - [ ] Create `ces-frontend/src/lib/auth.ts`.
  - [ ] Encapsulate token storage, retrieval, clearing, and lightweight expiry checks in exported helper methods.
  - [ ] Store only JWT token; do not store username, password, roles, or decoded user profile.
  - [ ] Treat missing, malformed, or expired token as unauthenticated and clear it.
- [ ] Add typed API client (AC: 2, 4, 5, 7)
  - [ ] Create `ces-frontend/src/lib/api.ts`.
  - [ ] Read base URL from `import.meta.env.VITE_API_URL`; keep auth requests pointed at backend `/auth/login` and do not hardcode backend host elsewhere.
  - [ ] Implement typed `login(credentials)` for `POST /auth/login`.
  - [ ] Implement shared request method that injects bearer token from `auth.ts`.
  - [ ] On any HTTP 401 response, clear token and redirect to `/login`.
  - [ ] Parse backend error shape without leaking raw response internals into UI.
- [ ] Build login page (AC: 2, 3)
  - [ ] Create `ces-frontend/src/pages/LoginPage.tsx`.
  - [ ] Use existing `Button` primitive from `src/components/ui/button.tsx`; add a small local input pattern or shadcn-style `Input` primitive only if needed.
  - [ ] Keep design quiet, desktop-first, CES-branded, and consistent with existing `styles.css` tokens.
  - [ ] On success, store token through `auth.ts` and navigate to `/`.
  - [ ] On invalid credentials, show exact inline text `Invalid username or password`, clear password, retain username, and keep focus behavior usable.
- [ ] Add protected app shell and placeholder pages (AC: 1, 6)
  - [ ] Create `ces-frontend/src/components/ProtectedRoute.tsx`.
  - [ ] Update `App.tsx` to declare all required routes.
  - [ ] Preserve existing DDR Operations Console content as `/` dashboard placeholder instead of deleting the scaffold.
  - [ ] Add placeholder page components for `/reports/:id`, `/history`, `/query`, `/monitor`, and `/settings/keywords` under `src/pages/`.
  - [ ] Keep placeholders functional and minimal; do not implement upload, table, query, monitor, export, or keyword editing features in this story.
- [ ] Add auth hook only if it removes duplication (AC: 1-4)
  - [ ] Prefer small `useAuth` in `src/hooks/useAuth.ts` if LoginPage and ProtectedRoute otherwise duplicate storage/navigation behavior.
  - [ ] Keep state local with React `useState` and `useEffect`; do not add Redux, Zustand, React Query, or external state library.
- [ ] Add tests (AC: 1-7)
  - [ ] Test unauthenticated protected route redirects to `/login`.
  - [ ] Test valid login stores token and navigates to `/`.
  - [ ] Test invalid login shows exact inline error, clears password, and retains username.
  - [ ] Test API client injects `Authorization: Bearer <token>`.
  - [ ] Test API client clears token and redirects to `/login` on 401.
  - [ ] Test all required routes are declared and protected except `/login`.
  - [ ] Test `VITE_API_URL` usage without hardcoded backend URL in `api.ts`.
- [ ] Preserve scope boundaries (AC: all)
  - [ ] Do not add backend auth implementation, seeded credentials, RBAC, refresh tokens, password reset, user management, SSR, React Router Framework Mode, or business feature screens.
  - [ ] Do not modify `src/components/ui/` primitives unless a primitive is missing and needed for auth UI.
  - [ ] Do not read or print real `.env` values.

## Dev Notes

### Current Sprint State

Story 1.3 is `ready-for-dev`, not `done`, so frontend integration may need mocked API responses or dev-server contract assumptions until backend auth is implemented. Do not create a fake credential store in the frontend to bypass the backend. The frontend should call `POST /auth/login` exactly as specified and rely on backend 401 handling when available. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]

Story 1.2 is in `review` and changed migration/schema artifacts in the working tree. This story does not need database changes. Leave backend and shared schema files untouched unless a test fixture needs contract-only JSON under shared test fixtures. [Source: _bmad-output/implementation-artifacts/stories/1-2-database-schema-users-table-migration-tooling.md]

### Existing Frontend State

Current frontend is a minimal Vite React scaffold:

- `ces-ddr-platform/ces-frontend/src/App.tsx` renders the dashboard scaffold with `app-shell`, `workspace`, `workspace-header`, and `status-grid`.
- `src/main.tsx` renders `<App />` inside `StrictMode`.
- `src/styles.css` defines Tailwind 4 import, CES tokens, app shell layout, button styles, and responsive status grid.
- `src/components/ui/button.tsx` provides a shadcn-style `Button` primitive using `class-variance-authority`, Radix `Slot`, and `cn`.
- `src/lib/utils.ts` provides `cn`.
- `vite.config.ts` loads `VITE_API_URL`, defaults dev proxy target to `http://localhost:8000`, and proxies `/api` to backend with prefix rewrite.
- `.env.example` contains `VITE_API_URL=http://localhost:8000`.

Update these files in place. Do not replace the scaffold with a landing page. The first protected screen should remain an operations console placeholder. [Source: ces-ddr-platform/ces-frontend/src/App.tsx] [Source: ces-ddr-platform/ces-frontend/src/styles.css] [Source: ces-ddr-platform/ces-frontend/vite.config.ts]

### Auth Contract

Login endpoint:

```text
POST /auth/login
```

Request:

```json
{ "username": "string", "password": "string" }
```

Success:

```json
{ "token": "<JWT>", "expires_at": "<ISO8601 8hr from now>" }
```

Invalid credentials:

```json
{ "error": "Invalid credentials", "code": "UNAUTHORIZED", "details": {} }
```

Frontend UI maps invalid credentials to exactly `Invalid username or password`. Do not show backend raw error text directly. Preserve JSON field names exactly. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4] [Source: _bmad-output/implementation-artifacts/stories/1-3-authentication-api-login-jwt-middleware.md#Auth Contract]

### Token Handling

Use `localStorage` for V1 token storage because architecture explicitly allows it for this internal tool. Keep all access in `src/lib/auth.ts`; no direct `localStorage` calls in pages/components except tests. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]

Frontend cannot verify HS256 signatures because `JWT_SECRET` must never ship to browser. `ProtectedRoute` should treat a token as usable only if present and not expired according to decoded `exp`; server 401 remains the authority for signature validity. Malformed token means clear token and redirect to `/login`. Do not add client-side JWT verification libraries that require secrets. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]

### Routing Requirements

Architecture originally says React Router v6, but current official React Router docs show latest branch `7.15.0` and Declarative Mode still exposes `BrowserRouter`, `Routes`, `Route`, `Navigate`, `useNavigate`, `useLocation`, and related APIs. Use v7 Declarative Mode for the existing Vite SPA unless the project explicitly pins v6 before implementation. Do not adopt Framework Mode or file-based routing; it would add architecture churn this story does not need. [Source: https://reactrouter.com/start/modes]

Required routes:

```text
/login
/
/reports/:id
/history
/query
/monitor
/settings/keywords
```

All routes except `/login` must be wrapped by `<ProtectedRoute>`. Preserve intended destination when redirecting to login if simple to do with `location.state.from`; after successful login, default redirect is `/` per acceptance criteria. [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture] [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]

### API Client Requirements

All frontend API calls go through `src/lib/api.ts`; components and hooks must not call raw `fetch()`. API client injects bearer token from `auth.ts` on every non-login request. Any 401 clears token and redirects to `/login`. [Source: _bmad-output/planning-artifacts/architecture.md#Frontend API Client Pattern]

Base URL must come from `VITE_API_URL`. Existing Vite proxy only handles `/api` and rewrites it to backend root, while auth contract is backend path `/auth/login`. Safest implementation is `const API_BASE_URL = import.meta.env.VITE_API_URL` and login request to `${API_BASE_URL}/auth/login`. Do not use an empty-origin fallback unless `vite.config.ts` is explicitly updated and tested to proxy `/auth/login` correctly. [Source: ces-ddr-platform/ces-frontend/vite.config.ts] [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]

### UI And UX Guardrails

This is an internal operational tool, not a marketing page. Login and shell should be restrained, high-contrast, and fast to scan. Use CES red `#C41230` as accent, neutral surfaces, 8px or smaller radii, and compact desktop-first layout. Do not add decorative gradients, large hero sections, or unrelated feature explanations. [Source: _bmad-output/planning-artifacts/prd.md#Project-Type Overview] [Source: _bmad-output/planning-artifacts/ux-design-specification.md]

All authenticated users have identical full access. Do not create role checks, disabled nav items by role, or permission-based route branches. [Source: _bmad-output/planning-artifacts/prd.md#System Configuration & Access]

### File Structure Requirements

Expected files to create or update:

```text
ces-ddr-platform/ces-frontend/package.json
ces-ddr-platform/ces-frontend/package-lock.json
ces-ddr-platform/ces-frontend/vite.config.ts
ces-ddr-platform/ces-frontend/src/App.tsx
ces-ddr-platform/ces-frontend/src/components/ProtectedRoute.tsx
ces-ddr-platform/ces-frontend/src/lib/auth.ts
ces-ddr-platform/ces-frontend/src/lib/api.ts
ces-ddr-platform/ces-frontend/src/pages/LoginPage.tsx
ces-ddr-platform/ces-frontend/src/pages/DashboardPage.tsx
ces-ddr-platform/ces-frontend/src/pages/ReportsPage.tsx
ces-ddr-platform/ces-frontend/src/pages/HistoryPage.tsx
ces-ddr-platform/ces-frontend/src/pages/QueryPage.tsx
ces-ddr-platform/ces-frontend/src/pages/MonitorPage.tsx
ces-ddr-platform/ces-frontend/src/pages/KeywordsPage.tsx
ces-ddr-platform/ces-frontend/src/test/setup.ts
```

Optional, if useful:

```text
ces-ddr-platform/ces-frontend/src/hooks/useAuth.ts
ces-ddr-platform/ces-frontend/src/types/api.ts
```

Keep frontend naming aligned: components and pages use `PascalCase`, hooks use `use` prefix, API client functions use camelCase verbs. [Source: _bmad-output/planning-artifacts/architecture.md#Naming Conventions]

### Dependency Guidance

Current frontend dependencies include React `19.2.5`, React DOM `19.2.5`, Vite `8.0.10`, TypeScript `6.0.3`, Tailwind `4.2.4`, `@tailwindcss/vite`, Radix Slot, CVA, clsx, and tailwind-merge. Do not downgrade Tailwind to v3 just because architecture text predates current scaffold. Keep Tailwind 4 setup through `@tailwindcss/vite`. [Source: ces-ddr-platform/ces-frontend/package.json]

Current npm metadata checked on 2026-05-06:

- `react-router`: `7.15.0`
- `@testing-library/react`: `16.3.2`
- `vitest`: `4.1.5`
- `jsdom`: `29.1.1`

Install only what this story needs. Prefer `react-router` v7 docs import path over adding both `react-router` and `react-router-dom`. [Source: https://reactrouter.com/start/modes]

### Previous Story Intelligence

Story 1.3 prepared backend auth contract but is not implemented in working tree yet. Its guidance established:

- `POST /auth/login` response is direct JSON, no wrapper.
- Bad credentials use `Invalid credentials` backend error, but frontend shows user-safe copy.
- Token lifetime is 8 hours and JWT payload has `user_id` and `exp`.
- No refresh tokens, roles, RBAC, password reset, user management UI, or frontend login UI was included there.
- Existing exact health responses must remain backend concerns and not be changed by frontend work.

Story 1.2 review notes show prior implementation changed files and sprint status in the working tree. Do not revert or overwrite those unrelated changes. [Source: _bmad-output/implementation-artifacts/stories/1-3-authentication-api-login-jwt-middleware.md] [Source: _bmad-output/implementation-artifacts/stories/1-2-database-schema-users-table-migration-tooling.md]

### Git Intelligence

Recent committed history is shallow:

- `8e97969 change readme path`
- `61cae65 Initial Scaffolding`

Current working tree is dirty with prior Story 1.2 and Story 1.3 artifacts. Treat those as user or previous-agent work. Only modify frontend files and this story's status during implementation. [Source: git log -5 --oneline] [Source: git status --short]

### Testing Requirements

Run frontend checks from `ces-ddr-platform/ces-frontend/`:

```bash
npm run build
npm run test
```

Add focused unit/component tests with Vitest and React Testing Library. Mock `fetch`, `localStorage`, and navigation behavior where appropriate. Tests should prove route protection and API client behavior without requiring live backend. If backend Story 1.3 is implemented locally, a manual smoke test can verify valid login against backend, but automated frontend tests should not depend on a live server.

### Project Structure Notes

No conflict with backend architecture. This story is frontend-only except package lock updates. Current scaffold already has the right root path `ces-ddr-platform/ces-frontend/`; do not create another frontend app or move files.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend API Client Pattern]
- [Source: _bmad-output/planning-artifacts/prd.md#System Configuration & Access]
- [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md]
- [Source: ces-ddr-platform/ces-frontend/package.json]
- [Source: ces-ddr-platform/ces-frontend/src/App.tsx]
- [Source: ces-ddr-platform/ces-frontend/vite.config.ts]
- [Source: https://reactrouter.com/start/modes]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
