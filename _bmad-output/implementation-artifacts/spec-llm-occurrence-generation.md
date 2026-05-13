---
title: 'LLM-Based Occurrence Generation'
type: 'feature'
created: '2026-05-13'
status: 'done'
baseline_commit: '774286e486ac6d924ddd1f16e6bc87df6fa72b48'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Current occurrence generation uses a keyword regex engine (`classify_type`) that misses semantic context and requires manual keyword maintenance. Results are brittle when time log phrasing varies.

**Approach:** Replace keyword classification with a Gemini LLM call that receives all time logs formatted by date, identifies occurrences from full narrative context, and returns typed results. Deterministic post-processors (`classify_section`, `density_join`, `dedup`) run unchanged on LLM output. On retry, existing occurrences are passed back as context.

## Boundaries & Constraints

**Always:**
- Valid type must be one of the 32 `VALID_OCCURRENCE_TYPES` in `classify.py` — reject any LLM output with unrecognized type
- `classify_section`, `density_join`, `dedup` remain unchanged and run on LLM output
- Use `settings.GEMINI_MODEL` (default `gemini-2.5-flash-lite`) and `settings.GEMINI_API_KEY`
- Wait for all dates to be done before generating — pipeline already guarantees this, no change needed
- `replace_for_ddr` is idempotent — safe to re-run on retry

**Ask First:**
- If LLM returns zero occurrences for a DDR that had keyword-based occurrences before — ask before treating as valid empty result

**Never:**
- Do not modify `infer_mmd`, `classify_section`, `density_join`, or `dedup`
- Do not change `pipeline_service._generate_occurrences` signature
- Do not add corrections injection (4-1 not yet implemented)
- Do not fall back to keyword engine — LLM is the sole classifier

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal generation | All dates successful, no existing occurrences | LLM classifies, section/density applied, deduped rows written | — |
| Retry with existing | `occurrences` table already has rows for this DDR | Existing occurrences serialized and appended to prompt as context | Read before `replace_for_ddr` deletes them |
| LLM returns unknown type | `type: "Washout"` not in `VALID_OCCURRENCE_TYPES` | Row skipped, logged as warning | Continue processing rest |
| LLM returns null mmd | `mmd: null` | `section: null`, `density: null` (same as current keyword path) | — |
| All dates failed | No successful `DDRDate` rows | Return 0, no LLM call made | — |
| Gemini 429 / rate limit | API rate limit hit | Exponential backoff 1s→2s→4s→8s (mirror extraction retry pattern) | Raise after 4 retries |

</frozen-after-approval>

## Code Map

- `ces-backend/src/services/occurrence/generate.py` — current keyword-based service; `_generate_occurrences` in pipeline calls this
- `ces-backend/src/services/occurrence/classify.py` — `VALID_OCCURRENCE_TYPES`, `classify_section` — unchanged, used post-LLM
- `ces-backend/src/services/occurrence/density_join.py` — `density_join` — unchanged
- `ces-backend/src/services/occurrence/dedup.py` — `dedup` — unchanged
- `ces-backend/src/services/pipeline/extract.py` — `GoogleGenAIClient` — do NOT reuse for text-only call (always sends PDF part)
- `ces-backend/src/config/settings/base.py` — `settings.GEMINI_MODEL`, `settings.GEMINI_API_KEY`
- `ces-backend/src/services/pipeline_service.py` — `_generate_occurrences` (line 278) — update to call new service
- `ces-backend/src/repository/crud/occurrence.py` — `replace_for_ddr`, `get_by_ddr_id_filtered` — read existing before replace

## Tasks & Acceptance

**Execution:**
- [x] `src/services/occurrence/llm_generate.py` -- CREATE `LLMOccurrenceGenerationService` -- new LLM-based classifier
  - `__init__(self, ddr_date_repository, occurrence_repository)` — create `google.genai.Client(api_key=settings.GEMINI_API_KEY)` directly (NOT `GoogleGenAIClient` — it always sends a PDF part); store `settings.GEMINI_MODEL`
  - Pydantic response schema: `LLMOccurrenceItem(date: str, type: str, mmd: float | None, notes: str | None = None)` + `LLMOccurrenceResponse(occurrences: list[LLMOccurrenceItem])`
  - `_format_time_logs(rows) -> str` — KEEP: builds prompt block per date `=== YYYYMMDD ===\n[i] HH:MM-HH:MM (Xh) | {depth_md}m | activity comment`; depth shown as `-` when null
  - `_format_existing(occurrences) -> str` — KEEP: serializes as `- date | type | mmd | notes` lines
  - `async generate_for_ddr(ddr_id, ddr_well_name, ddr_surface_location, surface_shoe, intermediate_shoe) -> int`
    1. Guard: if `surface_shoe >= intermediate_shoe` raise `ValueError` immediately (before any DB calls)
    2. Fetch all `DDRDate` rows; filter successful; return 0 if none
    3. Read existing occurrences via `occurrence_repository.get_by_ddr_id_filtered(ddr_id, None, None, None, None)`
    4. Build prompt: system role + valid types list + formatted time logs + existing occurrences block (if any)
    5. Call `client.aio.models.generate_content(model=self._model, contents=[types.Part.from_text(prompt)], config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=LLMOccurrenceResponse.model_json_schema()))`; retry on 429 (backoff 1s/2s/4s/8s, max 4 attempts); use same `_is_rate_limit` signal check as extraction pipeline
    6. Parse: `logger.debug("LLM raw response: %s", result.text)`; wrap `json.loads(result.text)` + `LLMOccurrenceResponse(**parsed)` in try/except `(json.JSONDecodeError, ValidationError, Exception)` — on error log `logger.error("LLM parse failed: %s | raw: %.500s", exc, result.text)` and return 0
    7. For each item: skip if type not in `VALID_OCCURRENCE_TYPES` (log warning); skip if date not in `date_map` (log warning); run `classify_section(mmd, surface_shoe, intermediate_shoe)` + `density_join(mmd, mud_records_for_date)`
    8. `dedup(all_occurrences)` then `replace_for_ddr(ddr_id, deduped)`; return count
  - Rate limit signals: `("429", "rate limit", "ratelimit", "resource_exhausted", "quota", "too many requests")`

- [x] `src/services/pipeline_service.py` -- UPDATE `_generate_occurrences` -- swap to `LLMOccurrenceGenerationService`
  - Replace `OccurrenceGenerationService` import + instantiation with `LLMOccurrenceGenerationService`
  - Signature unchanged: `async _generate_occurrences(self, ddr_id, well_name, surface_location) -> int`

**Acceptance Criteria:**
- Given a DDR with successful dates, when `_generate_occurrences` runs, then `LLMOccurrenceGenerationService.generate_for_ddr` is called (not keyword engine)
- Given LLM returns occurrences with valid types, when written to DB, then `classify_section` and `density_join` values are populated using existing deterministic logic
- Given LLM returns a type not in `VALID_OCCURRENCE_TYPES`, when processing, then that row is skipped and a warning is logged
- Given occurrences already exist for this DDR, when `generate_for_ddr` runs again (retry), then existing occurrences appear in the LLM prompt as context before `replace_for_ddr` overwrites them
- Given all DDRDate rows are failed, when `generate_for_ddr` is called, then returns 0 without calling LLM
- Given Gemini returns 429, when retrying, then exponential backoff applied; raises after 4 failed attempts

## Design Notes

**Prompt structure (golden example):**
```
You are a drilling engineering expert. From the time logs below, identify occurrences —
drilling events or problems. Use ONLY the valid types listed.

VALID TYPES: Anhydrite, Back Ream, Ballooning, Bit Balling, Bit DBR, Blowout, CO2,
Calcite, Cement Plug, Coal, F.I.T. / L.O.T., Fishing, Foaming, Formation Fracture,
Gas Spike, Gravel, H2S, High Torque, Kick / Well Control, Lost Circulation, Mud Ring,
Other, Pressure Loss, Pressure Spike, Ream, Sand, Sidetrack, Sloughing, Stuck Pipe,
Tight Hole, Tool Failure, Water Flow

TIME LOGS:
=== 20240315 ===
[0] 06:00-07:30 (1.5h) | 2340m | Reamed tight hole, high drag on connection
[1] 07:30-09:00 (1.5h) | 2350m | Continued reaming to bottom

PREVIOUSLY GENERATED OCCURRENCES (context for refinement):
- 20240315 | Tight Hole | 2340.0 | Reamed tight hole, high drag on connection
```

**Gemini SDK usage (text-only — do NOT use `GoogleGenAIClient`):**
```python
from google import genai
from google.genai import types
from pydantic import ValidationError

client = genai.Client(api_key=settings.GEMINI_API_KEY)
response = await client.aio.models.generate_content(
    model=self._model,
    contents=[types.Part.from_text(text=prompt)],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=LLMOccurrenceResponse.model_json_schema(),
    ),
)
result_text = response.text  # str | None
```
`GoogleGenAIClient` always attaches a PDF `Part` — passing `b""` sends an empty PDF to the API. Use the SDK directly for text-only generation.

## Spec Change Log

### Loop 1 — 2026-05-13

**Triggering findings (bad_spec):**
1. `json.loads` + `LLMOccurrenceResponse(**parsed)` uncaught — any malformed/null/markdown-wrapped LLM response crashes the function. Spec tasks listed these calls but omitted error handling behavior.
2. `GoogleGenAIClient` with `pdf_bytes=b""` — client always constructs a PDF `Part`; empty bytes sends a zero-byte PDF to Gemini API. Spec said "mirror extraction pattern" but extraction client is not designed for text-only calls.
3. `LLMOccurrenceItem.notes: str` (non-nullable) — LLM can omit or null `notes`; Pydantic validation would crash.

**What was amended (non-frozen sections):**
- Code Map: removed `GoogleGenAIClient` reuse note
- Tasks: `__init__` now uses `google.genai.Client` directly; `notes` field typed `str | None = None`; added shoe validation guard; added `logger.debug` before parse; added try/except around parse step (log + return 0 on failure); added `"ratelimit"` to rate limit signals
- Design Notes: replaced `GoogleGenAIClient` usage note with direct SDK snippet

**Known-bad state avoided:** Empty PDF part causing API rejection; unhandled `JSONDecodeError`/`ValidationError` crashing pipeline with no context.

**KEEP instructions (what worked well — must survive re-derivation):**
- `LLMOccurrenceGenerationService` class structure and init pattern
- `_format_time_logs`, `_format_existing`, `_build_prompt` method implementations
- `_is_rate_limit` check + retry loop structure (4 attempts, backoff 1/2/4/8s)
- `date_map` dict `{row.date: (row.id, final_json)}` for `ddr_date_id` resolution
- `classify_section` / `density_join` / `dedup` post-processing chain
- `replace_for_ddr` as final write step

## Verification

**Commands:**
- `source .venv/bin/activate && ruff check src/services/occurrence/llm_generate.py` -- expected: no errors
- `source .venv/bin/activate && pytest tests/ -k "occurrence" -x` -- expected: existing occurrence tests pass

## Suggested Review Order

**Entry point — pipeline swap**

- Two-line swap: where keyword engine is replaced by LLM service
  [`pipeline_service.py:12`](../../ces-ddr-platform/ces-backend/src/services/pipeline_service.py#L12)

**LLM call & retry**

- Direct `genai.Client` usage (text-only, no PDF part); 4-attempt 429 backoff
  [`llm_generate.py:147`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L147)

- Rate-limit detection: status_code/code with `is not None` guard + string signals
  [`llm_generate.py:53`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L53)

**Response parsing & safety guards**

- Parse + broad except → return 0 (preserves pipeline stability on LLM failure)
  [`llm_generate.py:176`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L176)

- Empty-deduped guard: skips replace when LLM produces no valid rows but existing data exists
  [`llm_generate.py:228`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L228)

**Occurrence validation & post-processing**

- Type + date validation, then deterministic classify_section / density_join / dedup
  [`llm_generate.py:195`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L195)

**Prompt construction**

- Time log formatting (pre-filtered successful rows only, isinstance list guard)
  [`llm_generate.py:60`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L60)

- Existing occurrences injected as context when present (retry path)
  [`llm_generate.py:100`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L100)

**Pydantic schema**

- `mmd` and `notes` both nullable with defaults — LLM may omit either
  [`llm_generate.py:24`](../../ces-ddr-platform/ces-backend/src/services/occurrence/llm_generate.py#L24)

**Tests**

- Updated pipeline test: mocks `genai.Client`, provides fake JSON response
  [`test_occurrence_generation.py:461`](../../ces-ddr-platform/ces-backend/tests/test_occurrence_generation.py#L461)
