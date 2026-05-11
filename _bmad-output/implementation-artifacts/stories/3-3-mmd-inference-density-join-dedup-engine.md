# Story 3.3: mMD Inference, Density Join & Dedup Engine

Status: ready-for-dev

Completion note: Ultimate context engine analysis completed - comprehensive developer guide created.

## Story

As a platform developer,
I want the occurrence engine to infer measured depth (mMD), join mud density, and deduplicate occurrences,
So that each occurrence row has accurate depth, the correct density from the nearest mud record, and no duplicate rows.

## Acceptance Criteria

**Given** a time log row with an explicit depth value on the problem line
**When** `occurrence/infer_mmd` processes it
**Then** problem-line stated depth is used as mMD — backward scan is NOT performed
**And** `mmd` field is set to the stated depth value as `float`

**Given** a time log row with no explicit depth on the problem line
**When** `occurrence/infer_mmd` performs backward scan
**Then** time log rows are scanned backward from the problem row to find the most recent row with a depth value
**And** that depth value is assigned as mMD
**And** if no depth found in backward scan, `mmd` is `null`

**Given** an occurrence with an inferred mMD
**When** `occurrence/density_join` runs
**Then** the mud record with depth closest to the occurrence's mMD (within the same tour) is selected
**And** that mud record's `mud_weight` value (kg/m³) is assigned to the occurrence's `density` field
**And** cross-tour density lookup is never performed — same-tour constraint enforced by passing only same-date mud_records

**Given** an occurrence with no mMD (`mmd` is `None`)
**When** `occurrence/density_join` runs
**Then** the last mud record in the date's record list is used as the fallback density source
**And** if no mud records exist at all, `density` is `None`

**Given** multiple occurrences generated for the same DDR
**When** `occurrence/dedup` runs
**Then** occurrences sharing identical `(type, mmd)` pair within the same DDR are deduplicated — only one row kept
**And** dedup preserves the first occurrence encountered (insertion order)
**And** removed occurrence count is logged at `INFO` level — zero occurrences silently dropped

**Given** `ces-backend/tests/fixtures/expected_mmd_inference.json` contains known time_log arrays with expected mMD values
**When** mMD inference test suite runs against those fixtures
**Then** ≥ 85% of inferred mMD values are within ±10m of expected values (FR8 success criterion)

## Tasks / Subtasks

- [ ] Create `src/services/occurrence/infer_mmd.py` (AC: 1, 2)
  - [ ] Implement `infer_mmd(time_log_index: int, time_logs: list[dict]) -> float | None`
  - [ ] Problem-line first: return `float(time_logs[time_log_index]["depth_md"])` if not None
  - [ ] Backward scan: iterate `range(time_log_index - 1, -1, -1)`, return first non-None depth
  - [ ] Return `None` if no depth found anywhere

- [ ] Create `src/services/occurrence/density_join.py` (AC: 3, 4)
  - [ ] Implement `density_join(mmd: float | None, mud_records: list[dict]) -> float | None`
  - [ ] Return `None` if `mud_records` is empty
  - [ ] If `mmd is None`: return `float(mud_records[-1]["mud_weight"])` (last record fallback)
  - [ ] If `mmd is not None`: find mud_record minimizing `abs(float(r["depth_md"]) - mmd)` and return its `mud_weight`

- [ ] Create `src/services/occurrence/dedup.py` (AC: 5)
  - [ ] Implement `dedup(occurrences: list[dict]) -> list[dict]`
  - [ ] Dedup key: `(occ.get("type"), occ.get("mmd"))` — tuple of type string + float-or-None
  - [ ] Preserve first occurrence for each key; skip subsequent duplicates
  - [ ] Log removed count: `logger.info("dedup: removed %d duplicate occurrence(s)", removed)` if removed > 0
  - [ ] Return deduplicated list (may be same list if no duplicates)

- [ ] Create `tests/fixtures/expected_mmd_inference.json` (AC: 6)
  - [ ] At least 20 test cases with known `time_logs` arrays, `problem_index`, and `expected_mmd`
  - [ ] Cover: explicit depth on problem line, backward scan (1 row back), backward scan (multiple rows back), no depth in scan (expected_mmd null), depth at index 0
  - [ ] Format: `[{ "time_logs": [...], "problem_index": N, "expected_mmd": float|null, "description": "..." }]`

- [ ] Write tests (AC: 1–6)
  - [ ] `tests/test_infer_mmd.py` — unit tests for `infer_mmd`
  - [ ] `tests/test_density_join.py` — unit tests for `density_join`
  - [ ] `tests/test_dedup.py` — unit tests for `dedup`
  - [ ] Fixture-driven ≥85% accuracy test in `test_infer_mmd.py`
  - [ ] Run: `source .venv/bin/activate && ruff check . && pytest` from `ces-ddr-platform/ces-backend/`

## Dev Notes

### Module Location

Three new files in the existing `occurrence/` package:

```
ces-ddr-platform/ces-backend/src/services/occurrence/infer_mmd.py    (NEW)
ces-ddr-platform/ces-backend/src/services/occurrence/density_join.py  (NEW)
ces-ddr-platform/ces-backend/src/services/occurrence/dedup.py         (NEW)
```

Existing package:
```
ces-ddr-platform/ces-backend/src/services/occurrence/__init__.py      (empty — do NOT modify)
ces-ddr-platform/ces-backend/src/services/occurrence/classify.py      (do NOT modify)
```

### DDR Data Schema — CRITICAL

These functions operate on raw dicts from `ddr_dates.final_json`. The JSON schema (in `src/resources/ddr_schema.json`) defines:

**`time_logs` array item** — required fields: `start_time`, `end_time`, `duration_hours`, `activity`; optional fields: `depth_md` (float|null), `comment` (str|null)

```python
# Example time_log row
{
    "start_time": "06:00",
    "end_time": "07:30",
    "duration_hours": 1.5,
    "activity": "drilling ahead",
    "depth_md": 1450.0,   # may be None
    "comment": None,
}
```

**`mud_records` array item** — required fields: `depth_md` (float), `mud_weight` (float); optional: `viscosity`, `ph`, `comment`

```python
# Example mud_record row
{
    "depth_md": 1452.0,
    "mud_weight": 1.86,   # density in kg/m³ (or ppg — exact unit from Gemini extraction)
    "viscosity": None,
    "ph": None,
    "comment": None,
}
```

**Existing exports from `classify.py`** (usable in tests):
- `DEFAULT_SURFACE_SHOE_DEPTH = 600.0`
- `DEFAULT_INTERMEDIATE_SHOE_DEPTH = 2500.0`
- `VALID_SECTIONS: frozenset[str]`
- `VALID_OCCURRENCE_TYPES: frozenset[str]`

### `infer_mmd` Implementation

```python
# src/services/occurrence/infer_mmd.py


def infer_mmd(time_log_index: int, time_logs: list[dict]) -> float | None:
    row = time_logs[time_log_index]
    d = row.get("depth_md")
    if d is not None:
        return float(d)
    for i in range(time_log_index - 1, -1, -1):
        d = time_logs[i].get("depth_md")
        if d is not None:
            return float(d)
    return None
```

**Critical rules:**
- Function is pure — takes index + full list, returns float or None
- `time_log_index` is the index of the occurrence's source row in the time_logs array
- Problem-line takes priority: if `depth_md` is not None on that row, use it and stop — do NOT scan
- Backward scan only runs when problem-line depth is None
- Return `None` (not 0.0) when no depth found — `None` propagates correctly to section classifier

### `density_join` Implementation

`mud_records` have no timestamp field in the schema — only `depth_md`. Depth-based proximity is the correct join key for same-tour data (physically: density at nearest measured depth).

```python
# src/services/occurrence/density_join.py


def density_join(mmd: float | None, mud_records: list[dict]) -> float | None:
    if not mud_records:
        return None
    if mmd is None:
        return float(mud_records[-1]["mud_weight"])
    nearest = min(mud_records, key=lambda r: abs(float(r["depth_md"]) - mmd))
    return float(nearest["mud_weight"])
```

**Critical rules:**
- "Same-tour constraint" is satisfied by caller passing only mud_records from the same `ddr_date_id`'s `final_json` — this function never filters by tour
- `mmd is None` fallback → last record (latest logged mud check in the tour)
- Empty list → None (no density data; field stays null in DB — valid state)
- `mud_weight` is the density value (field name from DDR schema); always return as `float`
- No clamping needed — `min()` handles both ends naturally

### `dedup` Implementation

```python
# src/services/occurrence/dedup.py
import logging

logger = logging.getLogger(__name__)


def dedup(occurrences: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []
    removed = 0
    for occ in occurrences:
        key = (occ.get("type"), occ.get("mmd"))
        if key not in seen:
            seen.add(key)
            result.append(occ)
        else:
            removed += 1
    if removed:
        logger.info("dedup: removed %d duplicate occurrence(s)", removed)
    return result
```

**Critical rules:**
- Key is `(type, mmd)` as a tuple — `mmd` may be `None` (Python None is hashable and works in sets)
- Two occurrences with `mmd=None` of the same type ARE duplicates — only first kept
- First occurrence wins — insertion order is authoritative
- Log ONLY when removed > 0 — no log output for clean runs (avoids test noise)
- `occ.get("type")` not `occ["type"]` — defensive for malformed dicts in tests

### Test Fixture — `tests/fixtures/expected_mmd_inference.json`

Create with at least 20 cases. Required format:

```json
[
  {
    "description": "explicit depth on problem line",
    "time_logs": [
      {"start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0, "activity": "drilling", "depth_md": 1450.0, "comment": null},
      {"start_time": "07:00", "end_time": "08:00", "duration_hours": 1.0, "activity": "stuck pipe", "depth_md": 1455.0, "comment": null}
    ],
    "problem_index": 1,
    "expected_mmd": 1455.0
  },
  {
    "description": "no depth on problem line — backward scan 1 row",
    "time_logs": [
      {"start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0, "activity": "drilling", "depth_md": 1430.0, "comment": null},
      {"start_time": "07:00", "end_time": "08:00", "duration_hours": 1.0, "activity": "stuck pipe", "depth_md": null, "comment": null}
    ],
    "problem_index": 1,
    "expected_mmd": 1430.0
  },
  {
    "description": "no depth on problem line — backward scan multiple rows",
    "time_logs": [
      {"start_time": "05:00", "end_time": "06:00", "duration_hours": 1.0, "activity": "trip in", "depth_md": 2300.0, "comment": null},
      {"start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0, "activity": "reaming", "depth_md": null, "comment": null},
      {"start_time": "07:00", "end_time": "08:00", "duration_hours": 1.0, "activity": "lost circulation", "depth_md": null, "comment": null}
    ],
    "problem_index": 2,
    "expected_mmd": 2300.0
  },
  {
    "description": "no depth anywhere — returns null",
    "time_logs": [
      {"start_time": "06:00", "end_time": "07:00", "duration_hours": 1.0, "activity": "stuck pipe", "depth_md": null, "comment": null}
    ],
    "problem_index": 0,
    "expected_mmd": null
  },
  {
    "description": "problem line is first row, has explicit depth",
    "time_logs": [
      {"start_time": "00:00", "end_time": "01:00", "duration_hours": 1.0, "activity": "washout detected", "depth_md": 980.0, "comment": null},
      {"start_time": "01:00", "end_time": "02:00", "duration_hours": 1.0, "activity": "drilling", "depth_md": 990.0, "comment": null}
    ],
    "problem_index": 0,
    "expected_mmd": 980.0
  }
]
```

The fixture test checks ≥ 85% accuracy (≥17/20 cases) — allow 3 misses for unexpected None-handling edge cases. Design your fixture so 100% pass with correct implementation, but the 85% threshold is the hard floor.

### Test File Patterns

Follow flat test directory pattern (no subdirectory), matching existing project convention:

```
tests/test_infer_mmd.py       (NEW)
tests/test_density_join.py    (NEW)
tests/test_dedup.py           (NEW)
tests/fixtures/expected_mmd_inference.json  (NEW)
```

**`test_infer_mmd.py` key tests:**

```python
from src.services.occurrence.infer_mmd import infer_mmd

def _log(start, end, depth, activity="drilling"):
    return {"start_time": start, "end_time": end, "duration_hours": 1.0,
            "activity": activity, "depth_md": depth, "comment": None}

def test_uses_problem_line_depth_when_present():
    logs = [_log("06:00", "07:00", 1400.0), _log("07:00", "08:00", 1455.0, "stuck pipe")]
    assert infer_mmd(1, logs) == 1455.0

def test_backward_scan_one_row():
    logs = [_log("06:00", "07:00", 1430.0), _log("07:00", "08:00", None, "stuck pipe")]
    assert infer_mmd(1, logs) == 1430.0

def test_backward_scan_multiple_rows():
    logs = [_log("05:00", "06:00", 2300.0), _log("06:00", "07:00", None), _log("07:00", "08:00", None, "kick")]
    assert infer_mmd(2, logs) == 2300.0

def test_returns_none_when_no_depth_anywhere():
    logs = [_log("07:00", "08:00", None, "stuck pipe")]
    assert infer_mmd(0, logs) is None

def test_problem_line_skips_later_rows():
    # backward scan must not look FORWARD
    logs = [_log("07:00", "08:00", None, "stuck pipe"), _log("08:00", "09:00", 1500.0)]
    assert infer_mmd(0, logs) is None

def test_returns_float_not_int():
    logs = [_log("07:00", "08:00", 1450, "stuck pipe")]  # int in dict
    result = infer_mmd(0, logs)
    assert result == 1450.0
    assert isinstance(result, float)

def test_fixture_accuracy():
    import json
    from pathlib import Path
    cases = json.loads((Path(__file__).parent / "fixtures" / "expected_mmd_inference.json").read_text())
    correct = 0
    for c in cases:
        result = infer_mmd(c["problem_index"], c["time_logs"])
        expected = c["expected_mmd"]
        if expected is None:
            if result is None:
                correct += 1
        elif result is not None and abs(result - expected) <= 10.0:
            correct += 1
    accuracy = correct / len(cases)
    assert accuracy >= 0.85, f"mMD inference accuracy {accuracy:.1%} below 85% ({correct}/{len(cases)})"
```

**`test_density_join.py` key tests:**

```python
from src.services.occurrence.density_join import density_join

def _mud(depth, weight):
    return {"depth_md": depth, "mud_weight": weight, "viscosity": None, "ph": None, "comment": None}

def test_nearest_depth_exact_match():
    records = [_mud(1400.0, 1.80), _mud(1450.0, 1.85), _mud(1500.0, 1.90)]
    assert density_join(1450.0, records) == 1.85

def test_nearest_depth_between_records():
    records = [_mud(1400.0, 1.80), _mud(1500.0, 1.90)]
    # 1430 is closer to 1400 than 1500
    assert density_join(1430.0, records) == 1.80

def test_nearest_depth_above_all():
    records = [_mud(1000.0, 1.75), _mud(1200.0, 1.80)]
    assert density_join(2000.0, records) == 1.80  # nearest = 1200

def test_none_mmd_returns_last_record():
    records = [_mud(1000.0, 1.75), _mud(1200.0, 1.80), _mud(1400.0, 1.85)]
    assert density_join(None, records) == 1.85

def test_empty_records_returns_none():
    assert density_join(1450.0, []) is None
    assert density_join(None, []) is None

def test_single_record_always_selected():
    records = [_mud(1000.0, 1.82)]
    assert density_join(5000.0, records) == 1.82  # only option

def test_returns_float():
    records = [_mud(1450, 2)]  # ints in dict
    result = density_join(1450.0, records)
    assert isinstance(result, float)
```

**`test_dedup.py` key tests:**

```python
from src.services.occurrence.dedup import dedup

def _occ(type_, mmd):
    return {"type": type_, "mmd": mmd, "notes": "test"}

def test_no_duplicates_returns_same():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Lost Circulation", 2300.0)]
    assert dedup(occs) == occs

def test_removes_exact_type_mmd_duplicate():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0)]
    result = dedup(occs)
    assert len(result) == 1
    assert result[0] is occs[0]  # first preserved

def test_same_type_different_mmd_not_deduped():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1460.0)]
    assert len(dedup(occs)) == 2

def test_same_mmd_different_type_not_deduped():
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Lost Circulation", 1450.0)]
    assert len(dedup(occs)) == 2

def test_none_mmd_deduped_by_type():
    occs = [_occ("Stuck Pipe", None), _occ("Stuck Pipe", None)]
    assert len(dedup(occs)) == 1

def test_none_mmd_different_types_not_deduped():
    occs = [_occ("Stuck Pipe", None), _occ("Lost Circulation", None)]
    assert len(dedup(occs)) == 2

def test_preserves_first_insertion_order():
    occs = [
        {"type": "Stuck Pipe", "mmd": 1450.0, "notes": "first"},
        {"type": "Stuck Pipe", "mmd": 1450.0, "notes": "second"},
    ]
    result = dedup(occs)
    assert result[0]["notes"] == "first"

def test_empty_list_returns_empty():
    assert dedup([]) == []

def test_logs_removed_count(caplog):
    import logging
    occs = [_occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0), _occ("Stuck Pipe", 1450.0)]
    with caplog.at_level(logging.INFO, logger="src.services.occurrence.dedup"):
        result = dedup(occs)
    assert len(result) == 1
    assert "removed 2" in caplog.text

def test_no_log_when_no_duplicates(caplog):
    import logging
    occs = [_occ("Stuck Pipe", 1450.0)]
    with caplog.at_level(logging.INFO, logger="src.services.occurrence.dedup"):
        dedup(occs)
    assert caplog.text == ""
```

### Architecture Compliance

- Python-only backend. No frontend files.
- All three modules: pure functions only — no ORM, no DB, no HTTP calls, no config reads.
- No `os.getenv` anywhere in these modules.
- All functions take explicit parameters — no global state.
- `dedup.py` uses stdlib `logging` only (`import logging`) — no fastapi, no sqlalchemy.
- Ruff + pytest must pass clean from `ces-ddr-platform/ces-backend/`.

### Previous Story Intelligence (3-2)

**What was built in 3-2:**
- `src/services/occurrence/classify.py` — exports `classify_type`, `classify_section`, `DEFAULT_SURFACE_SHOE_DEPTH`, `DEFAULT_INTERMEDIATE_SHOE_DEPTH`, `VALID_SECTIONS`, `VALID_OCCURRENCE_TYPES`
- `classify_section` defaults already accept custom shoe depths — story 3.3 passes actual shoe depths from deviation surveys when available (signature is ready, no changes needed)
- `src/services/occurrence/__init__.py` — empty, do NOT add exports to it
- `tests/test_classify.py`, `tests/test_classify_fixture.py`, `tests/test_keywords_route.py` — all must still pass
- 117 tests currently pass (2 pre-existing DB failures in `test_ddr_upload_contract.py` are unrelated — ignore)

**Key decision from 3-2:** `classify_type` uses `re.search` with `\b` word boundaries. The "problem text" passed to it is typically `time_log["activity"]` + optionally `time_log["comment"]` combined. Story 3.4 (occurrence generation pipeline) decides how to build that string; this story's functions receive `time_log_index` and the raw list, not the classified text.

**Deviation surveys for shoe depths:** Story 3-2's `classify_section` defaults to 600m/2500m. Story 3-3 does NOT wire deviation survey data to actual shoe depths — that's story 3.4's concern. Story 3-3 only implements the three pure engine functions.

### File Structure

Files to create:
```
ces-ddr-platform/ces-backend/src/services/occurrence/infer_mmd.py          (NEW)
ces-ddr-platform/ces-backend/src/services/occurrence/density_join.py        (NEW)
ces-ddr-platform/ces-backend/src/services/occurrence/dedup.py               (NEW)
ces-ddr-platform/ces-backend/tests/fixtures/expected_mmd_inference.json     (NEW)
ces-ddr-platform/ces-backend/tests/test_infer_mmd.py                        (NEW)
ces-ddr-platform/ces-backend/tests/test_density_join.py                     (NEW)
ces-ddr-platform/ces-backend/tests/test_dedup.py                            (NEW)
```

No files to update. All new additions.

### Testing Requirements

```bash
# from ces-ddr-platform/ces-backend/
source .venv/bin/activate
ruff check .
pytest
```

All new tests must pass. Existing 117 tests must still pass (2 pre-existing DB failures are unrelated — same before/after).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#FR6–FR11 Occurrence Generation]
- [Source: _bmad-output/implementation-artifacts/stories/3-2-keyword-classification-engine-type-section.md]
- [Source: ces-ddr-platform/ces-backend/src/resources/ddr_schema.json]
- [Source: ces-ddr-platform/ces-backend/src/services/occurrence/classify.py]
- [Source: ces-ddr-platform/ces-backend/src/models/schemas/occurrence.py]
- [Source: ces-ddr-platform/ces-backend/src/repository/crud/occurrence.py]

## Dev Agent Record

### Agent Model Used

_to be filled by dev agent_

### Debug Log References

_to be filled by dev agent_

### Completion Notes List

_to be filled by dev agent_

### File List

_to be filled by dev agent_

### Review Findings

_to be filled by dev agent_

### Change Log

- 2026-05-11: Story created — mMD inference, density join, dedup engine.
