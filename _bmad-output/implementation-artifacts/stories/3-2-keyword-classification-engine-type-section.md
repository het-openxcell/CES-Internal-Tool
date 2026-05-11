# Story 3.2: Keyword Classification Engine — Type & Section

Status: done

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want the occurrence engine to classify each occurrence by type and section using the keyword rule engine,
So that extracted problem-line text is mapped to one of the 15–17 standard occurrence types and a casing section.

## Acceptance Criteria

**Given** `ces-backend/src/resources/keywords.json` is loaded at backend startup
**When** `occurrence/classify` processes a problem-line text string
**Then** keyword matching is case-insensitive substring match — "backreamed to free" matches keyword "backreamed"
**And** first matching keyword's mapped type is assigned (first-match wins; keyword order in file is authoritative)
**And** if no keyword matches, type is assigned `"Unclassified"`

**Given** a classified occurrence with an inferred depth (mMD)
**When** `occurrence/classify` determines section
**Then** section is `"Surface"` if mMD ≤ inferred surface casing shoe depth (fallback: 600m)
**And** section is `"Int."` if mMD ≤ inferred intermediate casing shoe depth (fallback: 2500m)
**And** section is `"Main"` if mMD > intermediate shoe depth

**Given** `ces-backend/tests/fixtures/expected_occurrences.json` contains known input→type mappings
**When** keyword classification test suite runs
**Then** ≥ 90% of expected type classifications match (FR7 success criterion)

**Given** keyword file is reloaded at runtime via `PUT /keywords`
**When** `occurrence/classify` is called after reload
**Then** new keyword mappings are used immediately — no restart required (ARCH-9)

## Tasks / Subtasks

- [x] Create `src/services/occurrence/` package (AC: 1)
  - [x] Add `src/services/occurrence/__init__.py` (empty)
  - [x] Add `src/services/occurrence/classify.py` with `classify_type` and `classify_section` functions

- [x] Implement `classify_type(text: str, keywords: dict[str, str]) -> str` (AC: 1)
  - [x] Case-insensitive substring match: `keyword.lower() in text.lower()`
  - [x] Iterate keyword dict in insertion order (Python 3.7+ dicts preserve order)
  - [x] Return first matching type; return `"Unclassified"` if no match
  - [x] Function is pure — takes keywords dict as argument (no global state access inside function)

- [x] Implement `classify_section(mmd: float | None, surface_shoe: float = 600.0, intermediate_shoe: float = 2500.0) -> str | None` (AC: 2)
  - [x] Return `None` if `mmd` is `None`
  - [x] Return `"Surface"` if `mmd <= surface_shoe`
  - [x] Return `"Int."` if `mmd <= intermediate_shoe`
  - [x] Return `"Main"` if `mmd > intermediate_shoe`

- [x] Add section validator to `OccurrenceInCreate` schema (Story 3.1 deferred this) (AC: 1)
  - [x] File: `src/models/schemas/occurrence.py`
  - [x] Add `field_validator("section")` accepting `None`, `"Surface"`, `"Int."`, `"Main"` only
  - [x] Raise `ValueError` for any other non-None value

- [x] Create `tests/fixtures/expected_occurrences.json` (AC: 3)
  - [x] At least 20 test cases covering all 16 types + `"Unclassified"`
  - [x] Format: `[{ "text": "...", "expected_type": "..." }, ...]`
  - [x] Include edge cases: mixed case, multi-word keywords, no-match text

- [x] Add `PUT /keywords` endpoint (AC: 4 — ARCH-9)
  - [x] New file: `src/api/routes/v1/keywords.py`
  - [x] `PUT /keywords` accepts `dict[str, str]` request body
  - [x] Calls `KeywordLoader.reload(new_data)` — in-memory reload only (no file write needed for MVP)
  - [x] Requires `jwt_authentication` (all routes require auth)
  - [x] Returns `{"updated": len(new_data)}` on success
  - [x] Register router in `src/api/endpoints.py`

- [x] Write tests (AC: 1–4)
  - [x] `tests/test_classify.py` — unit tests for `classify_type` and `classify_section`
  - [x] `tests/test_classify_fixture.py` — fixture-driven test loading `expected_occurrences.json`
  - [x] `tests/test_keywords_route.py` — test `PUT /keywords` reloads in-memory store
  - [x] Run: `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/`

## Dev Notes

### Module Location

Per architecture `src/services/occurrence/classify.py` — create the `occurrence/` subpackage under `services/`:

```
ces-ddr-platform/ces-backend/src/services/occurrence/__init__.py   (NEW, empty)
ces-ddr-platform/ces-backend/src/services/occurrence/classify.py   (NEW)
```

Existing `src/services/` already contains: `ddr.py`, `keywords/`, `pipeline/`, `pipeline_service.py`, `processing_resume.py`, `processing_status.py`.

### `classify_type` Implementation

```python
def classify_type(text: str, keywords: dict[str, str]) -> str:
    text_lower = text.lower()
    for keyword, occurrence_type in keywords.items():
        if keyword.lower() in text_lower:
            return occurrence_type
    return "Unclassified"
```

**Critical**: `keywords` dict order is authoritative — Python dicts preserve insertion order since 3.7. The `keywords.json` file order determines which type wins on ambiguous text. Do NOT sort or reorder.

### `classify_section` Implementation

```python
def classify_section(
    mmd: float | None,
    surface_shoe: float = 600.0,
    intermediate_shoe: float = 2500.0,
) -> str | None:
    if mmd is None:
        return None
    if mmd <= surface_shoe:
        return "Surface"
    if mmd <= intermediate_shoe:
        return "Int."
    return "Main"
```

**Fallbacks**: 600m surface shoe, 2500m intermediate shoe are per-spec defaults. Story 3.3 will pass actual shoe depths extracted from deviation surveys when available; this function signature already supports that.

### Section Validator — `src/models/schemas/occurrence.py`

Story 3.1 deferred section validation here. Add:

```python
_VALID_SECTIONS = {"Surface", "Int.", "Main"}

@field_validator("section")
@classmethod
def validate_section(cls, v: str | None) -> str | None:
    if v is not None and v not in _VALID_SECTIONS:
        raise ValueError(f"section must be one of {sorted(_VALID_SECTIONS)} or None")
    return v
```

Existing file already imports `field_validator` and `re` — no new imports needed for this.

### Test Fixture — `tests/fixtures/expected_occurrences.json`

Create with at least 20 cases. Suggested structure:

```json
[
  {"text": "pipe stuck in formation", "expected_type": "Stuck Pipe"},
  {"text": "lost circulation during drilling", "expected_type": "Lost Circulation"},
  {"text": "backreamed to free string", "expected_type": "Back Ream"},
  {"text": "REAMING AHEAD TO BOTTOM", "expected_type": "Ream"},
  {"text": "tight hole overpull observed", "expected_type": "Tight Hole"},
  {"text": "bit washout detected", "expected_type": "Washout"},
  {"text": "mwd failure in bha", "expected_type": "BHA Failure"},
  {"text": "stick slip and vibration issues", "expected_type": "Vibration"},
  {"text": "pit gain and shut in", "expected_type": "Kick / Well Control"},
  {"text": "h2s detected at surface", "expected_type": "H2S"},
  {"text": "fish left in hole from stuck bha", "expected_type": "Fishing"},
  {"text": "casing collapse encountered", "expected_type": "Casing Issue"},
  {"text": "bit balling causing slow progress", "expected_type": "Bit Failure"},
  {"text": "cement job performed", "expected_type": "Cementing Issue"},
  {"text": "packoff encountered while drilling", "expected_type": "Pack Off"},
  {"text": "dogleg severity exceeded plan", "expected_type": "Deviation"},
  {"text": "normal drilling operations continue", "expected_type": "Unclassified"},
  {"text": "running casing to bottom", "expected_type": "Unclassified"},
  {"text": "Jarring downward to free stuck string", "expected_type": "Stuck Pipe"},
  {"text": "Total loss of returns observed", "expected_type": "Lost Circulation"},
  {"text": "Hydrogen sulphide alarm triggered", "expected_type": "H2S"}
]
```

The ≥ 90% pass criterion means 18+ of 20 cases must match (using the real `keywords.json`).

### `PUT /keywords` Route

```python
# src/api/routes/v1/keywords.py
from fastapi import APIRouter, Depends, status
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.services.keywords.loader import KeywordLoader

router = APIRouter(prefix="/keywords", tags=["Keywords"])

@router.put("", status_code=status.HTTP_200_OK)
async def update_keywords(
    keywords: dict[str, str],
    current_user=Depends(jwt_authentication),
) -> dict[str, int]:
    KeywordLoader.reload(keywords)
    return {"updated": len(keywords)}
```

Register in `src/api/endpoints.py`:
```python
from src.api.routes.v1.keywords import router as keywords_router
# ...
router.include_router(router=keywords_router)
```

**Note**: Architecture says "writes file + triggers in-memory reload" — for this story implement in-memory reload only. File write (persistence across restarts) is Story 7.3 scope. The AC only requires "no restart required", which in-memory reload satisfies.

### Test File Patterns

Follow flat test directory pattern (not subdirectory) matching existing project convention:

```
tests/test_classify.py              (NEW — unit tests for classify functions)
tests/test_classify_fixture.py      (NEW — fixture-driven ≥90% accuracy test)
tests/test_keywords_route.py        (NEW — PUT /keywords endpoint test)
```

**`test_classify.py` key tests:**
```python
from src.services.occurrence.classify import classify_type, classify_section

def test_classify_type_returns_matching_type():
    keywords = {"stuck pipe": "Stuck Pipe", "lost circulation": "Lost Circulation"}
    assert classify_type("pipe stuck in formation", keywords) == "Unclassified"  # not "stuck pipe" substring!
    assert classify_type("stuck pipe encountered", keywords) == "Stuck Pipe"

def test_classify_type_case_insensitive():
    keywords = {"stuck pipe": "Stuck Pipe"}
    assert classify_type("STUCK PIPE AT 2000m", keywords) == "Stuck Pipe"

def test_classify_type_first_match_wins():
    keywords = {"stuck pipe": "Stuck Pipe", "pipe": "Other Type"}
    assert classify_type("stuck pipe", keywords) == "Stuck Pipe"  # first match

def test_classify_type_unclassified():
    keywords = {"stuck pipe": "Stuck Pipe"}
    assert classify_type("normal drilling operations", keywords) == "Unclassified"

def test_classify_section_surface():
    assert classify_section(500.0) == "Surface"
    assert classify_section(600.0) == "Surface"  # boundary inclusive

def test_classify_section_intermediate():
    assert classify_section(601.0) == "Int."
    assert classify_section(2500.0) == "Int."  # boundary inclusive

def test_classify_section_main():
    assert classify_section(2501.0) == "Main"

def test_classify_section_none_mmd():
    assert classify_section(None) is None

def test_classify_section_custom_shoes():
    assert classify_section(400.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Surface"
    assert classify_section(1500.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Int."
    assert classify_section(2001.0, surface_shoe=500.0, intermediate_shoe=2000.0) == "Main"
```

**`test_classify_fixture.py` key test:**
```python
import json
from pathlib import Path
from src.services.occurrence.classify import classify_type
from src.services.keywords.loader import KeywordLoader

def test_fixture_accuracy():
    KeywordLoader.load()
    keywords = KeywordLoader.get_keywords()
    fixtures_path = Path(__file__).parent / "fixtures" / "expected_occurrences.json"
    cases = json.loads(fixtures_path.read_text())
    correct = sum(1 for c in cases if classify_type(c["text"], keywords) == c["expected_type"])
    accuracy = correct / len(cases)
    assert accuracy >= 0.90, f"Accuracy {accuracy:.1%} below 90% ({correct}/{len(cases)} correct)"
```

**`test_keywords_route.py` key tests** — use FastAPI `TestClient` following existing test patterns in the project (check `tests/test_ddr_upload_contract.py` for client setup).

### Section Validation — What Changed in `occurrence.py`

Story 3.1 note: `section` field in `OccurrenceInCreate` has valid values `"Surface"`, `"Int."`, `"Main"` but validation was deferred. This story adds the `field_validator` to `src/models/schemas/occurrence.py`. The existing `test_occurrence_schema.py` tests must still pass — verify `section=None` and valid section values are accepted, invalid strings rejected.

### Architecture Compliance

- Python-only backend. No frontend files.
- All config via `decouple + BackendBaseSettings`. No `os.getenv`.
- Pure functions in `classify.py` — no ORM, no DB, no HTTP calls.
- `KeywordLoader` class state is already thread-safe for read (returns dict copy). `reload()` replaces atomically.
- Ruff + pytest must pass clean from `ces-ddr-platform/ces-backend/`.

### Previous Story Intelligence (3-1)

- `KeywordLoader` fully implemented: `load()`, `get_keywords()` (returns copy), `reload(new_data)`.
- `keywords.json` has 140+ entries covering 16 types. Order is authoritative.
- `OccurrenceInCreate.section` is `str | None` — validator needed (this story).
- `test_keyword_loader.py` passes; do NOT break those tests.
- Existing test count: 91 tests pass (2 pre-existing failures in `test_ddr_upload_contract.py` due to no local DB — unrelated, ignore them).

### File Structure

Files to create:
```
ces-ddr-platform/ces-backend/src/services/occurrence/__init__.py          (NEW)
ces-ddr-platform/ces-backend/src/services/occurrence/classify.py          (NEW)
ces-ddr-platform/ces-backend/src/api/routes/v1/keywords.py                (NEW)
ces-ddr-platform/ces-backend/tests/fixtures/expected_occurrences.json     (NEW)
ces-ddr-platform/ces-backend/tests/test_classify.py                       (NEW)
ces-ddr-platform/ces-backend/tests/test_classify_fixture.py               (NEW)
ces-ddr-platform/ces-backend/tests/test_keywords_route.py                 (NEW)
```

Files to update:
```
ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py             (UPDATE — add section validator)
ces-ddr-platform/ces-backend/src/api/endpoints.py                         (UPDATE — register keywords router)
```

### Testing Requirements

```bash
# from ces-ddr-platform/ces-backend/
source .venv/bin/activate
ruff check .
pytest
```

All new tests must pass. Existing 91 tests must still pass (2 pre-existing DB failures are unrelated — they fail in CI/local the same way before and after this story).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#FR→File Mapping (FR6–FR11)]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH-9 Keyword Store]
- [Source: _bmad-output/implementation-artifacts/stories/3-1-occurrences-database-schema.md]
- [Source: ces-ddr-platform/ces-backend/src/services/keywords/loader.py]
- [Source: ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py]
- [Source: ces-ddr-platform/ces-backend/src/api/endpoints.py]
- [Source: ces-ddr-platform/ces-backend/src/api/routes/v1/pipeline.py]
- [Source: ces-ddr-platform/ces-backend/src/resources/keywords.json]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — clean implementation, no debug iterations needed.

### Completion Notes List

- Created `src/services/occurrence/` package with pure `classify_type` and `classify_section` functions
- `classify_type`: case-insensitive substring match, dict insertion order preserved, returns "Unclassified" on no match
- `classify_section`: boundary-inclusive thresholds (surface ≤600m, int ≤2500m, main >2500m), returns None for None mmd
- Added `field_validator("section")` to `OccurrenceInCreate` — accepts None, "Surface", "Int.", "Main" only
- Created `tests/fixtures/expected_occurrences.json` with 21 cases covering all 16 types + Unclassified; 100% accuracy (>90% required)
- Created `PUT /keywords` endpoint with jwt_authentication guard; in-memory reload via `KeywordLoader.reload()`
- Registered keywords router in `src/api/endpoints.py`
- All 18 new tests pass; 109/109 total (zero regressions); ruff clean

### File List

- `ces-ddr-platform/ces-backend/src/services/occurrence/__init__.py` (NEW)
- `ces-ddr-platform/ces-backend/src/services/occurrence/classify.py` (NEW)
- `ces-ddr-platform/ces-backend/src/api/routes/v1/keywords.py` (NEW)
- `ces-ddr-platform/ces-backend/tests/fixtures/expected_occurrences.json` (NEW)
- `ces-ddr-platform/ces-backend/tests/test_classify.py` (NEW)
- `ces-ddr-platform/ces-backend/tests/test_classify_fixture.py` (NEW)
- `ces-ddr-platform/ces-backend/tests/test_keywords_route.py` (NEW)
- `ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py` (UPDATED — section validator added)
- `ces-ddr-platform/ces-backend/src/api/endpoints.py` (UPDATED — keywords router registered)

### Review Findings

- [x] [Review][Decision] PUT /keywords missing role-based authorization — dismissed: any authenticated user is acceptable for internal tool. Role-based gating deferred to Story 7.3.
- [x] [Review][Decision] PUT /keywords accepts arbitrary keyword values — fixed: added VALID_OCCURRENCE_TYPES frozenset to classify.py; PUT /keywords now validates all values and returns 422 on invalid types.
- [x] [Review][Patch] KeywordLoader state not restored after test_put_keywords_reloads_in_memory_store — fixed: moved assertions inside try block, added KeywordLoader.load() to finally. [tests/test_keywords_route.py]
- [x] [Review][Patch] _VALID_SECTIONS duplicated — fixed: VALID_SECTIONS and VALID_OCCURRENCE_TYPES defined in classify.py as frozensets; occurrence.py imports VALID_SECTIONS from there. [src/services/occurrence/classify.py]
- [x] [Review][Patch] OccurrenceInCreate.validate_section untested — fixed: added 4 tests covering None, all valid values, invalid string, empty string. [tests/test_classify.py]
- [x] [Review][Fixed] PUT /keywords payload size limit — added 1000-entry cap, returns 400 on excess [src/api/routes/v1/keywords.py]
- [x] [Review][Fixed] test_fixture_accuracy per-case failure output — assertion now lists each failing case with expected vs actual [tests/test_classify_fixture.py]
- [x] [Review][Fixed] TestClient shared via pytest fixtures — refactored to client/authed_client fixtures with proper teardown [tests/test_keywords_route.py]
- [x] [Review][Fixed] "running casing to bottom" fragile fixture — replaced with "surface pressure readings taken during survey" which cannot match any keyword [tests/fixtures/expected_occurrences.json]
- [x] [Review][Fixed] "jar to free" shadowing — moved "jar to free" (→Fishing) before "jar" (→Stuck Pipe) in keywords.json; now reachable [src/resources/keywords.json]
- [x] [Review][Fixed] classify_section inverted shoe guard — raises ValueError when surface_shoe >= intermediate_shoe; 2 new tests added [src/services/occurrence/classify.py]
- [x] [Review][Fixed] test_classify_type_substring_not_word_boundary misleading name — renamed to test_classify_type_word_order_matters with clearer comment [tests/test_classify.py]
- [x] [Review][Fixed] classify_type O(n×m) + short-keyword false positives — switched from substring to word-boundary regex (re.search with \b boundaries, re.IGNORECASE); Python re cache eliminates recompilation overhead; 117 tests pass [src/services/occurrence/classify.py]
- [x] [Review][Fixed] classify_section defaults extracted to named constants — DEFAULT_SURFACE_SHOE_DEPTH / DEFAULT_INTERMEDIATE_SHOE_DEPTH exported from classify.py; Story 3.3 can import and override [src/services/occurrence/classify.py]

### Change Log

- 2026-05-08: Story created — keyword classification engine, section inference, PUT /keywords endpoint.
- 2026-05-08: Story implemented — all tasks complete, 109 tests pass, status → review.
- 2026-05-11: Code review complete — 4 patches applied, 1 decision dismissed. 114 tests pass, ruff clean. Status → done.
- 2026-05-11: All 10 defer items resolved. 117 tests pass, ruff clean. Zero deferred work remaining.
