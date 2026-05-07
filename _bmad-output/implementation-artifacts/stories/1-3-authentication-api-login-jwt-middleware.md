# Story 1.3: Authentication API - Login & JWT Middleware

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a CES staff member,
I want to log in with my username and password and receive a JWT,
so that I can access all platform features without re-authenticating for 8 hours.

## Acceptance Criteria

1. Given a user exists in the `users` table with bcrypt-hashed password, when `POST /auth/login` is called with valid `{ "username": "...", "password": "..." }`, then HTTP 200 is returned with `{ "token": "<JWT>", "expires_at": "<ISO8601 8hr from now>" }`, JWT is HS256-signed using `JWT_SECRET` from environment, and JWT payload contains `user_id` and `exp` claims.
2. Given `POST /auth/login` is called with wrong credentials, when username does not exist or password does not match bcrypt hash, then HTTP 401 is returned with `{ "error": "Invalid credentials", "code": "UNAUTHORIZED", "details": {} }`, and response time is identical for both failure cases.
3. Given any endpoint except `POST /auth/login` is called without `Authorization: Bearer <token>`, when JWT middleware processes the request, then HTTP 401 is returned with `{ "error": "Authentication required", "code": "UNAUTHORIZED", "details": {} }`.
4. Given a JWT with expired `exp` claim is sent, when JWT middleware validates it, then HTTP 401 is returned with `UNAUTHORIZED` error code.
5. Given structured logging middleware is active, when any request is processed, then each log line is JSON containing `{ "timestamp", "level", "service", "request_id", "message" }`, `request_id` is a UUID generated per request and present on all log lines for that request, and `Authorization` header value, `JWT_SECRET`, and `POSTGRES_PASSWORD` values never appear in logs.
6. Given both Python backend implement the login endpoint, when same credentials are sent to each, then both return tokens validated by the same JWT middleware logic, with Go behavior canonical and Python matching exactly.

## Tasks / Subtasks

- [x] Confirm Story 1.2 database prerequisite is complete before implementation (AC: 1-2)
  - [x] Verify `users` table exists with `id`, `username`, `password_hash`, `created_at`, and `updated_at`.
  - [x] Verify migrations and shared schema have landed before adding runtime DB queries.
- [x] Add shared auth API contract fixtures (AC: 1-6)
  - [x] Add request/response/error fixtures under `ces-ddr-platform/ces-backend/tests/fixtures/auth/`.
  - [x] Keep JSON field names exactly `token`, `expires_at`, `error`, `code`, and `details`.
  - [x] Add tests proving Python uses the fixture expectations.
- [x] Implement Go auth dependencies and structure (AC: 1-6)
  - [x] Extend `ces-backend/internal/config/config.go` with `JWTSecret` using existing centralized config pattern.
  - [x] Add `ces-backend/internal/db/pool.go` for pgx pool setup using context-first APIs.
  - [x] Add `ces-backend/internal/db/queries/users.go` for username lookup only.
  - [x] Add `ces-backend/internal/models/user.go` for user data shape.
  - [x] Add `ces-backend/internal/auth/jwt.go`, `middleware.go`, and `password.go`.
  - [x] Add `ces-backend/internal/api/auth.go` and register `POST /auth/login`.
  - [x] Wrap all non-login routes with JWT middleware while preserving `GET /health`.
- [x] Implement Python auth dependencies and structure (AC: 1-6)
  - [x] Extend `ces-backend/app/config.py` with `jwt_secret` through `decouple + BackendBaseSettings`.
  - [x] Add `ces-backend/app/db/pool.py` using asyncpg.
  - [x] Add `ces-backend/app/db/queries/users.py` for async username lookup only.
  - [x] Add `ces-backend/app/models/user.py`.
  - [x] Add `ces-backend/app/auth/jwt.py`, `middleware.py`, and `password.py`.
  - [x] Add `ces-backend/app/api/auth.py` and register `POST /auth/login`.
  - [x] Add dependency or middleware protection for every route except `/auth/login` while preserving `GET /health` behavior unless test coverage decision explicitly protects health later.
- [x] Add structured request logging in the Python backend (AC: 5)
  - [x] Generate one UUID `request_id` per request at request entry.
  - [x] Emit JSON log lines with required keys and backend-specific `service`.
  - [x] Propagate request ID through Go context and Python `request.state`.
  - [x] Sanitize `Authorization`, `JWT_SECRET`, `POSTGRES_PASSWORD`, and raw secret values before any log write.
- [x] Add authentication tests and test coverage coverage (AC: 1-6)
  - [x] Test valid login returns token and ISO8601 `expires_at` roughly 8 hours ahead.
  - [x] Test JWT payload contains `user_id` and `exp`, signed with HS256.
  - [x] Test nonexistent username and wrong password return identical 401 body and use constant-time-safe failure path.
  - [x] Test missing, malformed, bad signature, and expired bearer tokens return standard `UNAUTHORIZED` errors.
  - [x] Test logs include `request_id` and never include secret/header values.
  - [x] Test existing health endpoint still returns exactly `{ "status": "ok" }`.
- [x] Preserve scope boundaries (AC: all)
  - [x] Do not add frontend login UI, localStorage token helpers, protected routing, refresh tokens, roles, RBAC, password reset, user management UI, DDR endpoints, upload endpoints, or business tables.

### Review Findings

- [x] [Review][Patch] Reject missing or placeholder JWT secrets instead of signing with a known default [ces-ddr-platform/ces-backend/internal/config/config.go:33]
- [x] [Review][Patch] Reject Go JWTs that omit the required `exp` claim [ces-ddr-platform/ces-backend/internal/auth/jwt.go:49]
- [x] [Review][Patch] Reject Python JWTs that omit `exp` or use a non-string `user_id` claim [ces-ddr-platform/ces-backend/app/auth/jwt.py:31]
- [x] [Review][Patch] Implement actual log secret sanitization before writing request logs [ces-ddr-platform/ces-backend/internal/auth/logging.go:24]
- [x] [Review][Patch] Remove production `/protected-test` routes from the Python backend [ces-ddr-platform/ces-backend/internal/api/router.go:54]
- [x] [Review][Patch] Return an infrastructure error for Go user-store failures instead of masking them as invalid credentials [ces-ddr-platform/ces-backend/internal/api/auth.go:39]
- [x] [Review][Patch] Add real cross-backend JWT test coverage coverage using a shared fixture user/hash [ces-ddr-platform/ces-backend/internal/api/auth_test.go:59]
- [x] [Review][Patch] Handle malformed Python bcrypt hashes without leaking an unhandled 500 [ces-ddr-platform/ces-backend/app/auth/password.py:16]
- [x] [Review][Patch] Guard lazy Python asyncpg pool initialization against concurrent first-request races [ces-ddr-platform/ces-backend/app/db/pool.py:10]

## Dev Notes

### Current Sprint State

Story 1.2 is currently marked `in-progress` in `sprint-status.yaml`. This story depends on Story 1.2 outputs because login reads the `users` table and verifies `password_hash`. Dev agent must not implement alternate schema, seed a different credential store, or create a second auth table to bypass the prerequisite. [Source: _bmad-output/implementation-artifacts/sprint-status.yaml]

### Auth Contract

Required endpoint:

```text
POST /auth/login
```

Request body:

```json
{ "username": "string", "password": "string" }
```

Success response:

```json
{ "token": "<JWT>", "expires_at": "<ISO8601 8hr from now>" }
```

Failure response for bad username, bad password, missing token, invalid token, and expired token must follow standard error shape:

```json
{ "error": "Authentication required", "code": "UNAUTHORIZED", "details": {} }
```

Bad login credentials specifically use:

```json
{ "error": "Invalid credentials", "code": "UNAUTHORIZED", "details": {} }
```

Do not return `detail`, `message`, wrapped data, or language-specific error shape. Success bodies are direct objects, no wrapper. [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]

### JWT Requirements

Use HS256 only. Token lifetime is exactly 8 hours from login; no refresh tokens, no silent extension, no roles in V1. Payload must include `user_id` and `exp`. `expires_at` should represent same expiry instant as `exp` in ISO8601 UTC form. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]

`JWT_SECRET` must come from existing config systems only:

- Go: add field to `internal/config.Config`; direct `os.Getenv` remains confined to `internal/config/config.go`.
- Python: add `jwt_secret` to `AppSettings` using `decouple.config` and `BackendBaseSettings`; never use `os.environ.get` or `os.getenv`.

Reject missing or empty `JWT_SECRET` at startup or app creation. Do not fall back to an insecure default in production-like environments. [Source: AGENTS.md#Backend Guidelines]

### Password Verification

Stored password is bcrypt hash in `users.password_hash`; never compare plaintext, never return whether username or password failed. Both nonexistent user and wrong password paths must run a comparable bcrypt verification path so callers cannot distinguish account existence by timing. Use a static dummy bcrypt hash for nonexistent users, held inside auth service/module code, not generated per request. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]

Python password verification is synchronous CPU work. Keep async route correctness by wrapping bcrypt verification in `asyncio.to_thread()` from the auth service or password verifier so FastAPI route handlers do not block event loop. [Source: AGENTS.md#Backend Guidelines]

### Route Protection Boundary

Architecture says all routes except `/auth/login` require bearer JWT. Current scaffold has only `GET /health`; Story 1.1 tests require it returns `{ "status": "ok" }`. Preserve health response and test compatibility while adding middleware structure that can protect future business routes by default. If dev chooses to protect `/health`, update test coverage tests and document the intentional decision; otherwise keep `/health` public as operational healthcheck and make that exception explicit in middleware. [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]

### Logging Requirements

Add structured request logging middleware in the Python backend. Required JSON keys:

```json
{ "timestamp": "ISO8601", "level": "info|warn|error", "service": "ces-backend|ces-backend", "request_id": "uuid", "message": "string" }
```

Generate request ID at request entry. Thread it via Go request context and Python `request.state`. Sanitization is mandatory before write: never log `Authorization` header value, `JWT_SECRET`, `POSTGRES_PASSWORD`, or raw values read from config. [Source: _bmad-output/planning-artifacts/architecture.md#Logging Pattern]

### Go Implementation Guardrails

Current Python backend has:

- `internal/api/router.go`: `NewRouter()` sets FastAPI release mode, creates `gin.New()`, registers health only.
- `internal/api/health.go`: `HealthHandler` returns `{"status":"ok"}`.
- `internal/config/config.go`: `Config` loads env through centralized `value`.
- `main.go`: loads config, creates router, runs server.
- `internal/api/health_test.go`: exact health response regression.

Preserve the class/struct style already used: handlers as structs with `Register` methods. Do not place DB queries inside handlers. Expected structure from architecture:

```text
ces-backend/internal/
├── api/auth.go
├── auth/jwt.go
├── auth/middleware.go
├── auth/password.go
├── db/pool.go
├── db/queries/users.go
└── models/user.go
```

Use `context.Context` first for DB/query/auth validation functions that touch DB or request-scoped work. Use `github.com/golang-jwt/jwt/v5`, `golang.org/x/crypto/bcrypt`, and `github.com/jackc/pgx/v5/pgxpool`. [Source: _bmad-output/planning-artifacts/architecture.md#Backend Package/Module Organization]

### Python Implementation Guardrails

Current Python backend has:

- `app/main.py`: `AppFactory` creates FastAPI, includes `HealthRouter`, registers `ExceptionHandlers`.
- `app/api/health.py`: `HealthRouter` class with async `read`.
- `app/config.py`: `BackendBaseSettings` and `AppSettings` using `decouple.config`.
- `app/exceptions.py`: global fallback currently returns `{"detail": "Internal server error"}`.
- `tests/api/test_health.py`: exact health response regression.

Continue class/service encapsulation. Do not add loose utility functions or global state beyond constants. Expected structure from architecture:

```text
ces-backend/app/
├── api/auth.py
├── auth/jwt.py
├── auth/middleware.py
├── auth/password.py
├── db/pool.py
├── db/queries/users.py
└── models/user.py
```

All route handlers remain `async def`; all DB calls use `await`. Use asyncpg for runtime DB access, `python-jose[cryptography]` for JWT, and `passlib[bcrypt]` for password verification unless dev elects direct `bcrypt` to avoid passlib compatibility risk. If using passlib 1.7.4, pin `bcrypt<5.0` because bcrypt 5 changed long-password behavior and has known compatibility friction with passlib assumptions. [Source: _bmad-output/planning-artifacts/architecture.md#Async Pattern]

### Dependency Guidance

Go:

```text
github.com/golang-jwt/jwt/v5
github.com/jackc/pgx/v5
golang.org/x/crypto/bcrypt
github.com/google/uuid or github.com/gin-contrib/requestid
```

Current Go module is `go 1.22.2`. Latest `golang-jwt/jwt/v5` docs show v5.3.1 published January 28, 2026. Use v5 import path. For pgx, latest docs show v5.9.x, but verify Go version compatibility before upgrading; do not bump project Go version inside this story unless required and discussed. [Source: https://pkg.go.dev/github.com/golang-jwt/jwt/v5] [Source: https://pkg.go.dev/github.com/jackc/pgx/v5]

Python:

```toml
"asyncpg>=0.30.0,<1.0.0",
"python-jose[cryptography]>=3.5.0,<4.0.0",
"passlib[bcrypt]>=1.7.4,<2.0.0",
"bcrypt>=4.0.0,<5.0.0"
```

Passlib stable bcrypt docs identify bcrypt `"2b"` as current default. Python-jose PyPI currently exposes install extra `python-jose[cryptography]`. Keep dependency additions narrow; do not add ORM unless needed by implementation. [Source: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html] [Source: https://pypi.org/project/python-jose/]

### Existing Code To Preserve

Do not regress:

- `GET /health` JSON response and status in the Python backend.
- `AppFactory` creation pattern.
- `HealthRouter` class pattern.
- `ExceptionHandlers().register(app)` flow.
- Go `HealthHandler{}.Register(router)` style.
- Centralized Go config reads.
- Python `decouple + BackendBaseSettings` config reads.
- Existing `.env.example` placeholder-only policy.

No secret values may be committed or printed. A real `.env` exists locally under `ces-ddr-platform/.env`; do not read or include its values in story, tests, logs, or docs. [Source: AGENTS.md#Backend Guidelines]

### Testing Requirements

Run Python tests from `ces-ddr-platform/ces-backend/`:

```bash
source .venv/bin/activate
pytest
```

Run Go tests from `ces-ddr-platform/ces-backend/`:

```bash
GOTOOLCHAIN=local go test ./...
```

Add tests that verify:

- Valid login status/body/token claims.
- Wrong username and wrong password return same body and status.
- Missing bearer token returns standard authentication-required error.
- Expired token returns standard `UNAUTHORIZED` error.
- Bad signature and malformed token return standard `UNAUTHORIZED` error.
- Logs contain `request_id` and required keys.
- Logs do not contain bearer token, raw `Authorization` header value, `JWT_SECRET`, configured JWT secret value, `POSTGRES_PASSWORD`, or configured password value.
- Python accepts the bcrypt-hashed fixture user and generates a valid HS256 token with the configured secret.

If PostgreSQL, migrations, or Story 1.2 files are not available locally, document exact blocker in Dev Agent Record and keep unit-level JWT/password/error tests in place.

### Previous Story Intelligence

Story 1.1 established scaffold and health endpoints. Story 1.2 is currently in progress and created/modified migration-related tests in working tree, but its story file is not marked done. Treat database/migration outputs as prerequisites, not guaranteed complete.

Patterns to reuse:

- Python code is class-oriented and small: `AppFactory`, `HealthRouter`, `ExceptionHandlers`, `AppSettings`.
- Go code is package-oriented with config centralized in `internal/config`.
- Existing tests assert exact response bodies; auth tests should do same.
- Previous guidance emphasized no real secrets in committed files and no direct env reads outside config.

Recent Git history only shows README path movement and initial scaffolding; no auth implementation pattern exists yet. [Source: git log --oneline -5]

### Project Structure Notes

This story adds first runtime DB access layer and first auth layer. Keep files inside `ces-ddr-platform/ces-backend` and `ces-ddr-platform/ces-backend`. Do not add backend code at repository root. Do not modify frontend files; Story 1.4 owns login UI, localStorage token helpers, and protected routing.

### References

- [Source: AGENTS.md#Backend Guidelines]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Format]
- [Source: _bmad-output/planning-artifacts/architecture.md#Logging Pattern]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/implementation-artifacts/stories/1-2-database-schema-users-table-migration-tooling.md]
- [Source: https://pkg.go.dev/github.com/golang-jwt/jwt/v5]
- [Source: https://pkg.go.dev/github.com/jackc/pgx/v5]
- [Source: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html]
- [Source: https://pypi.org/project/python-jose/]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-05-06: Red tests failed before implementation because Go auth package and Python `app.auth` package were absent.
- 2026-05-06: Latest `pgx/v5` required Go 1.25 and attempted to bump `go.mod`; pinned `pgx/v5` to Go-1.22-compatible `v5.5.5` and preserved `go 1.22.2`.
- 2026-05-06: Python regression suite passed after auth implementation.

### Completion Notes List

- Confirmed Story 1.2 schema prerequisite is done and reused canonical `users` table shape for runtime lookup.
- Added shared auth request, success, and error fixtures under `ces-backend/tests/fixtures/auth`.
- Implemented Go login handler, JWT generation/validation, bcrypt password verification with dummy hash path, pgx pool/user query layer, auth middleware, and structured JSON request logging.
- Implemented Python login router, JWT generation/validation, bcrypt verification wrapped in `asyncio.to_thread()`, asyncpg pool/user repository, auth middleware, and structured JSON request logging.
- Kept `/health` public and unchanged in the Python backend while protecting non-public routes by default.
- Added auth tests covering valid login, invalid credentials, missing/malformed/bad/expired bearer tokens, shared fixture shape, health regression, and log secret redaction.

### File List

- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/implementation-artifacts/stories/1-3-authentication-api-login-jwt-middleware.md
- ces-ddr-platform/ces-backend/go.mod
- ces-ddr-platform/ces-backend/go.sum
- ces-ddr-platform/ces-backend/main.go
- ces-ddr-platform/ces-backend/internal/api/auth.go
- ces-ddr-platform/ces-backend/internal/api/auth_test.go
- ces-ddr-platform/ces-backend/internal/api/router.go
- ces-ddr-platform/ces-backend/internal/auth/errors.go
- ces-ddr-platform/ces-backend/internal/auth/jwt.go
- ces-ddr-platform/ces-backend/internal/auth/logging.go
- ces-ddr-platform/ces-backend/internal/auth/middleware.go
- ces-ddr-platform/ces-backend/internal/auth/password.go
- ces-ddr-platform/ces-backend/internal/auth/store.go
- ces-ddr-platform/ces-backend/internal/config/config.go
- ces-ddr-platform/ces-backend/internal/db/pool.go
- ces-ddr-platform/ces-backend/internal/db/queries/users.go
- ces-ddr-platform/ces-backend/internal/models/user.go
- ces-ddr-platform/ces-backend/app/api/auth.py
- ces-ddr-platform/ces-backend/app/auth/__init__.py
- ces-ddr-platform/ces-backend/app/auth/errors.py
- ces-ddr-platform/ces-backend/app/auth/jwt.py
- ces-ddr-platform/ces-backend/app/auth/middleware.py
- ces-ddr-platform/ces-backend/app/auth/password.py
- ces-ddr-platform/ces-backend/app/config.py
- ces-ddr-platform/ces-backend/app/db/__init__.py
- ces-ddr-platform/ces-backend/app/db/pool.py
- ces-ddr-platform/ces-backend/app/db/queries/__init__.py
- ces-ddr-platform/ces-backend/app/db/queries/users.py
- ces-ddr-platform/ces-backend/app/main.py
- ces-ddr-platform/ces-backend/app/models/__init__.py
- ces-ddr-platform/ces-backend/app/models/user.py
- ces-ddr-platform/ces-backend/pyproject.toml
- ces-ddr-platform/ces-backend/tests/api/test_auth.py
- ces-ddr-platform/ces-backend/tests/conftest.py
- ces-ddr-platform/ces-backend/tests/fixtures/auth/README.md
- ces-ddr-platform/ces-backend/tests/fixtures/auth/authentication-required-response.json
- ces-ddr-platform/ces-backend/tests/fixtures/auth/login-invalid-credentials-response.json
- ces-ddr-platform/ces-backend/tests/fixtures/auth/login-success-response.json
- ces-ddr-platform/ces-backend/tests/fixtures/auth/login-valid-request.json
- ces-ddr-platform/ces-backend/tests/fixtures/auth/shared-user.json

### Change Log

- 2026-05-06: Implemented Story 1.3 authentication API, JWT middleware, structured logging, runtime user lookup layers, fixtures, dependencies, and Python test coverage.
- 2026-05-06: Fixed code review findings for JWT secret validation, required JWT expiry, logging sanitization, production test routes, malformed bcrypt hashes, and Python pool initialization.
