# Sprint Change Proposal: AI Avatar B2C-Style RBAC and User Management

**Project:** Canadian Energy Service Internal Tool  
**Date:** 2026-05-25 11:23:30 IST  
**Requested by:** Het  
**Status:** Approved for implementation  
**Change trigger:** Access model must change from one full-access role to RBAC matching the pattern used in `Desktop/AI Avatar B2C`: role table, user-role join table, role checker dependencies, seeded roles/admin, admin-only APIs, and admin-only User Management navigation.

## 1. Issue Summary

Current CES planning artifacts repeatedly say V1 has one authenticated role and no RBAC. That is no longer correct.

The revised requirement is not just a `users.role` column. CES should implement the same RBAC pattern used in `Desktop/AI Avatar B2C`:

- Separate `roles` table.
- Join table between users and roles.
- Seed `ADMIN` and `USER` roles.
- Seed initial admin account and assign `ADMIN` through the join table.
- Use reusable role-check dependencies like `admin_only`, `user_only`, and `admin_or_user`.
- Admin can create users and deactivate users.
- Admin-only APIs are protected by backend role dependency.
- Frontend shows User Management tab only when authenticated user has `ADMIN` role.
- Regular users do not see the tab and cannot access user management APIs.

Do not copy AI Avatar B2C implementation blindly. Adopt the RBAC architecture pattern, but keep CES rules: `decouple + BackendBaseSettings`, Alembic under `src/repository/migrations`, SQLAlchemy async repositories, service classes, epoch timestamps, no hardcoded admin password, no `os.getenv`, no comments unless necessary, and no blocking sync calls in async routes.

## 2. AI Avatar B2C Reference Pattern

Observed source pattern from `/home/het/Desktop/AI Avatar B2C`:

- DB model: `Account` has many-to-many relationship to `Role` through `account_role`.
- DB tables: `role`, `account_role`.
- Role names: `ADMIN`, `USER`.
- Auth: `jwt_authentication` loads current user and eager-loads roles.
- Authorization: `RoleChecker(allowed_roles)` checks current user roles and raises unauthorized if no allowed role matches.
- Reusable dependencies:
  - `admin_only = RoleChecker(["ADMIN"])`
  - `user_only = RoleChecker(["USER"])`
  - `admin_or_user = RoleChecker(["ADMIN", "USER"])`
- Admin route pattern: `dependencies=[Depends(admin_only)]`.
- Seeding pattern: create roles if missing, then assign role to admin through join table.
- Inactive account pattern: auth rejects inactive users.

CES adaptation:

- Use `users`, `roles`, and `user_roles` naming to match current project naming conventions.
- Use SQLAlchemy async repository/service pattern instead of raw SQL scripts.
- Seed through Alembic data migration or explicit seed service/command loaded through settings.
- Keep JWT payload useful for frontend, but always enforce role permissions from backend-loaded DB roles.

## 3. Impact Analysis

### Epic Impact

Epic 1 is historically affected because users/auth were implemented without RBAC. Completed stories stay done, but their no-role guidance is superseded by this approved change.

Epic 7 is the right active target because it already covers System Administration. Add RBAC and user management there instead of rewriting completed Epic 1.

Recommended Epic 7 adjustment:

- Keep Story 7.1 for pipeline queue/status API.
- Keep Story 7.2 for error log and re-run API.
- Keep Story 7.3 for keyword management API.
- Add backend RBAC/user-management story.
- Add frontend User Management UI story.

### Story Impact

Affected story areas:

- Story 1.2 historical schema: superseded by new RBAC migrations adding `roles` and `user_roles`, plus `users.is_active`.
- Story 1.3 login: must reject inactive users and allow current-user auth to load roles.
- Story 1.4 frontend auth shell: previous “no roles/RBAC/user management” guardrail is superseded.
- Story 7.4 Monitor Dashboard & Keyword Editor UI: User Management should be separate to avoid scope bloat.
- New Story 7.5 should implement RBAC backend.
- New Story 7.6 should implement admin User Management UI.

### Artifact Conflicts

PRD conflicts:

- Project classification says single role.
- MVP scope says single authenticated user role.
- Domain security says no RBAC required.
- FR35 says all authenticated users have identical full access.

Architecture conflicts:

- Users table has no active-state or RBAC association.
- Auth section says no role differentiation.
- JWT/auth dependencies do not mention role loading or role checker dependencies.
- API routes do not include admin user management.

UX conflicts:

- Target users say no role differentiation.
- Navigation has no admin-only User Management tab.

Sprint status conflicts:

- Epic 7 has no RBAC/user management stories.

### Technical Impact

Backend changes needed:

- Add `users.is_active BOOLEAN NOT NULL DEFAULT true`.
- Add `roles` table: `id`, `name`, `description`, `created_at`, `updated_at`.
- Add `user_roles` join table: `user_id`, `role_id`, primary key `(user_id, role_id)`.
- Seed roles: `ADMIN`, `USER`.
- Seed first admin user from settings and assign `ADMIN` role through `user_roles`.
- Add `RoleCRUDRepository` or equivalent repository.
- Extend `UserCRUDRepository` to load roles.
- Add `RoleChecker` class under `src/securities/authorizations/rbac.py` or equivalent.
- Export reusable dependencies: `admin_only`, `user_only`, `admin_or_user`.
- Auth dependency must load current active user with roles.
- Login must reject inactive users with same invalid-credentials response to avoid account-state enumeration.
- User creation must assign default `USER` role unless admin explicitly assigns allowed role.
- User deactivation sets `is_active=false`; no hard delete.
- Password hashes never returned.
- All routes remain async and use service/repository classes.

Frontend changes needed:

- Auth token/profile logic must expose roles or call `/auth/me` / `/users/me` to retrieve roles.
- TopNav shows User Management only if roles include `ADMIN`.
- Add `/users` or `/admin/users` route.
- User Management page lists users, creates users, deactivates users.
- UI route guard is convenience only; backend remains security boundary.

## 4. Recommended Approach

Recommended path: Direct Adjustment.

Rationale:

- Product scope mostly unchanged.
- AI Avatar B2C RBAC pattern is known and reusable.
- Separate `roles` + `user_roles` is more flexible than a single `users.role` column.
- Admin/user distinction now has strong backend enforcement, not just hidden nav.
- Epic 7 can absorb this cleanly without reopening completed Epic 1 work.

Effort: Medium.

Risk: Medium.

Timeline impact: Add one backend RBAC/admin story and one frontend User Management story before closing Epic 7.

Scope classification: Moderate.

## 5. Detailed Change Proposals

### PRD: Project Classification

OLD:

```md
| Access Model | Single role — all authenticated users have full access |
```

NEW:

```md
| Access Model | RBAC with ADMIN and USER roles. Roles are stored in a roles table and assigned through a user_roles join table, following the AI Avatar B2C pattern. ADMIN users can create and deactivate users and see User Management navigation. USER accounts use core DDR workflows and cannot access user management. |
```

Rationale: Replaces single-role V1 with real RBAC.

### PRD: MVP Scope

OLD:

```md
Single authenticated user role — all users have full access to all features
```

NEW:

```md
Authenticated access with RBAC. ADMIN and USER roles are seeded/assigned through roles and user_roles tables. A seeded ADMIN account can create users and deactivate users. USER accounts do not see User Management navigation and cannot call user management APIs.
```

Rationale: Captures requested AI Avatar B2C-style RBAC.

### PRD: Domain Data Sensitivity & Access Control

OLD:

```md
Single user role: all authenticated users have full access — upload, query, edit, export, pipeline management, keyword list editing. No RBAC required for V1.
```

NEW:

```md
RBAC applies to system administration. Active authenticated users with USER or ADMIN roles can use core DDR workflows unless a later story restricts a workflow. ADMIN users additionally manage accounts: create users and deactivate users. User management APIs are admin-only through backend role-check dependencies. Hidden frontend navigation is not the security boundary.
```

Rationale: Keeps product workflows open while restricting account administration.

### PRD: Functional Requirements

OLD:

```md
FR35: All authenticated users have identical full access to all system capabilities
```

NEW:

```md
FR35: Active authenticated users with USER or ADMIN role can access core platform workflows.
FR36: System stores roles in a roles table and assigns them through a user_roles join table.
FR37: System seeds ADMIN and USER roles plus an initial ADMIN account.
FR38: ADMIN users can create users.
FR39: ADMIN users can deactivate users.
FR40: USER accounts cannot access user management APIs or see User Management navigation.
```

Rationale: Makes RBAC testable.

### Architecture: Data Architecture

OLD:

```md
users table: id UUID, username, password_hash, created_at, updated_at
```

NEW:

```md
users table: id UUID, username, password_hash, is_active, created_at, updated_at.
roles table: id UUID, name, description, created_at, updated_at.
user_roles table: user_id UUID, role_id UUID, primary key (user_id, role_id).
Seeded role names: ADMIN, USER.
All timestamps use epoch integer columns.
```

Rationale: Matches AI Avatar B2C RBAC structure while preserving CES naming.

### Architecture: Authentication & Security

OLD:

```md
No refresh tokens for V1 — re-login on expiry. All protected routes require Bearer JWT.
```

NEW:

```md
No refresh tokens for V1 — re-login on expiry. All protected routes require Bearer JWT. Auth dependency loads the current active user with assigned roles. Inactive users cannot authenticate. RBAC uses a RoleChecker dependency pattern with admin_only, user_only, and admin_or_user reusable dependencies. Backend role checks guard admin endpoints even if frontend nav is hidden.
```

Rationale: Makes role enforcement backend-owned.

### Architecture: JWT Payload and Current User

OLD:

```md
JWT payload contains user_id and exp claims.
```

NEW:

```md
JWT payload contains user_id, username, exp, and optionally roles for frontend navigation. Backend authorization does not trust roles from token alone; it loads current user roles from DB before applying RoleChecker.
```

Rationale: Allows admin-only nav without weakening server authorization.

### Architecture: RBAC Dependency Pattern

NEW:

```md
RoleChecker accepts allowed role names and checks current_user.roles.
Reusable dependencies:
- admin_only = RoleChecker(["ADMIN"])
- user_only = RoleChecker(["USER"])
- admin_or_user = RoleChecker(["ADMIN", "USER"])
Admin-only route pattern: dependencies=[Depends(admin_only)].
```

Rationale: Directly mirrors AI Avatar B2C.

### Architecture: Admin Seeding

OLD:

```md
Static credentials stored bcrypt-hashed.
```

NEW:

```md
Seed ADMIN and USER roles idempotently. Seed initial admin account from settings loaded through decouple + BackendBaseSettings, with bcrypt-hashed password and ADMIN role assignment through user_roles. No default plaintext admin password is committed. Seed process never logs password or hash.
```

Rationale: Same RBAC structure, CES-safe seeding.

### Architecture: API Routes

OLD:

```md
POST /api/auth/login
```

NEW:

```md
POST /api/auth/login
GET /api/users                    ADMIN only
POST /api/users                   ADMIN only
PATCH /api/users/:id/deactivate   ADMIN only
```

Optional later route:

```md
GET /api/auth/me or GET /api/users/me returns safe current user profile with roles.
```

Rationale: Minimal user management surface.

### UX: Target Users

OLD:

```md
All three users are authenticated internal CES staff with identical full access — no role differentiation in V1.
```

NEW:

```md
Users authenticate with assigned RBAC roles. ADMIN users see a User Management tab and can create or deactivate accounts. USER accounts do not see the tab and cannot access those APIs.
```

Rationale: Aligns UX with RBAC.

### UX: Navigation

OLD:

```md
Routes: /login, /, /reports/:id, /history, /query, /monitor, /settings/keywords
```

NEW:

```md
Routes: /login, /, /reports/:id, /history, /query, /monitor, /settings/keywords, /users.
The User Management tab appears in top navigation only when authenticated user roles include ADMIN.
```

Rationale: Implements user request.

### Epics: Requirements Inventory

OLD:

```md
FR35: All authenticated users have identical full access to all system capabilities
```

NEW:

```md
FR35: Active authenticated users with USER or ADMIN role can access core platform workflows.
FR36: System stores roles in a roles table and assigns them through a user_roles join table.
FR37: System seeds ADMIN and USER roles plus an initial ADMIN account.
FR38: ADMIN users can create users.
FR39: ADMIN users can deactivate users.
FR40: USER accounts cannot access user management APIs or see User Management navigation.
```

Rationale: Keeps epics aligned with PRD.

### Epics: Epic 7 Scope

OLD:

```md
Pipeline Monitoring & System Administration
Users can monitor pipeline queue + AI costs, drill into per-date extraction status, view raw error logs, re-run failed dates with manual date override, and update keyword rules without a code deploy.
```

NEW:

```md
Pipeline Monitoring & System Administration
Users can monitor pipeline queue + AI costs, drill into per-date extraction status, view raw error logs, re-run failed dates with manual date override, update keyword rules without a code deploy, and ADMIN users can manage user accounts through RBAC-protected APIs.
```

Rationale: User management belongs in System Administration.

### Epics: Add Story 7.5 Backend RBAC and User Management

NEW STORY:

```md
### Story 7.5: RBAC Schema, Seeded Admin, and Admin User Management API

As a platform admin,
I want RBAC with seeded ADMIN/USER roles and admin-only user management APIs,
So that account administration follows the established AI Avatar B2C authorization pattern.

Acceptance Criteria:

Given Alembic migrations run
When schema is inspected
Then users table includes is_active boolean default true
And roles table exists with id, name, description, created_at, updated_at
And user_roles join table exists with user_id, role_id, and composite primary key
And all timestamps are epoch integers

Given seed process runs
When ADMIN and USER roles do not exist
Then both roles are created idempotently
And initial admin user is created from settings if missing
And admin user is assigned ADMIN role through user_roles
And password is bcrypt-hashed and never logged

Given auth dependency validates a JWT
When current user is loaded
Then assigned roles are loaded from DB
And inactive users are rejected

Given RoleChecker is used
When admin_only, user_only, or admin_or_user dependencies run
Then access is granted only if current user has at least one allowed role
And insufficient role returns standard forbidden/unauthorized error shape

Given an ADMIN JWT calls GET /api/users
When users exist
Then HTTP 200 returns safe user records with id, username, is_active, roles, created_at, updated_at
And password_hash is never returned

Given an ADMIN JWT calls POST /api/users
When username is unique and password is valid
Then user is created with hashed password, is_active=true, and USER role by default
And HTTP 201 returns safe user fields

Given an ADMIN JWT calls PATCH /api/users/:id/deactivate
When target user exists
Then user.is_active becomes false and updated_at refreshes
And HTTP 200 returns safe user fields

Given USER JWT calls any user management endpoint
When request reaches backend
Then HTTP 403 or project-standard unauthorized response is returned
```

Rationale: Backend RBAC first, using AI Avatar B2C structure.

### Epics: Add Story 7.6 Admin User Management UI

NEW STORY:

```md
### Story 7.6: Admin User Management UI

As a platform admin,
I want a User Management tab and page,
So that I can create and deactivate users from the app.

Acceptance Criteria:

Given authenticated user roles include ADMIN
When TopNav renders
Then User Management tab is visible
And it links to /users

Given authenticated user roles do not include ADMIN
When TopNav renders
Then User Management tab is hidden

Given a USER navigates directly to /users
When route guard and API request run
Then UI shows forbidden state or redirects
And backend denies user management APIs

Given ADMIN opens /users
When users are loaded
Then table shows username, roles, active status, created_at, updated_at
And password_hash is never displayed

Given ADMIN creates a user
When username and password are submitted
Then POST /api/users is called through src/lib/api.ts
And created user appears in table with USER role

Given ADMIN deactivates a user
When confirmation is accepted
Then PATCH /api/users/:id/deactivate is called
And row status changes to inactive
```

Rationale: Requested admin-only nav and user management UX.

### Sprint Status

OLD:

```yaml
epic-7: backlog
7-1-pipeline-queue-per-date-status-api: backlog
7-2-error-log-per-date-re-run-api: backlog
7-3-keyword-management-api: backlog
7-4-monitor-dashboard-keyword-editor-ui: backlog
```

NEW:

```yaml
epic-7: backlog
7-1-pipeline-queue-per-date-status-api: backlog
7-2-error-log-per-date-re-run-api: backlog
7-3-keyword-management-api: backlog
7-4-monitor-dashboard-keyword-editor-ui: backlog
7-5-rbac-schema-seeded-admin-user-management-api: backlog
7-6-admin-user-management-ui: backlog
```

Rationale: Tracks RBAC implementation without renumbering existing backlog stories.

## 6. Checklist Status

- [x] 1.1 Triggering story identified: Epic 7 start exposed missing admin/user management and RBAC scope.
- [x] 1.2 Core problem defined: single-role artifacts conflict with new RBAC requirement.
- [x] 1.3 Evidence gathered: user requested AI Avatar B2C RBAC; reference project uses role table, join table, RoleChecker dependencies, ADMIN/USER roles, inactive user check, admin route dependencies.
- [x] 2.1 Current epic assessed: Epic 7 can absorb RBAC/user management.
- [x] 2.2 Epic-level changes identified: add RBAC backend and user management UI stories.
- [x] 2.3 Remaining epics reviewed: completed Epic 1 behavior extended by new migration/service story.
- [x] 2.4 No future epics invalidated.
- [x] 2.5 Priority change needed: add RBAC before Epic 7 closes.
- [x] 3.1 PRD impact reviewed: access model and FR35 need replacement.
- [x] 3.2 Architecture impact reviewed: roles schema, join table, auth dependency, RoleChecker, seeded admin, routes affected.
- [x] 3.3 UX impact reviewed: admin-only User Management nav/page affected.
- [x] 3.4 Other artifacts reviewed: sprint status needs new story keys after approval.
- [x] 4.1 Direct Adjustment viable: medium effort, medium risk.
- [N/A] 4.2 Rollback not needed.
- [N/A] 4.3 MVP Review not needed.
- [x] 4.4 Recommended path selected: Direct Adjustment.
- [x] 5.1 Issue summary created.
- [x] 5.2 Epic and artifact impacts documented.
- [x] 5.3 Recommended path documented.
- [x] 5.4 MVP impact defined: no scope reduction, moderate RBAC/admin expansion.
- [x] 5.5 Handoff plan defined.
- [x] 6.3 Explicit user approval captured on 2026-05-25.
- [x] 6.4 sprint-status updated with approved RBAC change and new Epic 7 story keys.

## 7. Implementation Handoff

Recommended next implementation sequence:

1. Approve this revised proposal.
2. Update PRD, architecture, UX, epics, and sprint status with accepted RBAC changes.
3. Create Story 7.5 for backend RBAC/schema/seeding/user management APIs.
4. Create Story 7.6 for frontend User Management UI.
5. Implement 7.5 before 7.6.
6. Run backend tests from activated UV virtualenv.
7. Run frontend tests after nav/page changes.

Handoff recipients:

- Developer agent for implementation.
- Story workflow for context-rich 7.5 and 7.6 story files.

Success criteria:

- `roles` and `user_roles` exist and work like AI Avatar B2C RBAC pattern.
- ADMIN and USER roles are seeded.
- Initial admin is seeded from settings and assigned ADMIN through user_roles.
- Inactive users cannot authenticate.
- Admin can create/deactivate users.
- USER cannot call admin user-management APIs.
- User Management tab appears only for ADMIN.
- No core DDR workflows regress.
