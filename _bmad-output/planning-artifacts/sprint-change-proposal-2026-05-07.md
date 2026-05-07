# Sprint Change Proposal: Python-Only Backend

**Project:** Canadian Energy Service Internal Tool  
**Date:** 2026-05-07  
**Requested by:** Het  
**Status:** Approved and implemented in planning/code cleanup pass  
**Change trigger:** Use one Python backend named `ces-backend`. Remove the old alternate backend and root backend coordination structure.

## 1. Issue Summary

Backend selection is complete. V1 uses one Python FastAPI backend. Maintaining alternate-backend planning language, duplicated backend folders, cross-backend tests, and root backend coordination assets would waste implementation time and confuse future developer agents.

Core decision:

- Keep `ces-ddr-platform/ces-backend`.
- Remove old alternate backend code.
- Remove root backend coordination assets.
- Put backend resources under `ces-backend/app/resources`.
- Put backend test fixtures under `ces-backend/tests/fixtures`.
- Make Alembic the only migration authority.
- Make pytest the backend verification gate.

## 2. Impact Analysis

Epic 1 needed cleanup because completed foundation stories referenced removed backend structure. No user-facing rollback was needed.

Epics 2-7 remain valid, but backend acceptance criteria now target only `ces-backend`.

UX does not change. Frontend still talks to one backend URL.

Technical impact:

- Backend framework: FastAPI.
- Settings: `decouple + BackendBaseSettings`.
- Migrations: Alembic.
- Excel: `openpyxl`.
- Search: Python BM25 implementation plus Qdrant client.
- Gemini: `google-genai` Python SDK.
- PDF processing: `pdfplumber`, `pypdf`.
- Schema validation: Pydantic v2.
- OpenAPI: FastAPI `/docs`.
- Deployment: one Python backend behind Nginx.

## 3. Recommended Approach

Recommended path: Direct Adjustment.

Rationale:

- MVP scope stays intact.
- Python fits the AI extraction, Pydantic validation, PDF parsing, async API, and project backend rules.
- One backend reduces timeline, CI complexity, deployment complexity, and future maintenance risk.

Scope classification: Moderate.

## 4. Implemented Changes

- Renamed the old Python backend folder to `ces-ddr-platform/ces-backend`.
- Removed old alternate backend folder.
- Removed root backend coordination folder after moving useful fixtures/resources.
- Moved keyword resource to `ces-backend/app/resources/keywords.json`.
- Moved auth fixtures to `ces-backend/tests/fixtures/auth`.
- Updated backend package name to `ces-backend`.
- Updated backend service logger name to `ces-backend`.
- Updated backend env examples to use `BACKEND_*`.
- Updated README commands to use `ces-backend` and Alembic only.
- Updated active backend tests to use local backend fixtures instead of deleted root paths.
- Updated PRD, architecture, epics, and completed story artifacts toward Python-only guidance.

## 5. Handoff

Developer agent owns continued implementation in `ces-backend`.

Future success criteria:

- No old alternate backend directory remains.
- No root backend coordination directory remains.
- Backend stories target Python only.
- Alembic is sole migration authority.
- `openpyxl` is sole Excel export implementation.
- Backend fixtures/resources live under `ces-backend`.
- Docker Compose runs frontend, Python backend, PostgreSQL, and Qdrant only when backend service is added.
- Backend verification runs through pytest.

## 6. Checklist Status

- [x] Triggering issue identified.
- [x] Core problem defined.
- [x] PRD impact reviewed.
- [x] Architecture impact reviewed.
- [x] Epic/story impact reviewed.
- [x] Direct Adjustment selected.
- [x] User approval captured.
- [x] Cleanup implementation started.
- [x] Handoff path defined.

Correct Course workflow complete, Het.
