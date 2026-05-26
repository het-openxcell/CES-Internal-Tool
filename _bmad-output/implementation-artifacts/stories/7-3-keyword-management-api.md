# Story 7.3: Keyword Management API

Status: ready-for-dev

## Story

As a CES staff member,
I want to view and update keyword-to-type mappings via API without restarting the server,
so that I can fix systematic misclassification immediately after spotting a pattern in the correction store.

## Acceptance Criteria

1. Given `GET /api/keywords` is called with a valid JWT, then HTTP 200 returns the full keyword map as `{ "<keyword>": "<type>", ... }`.
2. Given `PUT /api/keywords` is called with a valid JWT and a valid `{ "<keyword>": "<type>", ... }` body, then HTTP 200 returns the full updated keyword map and `keywords.json` is overwritten with the new content.
3. Given `PUT /api/keywords` succeeds, then in-memory `KeywordLoader.keywords` is updated immediately and subsequent `classify` calls use the new map — no server restart required.
4. Given `PUT /api/keywords` is called with a body that fails type validation, then HTTP 400 returns `{ "error": "<message>", "code": "KEYWORD_UPDATE_FAILED", "details": {} }` and `keywords.json` is not modified.
5. Given `GET /api/keywords` or `PUT /api/keywords` is called without authentication, then HTTP 401 is returned.
6. Given OpenAPI is generated, then `/api/keywords` appears in `/openapi.json`.
7. Given existing `classify` behavior, then `occurrence/classify` calls continue to use the in-memory map from `KeywordLoader.get_keywords()` — no change to classify code.

## Tasks / Subtasks

- [ ] Add file persistence to `KeywordLoader.reload()` (AC: 2)
  - [ ] In `src/services/keywords/loader.py`, update `KeywordLoader.reload(new_data)` to write `new_data` back to `keywords.json` using `asyncio.to_thread()` — wrap the blocking file I/O in a thread.
  - [ ] Use `importlib.resources.files("src.resources").joinpath("keywords.json")` to resolve the path, then convert to `pathlib.Path` for writing: `path = pathlib.Path(importlib.resources.files("src.resources").joinpath("keywords.json"))`.
  - [ ] Write using `path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False))`.
  - [ ] `reload` becomes `async def reload(cls, new_data)`. Call site in route must `await KeywordLoader.reload(keywords)`.
  - [ ] In-memory update (`cls.keywords = new_data`) must happen whether or not file write succeeds, so update memory THEN write file. If file write fails, raise so the route can catch and return an error — do not silently swallow IO errors.
- [ ] Fix PUT response to return full keyword map (AC: 2)
  - [ ] In `src/api/routes/v1/keywords.py`, change the PUT endpoint return type from `dict[str, int]` to `dict[str, str]`.
  - [ ] Return `KeywordLoader.get_keywords()` after calling `await KeywordLoader.reload(keywords)`.
- [ ] Fix PUT error shape to use project standard (AC: 4)
  - [ ] Replace `HTTPException` raises with `JSONResponse(status_code=400, content={"error": "<message>", "code": "KEYWORD_UPDATE_FAILED", "details": {}})`.
  - [ ] The two current `HTTPException` cases (too many keywords, invalid types) become `JSONResponse` 400 returns.
  - [ ] Any IO error from `KeywordLoader.reload()` is caught and returns the same `KEYWORD_UPDATE_FAILED` shape.
- [ ] Update frontend `api.ts` type for `updateKeywords` (AC: 2)
  - [ ] In `ces-frontend/src/lib/api.ts`, change `updateKeywords` return type from `{ updated: number }` to `Record<string, string>`.
  - [ ] The method already exists — only change the generic type parameter, not the method body.
- [ ] Add/extend backend tests (AC: 1–7)
  - [ ] Check `tests/test_keywords_route.py` (already exists). Extend it:
    - [ ] Test PUT returns full keyword map (not `{ "updated": N }`).
    - [ ] Test PUT with invalid type value returns 400 with `KEYWORD_UPDATE_FAILED` code.
    - [ ] Test PUT with too many keywords returns 400 with `KEYWORD_UPDATE_FAILED` code.
    - [ ] Test `KeywordLoader.get_keywords()` returns updated map after PUT succeeds.
    - [ ] Stub file I/O in tests — do not write to actual keywords.json in tests. Patch/mock `KeywordLoader.reload` at the route test boundary or stub at the classmethod level.
- [ ] Run quality gates
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && pytest`
  - [ ] `cd ces-ddr-platform/ces-backend && source .venv/bin/activate && ruff check src tests`

## Dev Notes

### Critical Context

- Backend-only story plus one frontend type fix.
- `GET /keywords` — **COMPLETE, no changes needed**. Only `PUT` needs changes.
- Existing `KeywordLoader` in `src/services/keywords/loader.py` already handles in-memory. Only file persistence and async signature are new.
- `VALID_OCCURRENCE_TYPES` validation in the route is already correct — keep it.
- The file write MUST be wrapped in `asyncio.to_thread()` — CES rule: never block the async event loop.

### DO NOT REIMPLEMENT — Reuse These

| Existing thing | Where | How to use in 7-3 |
|---|---|---|
| `GET /keywords` route | `src/api/routes/v1/keywords.py` | **Touch nothing.** Already returns full map. |
| `KeywordLoader.get_keywords()` | `src/services/keywords/loader.py` | Call after reload to build PUT response |
| `KeywordLoader.load()` | `src/services/keywords/loader.py` | Load path already uses `importlib.resources.files` — reuse same path expression for write |
| `VALID_OCCURRENCE_TYPES` validation | `src/api/routes/v1/keywords.py` | Keep as-is; only change error shape when raising |
| `jwt_authentication` | existing | No change needed — already on both routes |
| `test_keywords_route.py` | `tests/` | Extend existing test file; do not create new one |

### Keyword File Path

```python
import importlib.resources
import json
import pathlib

path = pathlib.Path(str(importlib.resources.files("src.resources").joinpath("keywords.json")))
path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False))
```

Wrap the `path.write_text(...)` call with `await asyncio.to_thread(path.write_text, json.dumps(new_data, indent=2, ensure_ascii=False))`.

### Changed Error Shape

Current (uses HTTPException):
```python
raise HTTPException(status_code=400, detail="Too many keywords...")
```

New (project standard):
```python
return JSONResponse(status_code=400, content={"error": "Too many keywords...", "code": "KEYWORD_UPDATE_FAILED", "details": {}})
```

### PUT Response Before vs After

Before: `return {"updated": len(keywords)}`
After: `return KeywordLoader.get_keywords()`
And: route return type annotation → `dict[str, str]`

### Frontend Type Fix (api.ts)

Current:
```ts
async updateKeywords(keywords: Record<string, string>) {
  return this.request<{ updated: number }>("/keywords", { ... });
}
```
After:
```ts
async updateKeywords(keywords: Record<string, string>) {
  return this.request<Record<string, string>>("/keywords", { ... });
}
```
This may require updating the call site in `KeywordsPage.tsx` if it destructures `{ updated }` — check and fix if so.

### Architecture Compliance

- No `os.getenv`. No loose functions. All file I/O in `asyncio.to_thread()`.
- Error shape: `{ "error": "...", "code": "KEYWORD_UPDATE_FAILED", "details": {} }`.
- Route stays thin — all logic in `KeywordLoader`.

### Regression Guardrails

- Do not change `GET /keywords` route or `KeywordLoader.load()` or `KeywordLoader.get_keywords()`.
- Do not change `VALID_OCCURRENCE_TYPES` constant.
- Do not change occurrence classify logic — it already calls `KeywordLoader.get_keywords()` and will pick up in-memory updates automatically.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md#Story-7.3`
- Keywords route: `ces-ddr-platform/ces-backend/src/api/routes/v1/keywords.py`
- KeywordLoader: `ces-ddr-platform/ces-backend/src/services/keywords/loader.py`
- Occurrence types constant: `ces-ddr-platform/ces-backend/src/constants/occurrence.py`
- Frontend api client: `ces-ddr-platform/ces-frontend/src/lib/api.ts`
- Existing tests: `ces-ddr-platform/ces-backend/tests/test_keywords_route.py`

## Story Context Completion

Ultimate context engine analysis completed — existing GET route and type validation reused; only file persistence, response format, and error shape are new.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
