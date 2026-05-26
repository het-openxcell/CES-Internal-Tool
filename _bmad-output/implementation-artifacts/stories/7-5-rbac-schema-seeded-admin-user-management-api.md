# Story 7.5: RBAC Schema, Seeded Admin, and Admin User Management API

Status: done

## Story

As a platform admin,
I want RBAC with seeded ADMIN/USER roles and admin-only user management APIs,
so that account administration follows the established AI Avatar B2C authorization pattern.

## Acceptance Criteria

1. Given Alembic migrations run, then `users` table includes `is_active BOOLEAN NOT NULL DEFAULT true`, `roles` table exists with `id UUID PK`, `name VARCHAR`, `description VARCHAR`, `created_at`, `updated_at` (epoch ints), and `user_roles` join table exists with `user_id UUID`, `role_id UUID`, composite primary key `(user_id, role_id)`.
2. Given seed process runs, then `ADMIN` and `USER` roles are created idempotently. Initial admin user is created from `ADMIN_USERNAME` / `ADMIN_PASSWORD` settings if not already present and assigned `ADMIN` role through `user_roles`. Password is bcrypt-hashed and never logged.
3. Given `POST /api/auth/login` is called with valid credentials for an inactive user, then HTTP 401 returns the same `InvalidCredentialsException` (not a distinct "account inactive" error — no account-state enumeration).
4. Given `jwt_authentication` validates a JWT, then current user is loaded from DB WITH roles eagerly. Inactive users are rejected. `current_user.roles` is a list of `Role` objects accessible in the request.
5. Given JWT is generated on successful login, then payload includes `user_id`, `username`, and `roles: ["ADMIN"]` (or `["USER"]`) so the frontend can read role for navigation without an extra request.
6. Given `RoleChecker(["ADMIN"])` dependency is evaluated for a request, then HTTP 403 (or 401 — follow project exception pattern) is returned if current user's roles do not include any of the allowed roles. `admin_only`, `user_only`, `admin_or_user` reusable dependencies are exported from `src/securities/authorizations/rbac.py`.
7. Given `GET /api/users` is called with an ADMIN JWT, then HTTP 200 returns all users as `[{ id, username, is_active, roles: [string], created_at, updated_at }]`. `password_hash` is never returned.
8. Given `POST /api/users` is called with an ADMIN JWT and `{ "username": "...", "password": "..." }`, then user is created with bcrypt-hashed password, `is_active=true`, and `USER` role by default. HTTP 201 returns safe user fields.
9. Given `POST /api/users` is called with a duplicate username, then HTTP 400 (or 409) returns `{ "error": "Username already exists", "code": "USERNAME_CONFLICT", "details": {} }`.
10. Given `PATCH /api/users/{id}/deactivate` is called with an ADMIN JWT, then `users.is_active` becomes `false` and `updated_at` refreshes. HTTP 200 returns updated safe user fields.
11. Given `PATCH /api/users/{id}/deactivate` is called for a non-existent user, then HTTP 404 returns `{ "error": "User not found", "code": "NOT_FOUND", "details": {} }`.
12. Given any user management endpoint is called with a non-ADMIN JWT, then HTTP 403 is returned.
13. Given any user management endpoint is called without auth, then HTTP 401 is returned.
14. Given OpenAPI is generated, then `/api/users` (GET, POST) and `/api/users/{id}/deactivate` (PATCH) appear in `/openapi.json`.
15. Existing endpoints do not regress: login, DDR routes, monitor routes, keywords, corrections, exports, query.

## Tasks / Subtasks

- [x] Alembic migration: add `is_active` to users + create `roles` and `user_roles` tables (AC: 1)
  - [x] Create migration file `src/repository/migrations/versions/<date>_<seq>-013_rbac_schema.py`.
  - [x] `upgrade()`: `ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true`; create `roles` table; create `user_roles` join table with FK constraints and composite PK.
  - [x] `downgrade()`: drop `user_roles`, drop `roles`, `ALTER TABLE users DROP COLUMN is_active`.
  - [x] Follow existing migration file naming convention: `2026_05_26_0013-013_rbac_schema.py`.
- [x] Add `Role` and `UserRole` SQLAlchemy models (AC: 1)
  - [x] New file `src/models/db/role.py` with `Role(Base)` and `UserRole(Base)` models.
  - [x] `Role`: `id` (UUID PK, server_default gen_random_uuid()), `name` (String, unique, not null), `description` (Text, nullable), `created_at` (BigInteger, epoch server_default), `updated_at` (BigInteger, epoch server_default).
  - [x] `UserRole`: `user_id` (UUID FK → users.id), `role_id` (UUID FK → roles.id), composite PK `(user_id, role_id)`.
  - [x] Update `User` model in `src/models/db/user.py`: add `is_active: Mapped[bool]` column with `server_default=sqlalchemy.true()` and `nullable=False`.
  - [x] Import `Role`, `UserRole` in `src/models/db/__init__.py` so Alembic autogenerate sees them.
- [x] Add `RoleCRUDRepository` and extend `UserCRUDRepository` (AC: 2, 7, 8, 10)
  - [x] In `src/repository/crud/role.py`, create `RoleCRUDRepository(BaseCRUDRepository[Role])`.
  - [x] Extend `UserCRUDRepository` in `src/repository/crud/user.py` with all required methods.
  - [x] Eager-loading roles via `selectinload`; `lazy="noload"` on relationship.
- [x] Add seeding logic (AC: 2)
  - [x] Create `src/services/seed.py` with `SeedService`.
  - [x] Add `ADMIN_USERNAME` and `ADMIN_PASSWORD` to `BackendBaseSettings` via `decouple`.
  - [x] Call `SeedService.seed_roles_and_admin()` from application startup in `src/config/events.py`.
- [x] Update `jwt_authentication` to load roles and check `is_active` (AC: 3, 4)
  - [x] `get_current_user` eager-loads roles via `selectinload` and returns `None` for inactive users.
  - [x] `stream_query_token_authentication` uses updated `get_current_user`.
- [x] Update `generate_access_token` to include roles in JWT payload (AC: 5)
  - [x] `JWTUser` schema updated with `roles: list[str] = []`.
  - [x] `generate_access_token` reads `user.roles` and embeds names in token.
- [x] Update login to reject inactive users (AC: 3)
  - [x] Auth route nulls out inactive user before password check (same `InvalidCredentialsException`).
  - [x] Added `dummy_hash()` to `PasswordGenerator` for timing-safe rejection.
- [x] Add `RoleChecker` and reusable dependencies (AC: 6)
  - [x] Created `src/securities/authorizations/rbac.py` with `RoleChecker`, `admin_only`, `user_only`, `admin_or_user`.
  - [x] `ForbiddenException` added to `src/utilities/exceptions/exceptions.py` with handler registered in `main.py`.
- [x] Add user management schemas (AC: 7, 8, 10)
  - [x] Created `src/models/schemas/user.py` with `UserResponse` and `CreateUserRequest`.
- [x] Add user management route file (AC: 7–14)
  - [x] Created `src/api/routes/v1/users.py` with GET, POST, PATCH endpoints.
  - [x] Registered `users` router in `src/api/endpoints.py`.
- [x] Add backend tests (AC: 1–15)
  - [x] Created `tests/test_user_management_route.py` — 12 tests, all passing.
- [x] Run quality gates (AC: 15)
  - [x] `alembic upgrade head` — migration 013 applied successfully.
  - [x] `pytest` — 303 passed, 0 failures.
  - [x] `ruff check src tests` — all checks passed.

## Dev Notes

### Critical Context

- Backend-only story. No frontend changes (Story 7-6 handles UI).
- Reference pattern: `Desktop/AI Avatar B2C` RBAC architecture — `roles` table + `user_roles` join + `RoleChecker` dependency + `admin_only`/`user_only` exports. Adopt the PATTERN, not the code.
- `User` model currently has no `is_active`, no roles relationship — migration adds both.
- `jwt_authentication` currently doesn't load roles or check `is_active` — both must be added.
- Seeding must be idempotent — app can restart without creating duplicate roles or admin.

### DO NOT REIMPLEMENT — Reuse These

| Existing thing | Where | How to use in 7-5 |
|---|---|---|
| `BaseCRUDRepository` | `src/repository/crud/base.py` | Extend for `RoleCRUDRepository` |
| `UserCRUDRepository.find_by_username` | `src/repository/crud/user.py` | Use in seed check and login |
| `pwd_generator.hash_password` | `src/securities/hashing/password.py` | Use in `POST /api/users` and seed |
| `pwd_generator.is_password_authenticated` | `src/securities/hashing/password.py` | Unchanged in login route |
| `jwt_generator.generate_access_token` | `src/securities/authorizations/jwt.py` | Extend to include `roles` — don't rewrite |
| `jwt_authentication` dependency | `src/securities/authorizations/jwt_authentication.py` | Extend `get_current_user` to eager-load roles and check `is_active` |
| `InvalidCredentialsException` | `src/utilities/exceptions` | Reuse for inactive user rejection in login |
| `EntityDoesNotExist` | `src/utilities/exceptions` | Reuse in user management routes for 404 |
| Existing migration file pattern | `src/repository/migrations/versions/` | Follow exact naming: `2026_MM_DD_NNNN-NNN_name.py` |
| `BackendBaseSettings` + decouple | `src/config/settings/base.py` | Add `ADMIN_USERNAME`, `ADMIN_PASSWORD` using same `config()` pattern |
| `get_repository()` DI factory | `src/api/dependencies/repository.py` | Use for `RoleCRUDRepository` dependency |
| Test override pattern | `tests/test_pipeline_cost_route.py` | Use for user management route tests |

### SQLAlchemy Relationship for Role Loading

Add to `User` model in `src/models/db/user.py`:
```python
from sqlalchemy.orm import relationship
roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", lazy="noload")
```
Using `lazy="noload"` means roles are only loaded when explicitly requested with `selectinload`. This prevents breaking existing queries that don't need roles.

For `get_current_user` in `jwt_authentication.py`:
```python
from sqlalchemy.orm import selectinload
stmt = sqlalchemy.select(User).options(selectinload(User.roles)).where(User.id == user_id)
```

### `ForbiddenException`

If no `ForbiddenException` exists in `src/utilities/exceptions`, create it:
```python
class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "forbidden"):
        super().__init__(status_code=403, detail=detail)
```
Follow the existing exception pattern in `src/utilities/exceptions/exceptions.py`.

### Settings Addition

In `src/config/settings/base.py`:
```python
ADMIN_USERNAME: str = config("ADMIN_USERNAME", default="admin")
ADMIN_PASSWORD: str = config("ADMIN_PASSWORD")
```
`ADMIN_PASSWORD` has no default — must be set in `.env`. This forces explicit config on deploy.

### JWT Payload with Roles

After adding `roles` to `JWTUser`:
```python
class JWTUser(BaseSchemaModel):
    user_id: str
    username: str
    roles: list[str] = []
```

In `generate_access_token`:
```python
role_names = [r.name for r in getattr(user, "roles", [])]
token_data = JWTUser(user_id=str(user.id), username=user.username, roles=role_names).model_dump()
```

The `roles` are embedded in the JWT for frontend nav — backend always re-loads from DB for authorization decisions.

### UserResponse Role Format

`roles` in `UserResponse` is a list of role name strings (`["ADMIN"]` or `["USER"]`), not role objects. Convert at the service/route level:
```python
UserResponse(
    ...,
    roles=[r.name for r in user.roles],
)
```

### Architecture Compliance

- No `os.getenv`. All new settings via `decouple` in `BackendBaseSettings`.
- No standalone functions — all logic in service/repository classes.
- Seed service is a class method, not a loose function.
- All file I/O: none in this story (in-memory + DB).
- Blocking calls: `asyncio.to_thread()` if any sync SDK calls — only DB (async already) and bcrypt (sync — check if `pwd_generator.hash_password` is already wrapped).
- Epoch timestamps only — `int(time.time())` for `updated_at` in deactivate.

### Regression Guardrails

- Do not change existing login response shape (`LoginResponse`).
- Do not change `UserCRUDRepository.read_user_by_username` or `find_by_username` signatures.
- Do not change `jwt_generator.retrieve_details_from_token`.
- Do not add roles to `JWTToken` (`JWToken` model) — only to `JWTUser` payload data.
- Existing DDR/monitor/correction routes are NOT protected by `admin_only` — only user management routes are.
- All non-user-management routes keep `Depends(jwt_authentication)` only (no role check).

### References

- Story source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25.md`
- AI Avatar B2C RBAC pattern: `Desktop/AI Avatar B2C` (reference only — adopt pattern, not code)
- Current User model: `ces-ddr-platform/ces-backend/src/models/db/user.py`
- Current UserCRUDRepository: `ces-ddr-platform/ces-backend/src/repository/crud/user.py`
- Current jwt_authentication: `ces-ddr-platform/ces-backend/src/securities/authorizations/jwt_authentication.py`
- Current jwt generator: `ces-ddr-platform/ces-backend/src/securities/authorizations/jwt.py`
- Current login route: `ces-ddr-platform/ces-backend/src/api/routes/v1/auth.py`
- Settings base: `ces-ddr-platform/ces-backend/src/config/settings/base.py`
- Events (startup): `ces-ddr-platform/ces-backend/src/config/events.py`
- Exceptions: `ces-ddr-platform/ces-backend/src/utilities/exceptions/exceptions.py`
- Migration versions: `ces-ddr-platform/ces-backend/src/repository/migrations/versions/`
- Test pattern: `ces-ddr-platform/ces-backend/tests/test_pipeline_cost_route.py`

## Story Context Completion

Ultimate context engine analysis completed — AI Avatar B2C RBAC pattern adopted; existing auth infrastructure extended minimally; seeding idempotent; no existing routes changed.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- DB port mismatch (5432 vs 5433) — resolved by starting CES docker compose postgres service.
- `dummy_hash()` missing from `PasswordGenerator` — added to fix existing auth.py reference.
- `EntityAlreadyExistsException` not caught by `EntityAlreadyExists` handler — raised `EntityAlreadyExists` alias instead.
- Ruff import sort — auto-fixed via `ruff --fix`.

### Completion Notes List

- Migration 013: `is_active` on users, `roles` table, `user_roles` join table with FK + composite PK.
- `Role` + `UserRole` models; `User.roles` relationship with `lazy="noload"` + `selectinload` on demand.
- `RoleCRUDRepository`: `find_by_name`, `create_role`. Extended `UserCRUDRepository`: `read_all_with_roles`, `create_user`, `assign_role`, `deactivate`, `read_user_with_roles`.
- `SeedService.seed_roles_and_admin`: idempotent ADMIN/USER roles + admin user from settings; wired into app startup.
- `get_current_user` now eager-loads roles + rejects inactive users (returns None).
- `JWTUser` + `generate_access_token` include `roles` list in JWT payload.
- Login route: inactive user nulled before password check (same 401 path as unknown user).
- `ForbiddenException` + handler + registered in main.py.
- `RoleChecker`, `admin_only`, `user_only`, `admin_or_user` in `rbac.py`.
- `UserResponse`, `CreateUserRequest` schemas (no `password_hash` exposure).
- `GET /api/users/`, `POST /api/users/`, `PATCH /api/users/{id}/deactivate` — all ADMIN-gated.
- 12 route tests; 303 total passing; ruff clean.

### File List

- `ces-ddr-platform/ces-backend/src/repository/migrations/versions/2026_05_26_0013-013_rbac_schema.py` (new)
- `ces-ddr-platform/ces-backend/src/models/db/role.py` (new)
- `ces-ddr-platform/ces-backend/src/models/db/user.py` (modified)
- `ces-ddr-platform/ces-backend/src/models/db/__init__.py` (modified)
- `ces-ddr-platform/ces-backend/src/repository/crud/role.py` (new)
- `ces-ddr-platform/ces-backend/src/repository/crud/user.py` (modified)
- `ces-ddr-platform/ces-backend/src/services/seed.py` (new)
- `ces-ddr-platform/ces-backend/src/config/settings/base.py` (modified)
- `ces-ddr-platform/ces-backend/src/config/events.py` (modified)
- `ces-ddr-platform/ces-backend/src/securities/authorizations/jwt_authentication.py` (modified)
- `ces-ddr-platform/ces-backend/src/securities/authorizations/jwt.py` (modified)
- `ces-ddr-platform/ces-backend/src/securities/authorizations/rbac.py` (new)
- `ces-ddr-platform/ces-backend/src/securities/hashing/password.py` (modified)
- `ces-ddr-platform/ces-backend/src/models/schemas/jwt.py` (modified)
- `ces-ddr-platform/ces-backend/src/models/schemas/user.py` (new)
- `ces-ddr-platform/ces-backend/src/utilities/exceptions/exceptions.py` (modified)
- `ces-ddr-platform/ces-backend/src/utilities/exceptions/__init__.py` (modified)
- `ces-ddr-platform/ces-backend/src/api/routes/v1/auth.py` (modified)
- `ces-ddr-platform/ces-backend/src/api/routes/v1/users.py` (new)
- `ces-ddr-platform/ces-backend/src/api/endpoints.py` (modified)
- `ces-ddr-platform/ces-backend/src/main.py` (modified)
- `ces-ddr-platform/ces-backend/tests/test_user_management_route.py` (new)
- `ces-ddr-platform/ces-backend/.env` (modified — added ADMIN_USERNAME/ADMIN_PASSWORD)

### Review Findings

- [ ] [Review][Decision] D1: Admin self-deactivation — no guard prevents admin from deactivating themselves, permanently locking out API access with no recovery path. Decision: add guard or allow?
- [ ] [Review][Decision] D2: Password validation absent — `CreateUserRequest.password: str` has no minimum length or complexity constraints; empty string `""` is accepted and hashed. Decision: what are minimum password requirements?
- [ ] [Review][Decision] D3: Duplicate username error code mismatch — AC9 specifies `"code": "USERNAME_CONFLICT"` but `EntityAlreadyExists` handler emits `"ENTITY_ALREADY_EXIST"`. Decision: create a custom exception or relax the AC9 error code requirement?
- [ ] [Review][Patch] P1: `dummy_hash` is an invalid bcrypt string — timing attack still leaks user existence [src/securities/hashing/password.py]
- [ ] [Review][Patch] P2: `deactivate()` response has empty `roles` — `session.refresh()` does not reload `noload` relationship; `_user_response(updated)` always returns `roles: []` [src/repository/crud/user.py + src/api/routes/v1/users.py]
- [ ] [Review][Patch] P3: `create_user` + `assign_role` non-atomic — two separate commits; crash between them leaves user with no role and no rollback [src/repository/crud/user.py + src/api/routes/v1/users.py]
- [ ] [Review][Patch] P4: Concurrent `POST /api/users/` with same username hits unhandled `IntegrityError` — check-then-insert is not atomic [src/api/routes/v1/users.py]
- [ ] [Review][Patch] P5: `SeedService` race condition on multi-worker startup — concurrent workers all pass `find_by_name` → `None` and all attempt `create_role`, second crashes with unhandled unique violation [src/services/seed.py]
- [ ] [Review][Patch] P6: `deactivate()` sets `updated_at = int(time.time())` (Python wall clock) while all other timestamps use DB server time `EXTRACT(EPOCH FROM now())::BIGINT` — clock skew risk [src/repository/crud/user.py]
- [ ] [Review][Patch] P7: `assign_role` silently skipped if USER role missing — `create_user` route produces user with `roles: []`, no error raised [src/api/routes/v1/users.py]
- [ ] [Review][Patch] P8: Login JWT always embeds `roles: []` — `find_by_username` has no `selectinload(User.roles)`; `User.roles` is `noload` so `generate_access_token` always sees empty list [src/api/routes/v1/auth.py + src/securities/authorizations/jwt.py] — violates AC5
- [ ] [Review][Patch] P9: OpenAPI path param named `{user_id}` but spec AC14 states `{id}` [src/api/routes/v1/users.py]
- [x] [Review][Defer] W1: JWT role staleness post-issuance — role changes not reflected until token expiry; pre-existing JWT architecture trade-off, not introduced by this story
- [x] [Review][Defer] W2: Test body assertions too weak — `test_post_users_creates_user` checks only status code; `StubUserRepo` hardcodes `"new-id"` masking duplicate-create bugs
- [x] [Review][Defer] W3: `UserResponse.id` string format not canonical UUID — no hyphen/case enforcement; pre-existing pattern across codebase
