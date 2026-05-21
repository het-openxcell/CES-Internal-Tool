# Story 4.3: Correction Context Builder & Pipeline Injection

Status: done

## Story

As a CES staff member,
I want previous corrections automatically summarized and injected as context into future occurrence generation,
So that the same misclassification is not repeated after it has been corrected once.

## Context: Where Corrections Actually Get Injected (read FIRST)

The epic AC text says "`corrections/context_builder` runs before a new DDR extraction" and "`pipeline/extract` sends the Gemini API call ... corrections context is prepended to the extraction prompt." **That wording is imprecise and you must NOT inject into the raw PDF-extraction prompt.** Reality of this codebase (two distinct Gemini calls):

1. **Raw DDR extraction** (`GeminiDDRExtractor` in `src/services/pipeline/extract.py`, prompt `LLMPrompts.ddr_extraction`): PDF bytes → `time_logs`, `mud_records`, `well_name`, etc. It extracts *raw report data*. It never produces `type`/`section`/`mmd`/`density`/`notes`.
2. **Occurrence generation** (`LLMOccurrenceGenerationService` in `src/services/occurrence/llm_generate.py`, prompt `LLMPrompts.occurrence_generation`): `time_logs` → occurrence rows with `type`, `mmd`, `notes` (then `section`/`density` derived locally).

Corrections store exactly the occurrence-generation output fields (`type`, `section`, `mmd`, `notes`, `density` — see story 4-2). So a correction like "type 'Ream' → 'Back Ream'" is only actionable in the **occurrence generation** prompt. The architecture is explicit and authoritative here:
- `architecture.md:75` — "summarized correction store injected into future **occurrence generation** prompts"
- `architecture.md:627-630` — "Correction Context Injection Cap: ... last 20 corrections, summarized" + the exact summary format

**Decision:** inject the correction context into `LLMPrompts.occurrence_generation` via `LLMOccurrenceGenerationService`. The epic's "extraction" phrasing is the same generic-wording drift seen in story 4-2 (dual-backend / error-shape leftovers). Follow the architecture, not the epic's literal "pipeline/extract".

The "same cap / same format / same test on **both Python backend**" clauses are dual-backend leftovers — the project is **Python-only** now (`sprint-status.yaml#approved_changes.python_only_backend_cleanup`). Ignore all dual-backend wording.

## Acceptance Criteria

1. **Given** the `corrections` table has entries
   **When** `CorrectionContextBuilder.build()` runs before occurrence generation
   **Then** at most the last 20 corrections (ordered by `created_at` descending) are retrieved
   **And** corrections are grouped by `(field_name, original_value, corrected_value)`
   **And** each group is summarized as the **exact** string: `Field '{field_name}': '{original_value}' corrected to '{corrected_value}' ({count} times). Reason: {most_recent_reason}` where `count` is the number of corrections in that group and `most_recent_reason` is the `reason` of the newest correction in the group
   **And** the summary lines are joined into a single context string (one line per group)

2. **Given** fewer than 20 corrections exist
   **When** `CorrectionContextBuilder.build()` runs
   **Then** all available corrections are used (no error, no padding)

3. **Given** no corrections exist
   **When** `CorrectionContextBuilder.build()` runs
   **Then** it returns an empty string `""`
   **And** occurrence generation proceeds with no correction note injected (prompt is byte-identical to the no-corrections baseline)

4. **Given** a non-empty corrections context string
   **When** `LLMOccurrenceGenerationService.generate_for_ddr` builds the Gemini prompt
   **Then** the context is **prepended** to the occurrence-generation prompt as a clearly-labelled "previously corrected — do not repeat" note, ahead of `VALID TYPES` / keyword hints / `CURRENT TIME LOGS`
   **And** the existing keyword-hints and time-logs sections remain intact and unchanged in content

5. **Given** the cap rule (ARCH-10)
   **When** more than 20 corrections exist in the store
   **Then** the context never includes more than 20 source corrections — the oldest are excluded
   **And** a builder test with **25 correction fixtures** confirms only the newest 20 are used (oldest 5 excluded)

6. **Given** occurrence generation runs inside the live pipeline (`PreSplitPipelineService._generate_occurrences`) and the reprocess path (`DDRReprocessService.regenerate_occurrences`)
   **When** a `correction_repository` is wired in
   **Then** the correction context is built and injected on both paths
   **And** when no `correction_repository` is supplied (default `None`), generation still works exactly as today (empty context, no regressions)

## Tasks / Subtasks

- [x] **Task 1: `CorrectionContextBuilder` service** (AC: 1, 2, 3, 5)
  - [x] Create `src/services/correction/__init__.py` and `src/services/correction/context_builder.py`
  - [x] Class `CorrectionContextBuilder` with class constant `MAX_INJECTED_CORRECTIONS = 20`
  - [x] `__init__(self, correction_repository: CorrectionCRUDRepository)` — store repo (no loose functions; CLAUDE.md)
  - [x] `async def build(self) -> str`:
    - [x] `corrections = await self.correction_repository.get_recent(self.MAX_INJECTED_CORRECTIONS)` (reuse existing `get_recent` — do NOT add a new repo method)
    - [x] Defensively slice `corrections[: self.MAX_INJECTED_CORRECTIONS]` so a repo/mocked source returning more than 20 still caps at 20
    - [x] If empty → `return ""`
    - [x] Group by key `(c.field_name, c.original_value, c.corrected_value)` preserving first-seen order (rows already `created_at` desc, so first-seen == most recent). Track `count` and `most_recent_reason` (reason of the first row seen for that key)
    - [x] Format each group with the EXACT template in AC 1 and join with `"\n"`; return the joined string
  - [x] No file comments (CLAUDE.md). Keep method small and self-documenting.

- [x] **Task 2: Prepend correction context in the occurrence-generation prompt** (AC: 4, 3)
  - [x] In `src/constants/prompts.py`, add a `corrections_context: str = ""` parameter to `LLMPrompts.occurrence_generation(...)`
  - [x] When `corrections_context` is non-empty, build a leading block (mirror the `keyword_context` conditional style already in the method) e.g.:
        `"PREVIOUSLY CORRECTED — these were fixed by a human before; do not repeat the same mistake:\n{corrections_context}\n\n"` and place it **before** the existing `"You are a drilling engineering expert..."` body (i.e. prepended to the returned prompt). When empty, prepend nothing (AC 3 byte-identical baseline).
  - [x] Do not alter `VALID TYPES`, `keyword_context`, or `CURRENT TIME LOGS` content.

- [x] **Task 3: Thread context through `LLMOccurrenceGenerationService`** (AC: 4, 6)
  - [x] `src/services/occurrence/llm_generate.py`: add optional `correction_repository: Any | None = None` as the **last** `__init__` param (keep `ddr_date_repository`, `occurrence_repository` positions unchanged — existing tests construct with 2 positional args)
  - [x] In `generate_for_ddr`, after computing `time_logs_text` and before/at `_build_prompt`, build context: `corrections_context = await CorrectionContextBuilder(self.correction_repository).build() if self.correction_repository is not None else ""`
  - [x] Change `_build_prompt(self, time_logs_text)` → `_build_prompt(self, time_logs_text, corrections_context="")`; pass `corrections_context` into `LLMPrompts.occurrence_generation(...)`
  - [x] Import `CorrectionContextBuilder` from `src.services.correction.context_builder`

- [x] **Task 4: Wire `correction_repository` into the pipeline service** (AC: 6)
  - [x] `src/services/pipeline_service.py`: add `correction_repository: Any | None = None` to `PreSplitPipelineService.__init__` (last param) and store `self.correction_repository = correction_repository`
  - [x] In `_generate_occurrences`, pass `correction_repository=self.correction_repository` when constructing `LLMOccurrenceGenerationService`

- [x] **Task 5: Wire at all `PreSplitPipelineService` construction sites** (AC: 6)
  - [x] `src/api/dependencies/services.py#get_pipeline_service`: inject `correction_repository: CorrectionCRUDRepository = Depends(get_repository(CorrectionCRUDRepository))` and pass to the constructor (import already present in this file)
  - [x] `src/services/ddr.py#DDRPipelineTaskBase._default_pipeline_service_factory`: add `correction_repository=CorrectionCRUDRepository(async_session=session)` (import `CorrectionCRUDRepository` is already in `ddr.py`)
  - [x] `src/services/ddr.py#DDRReprocessService`: add `correction_repository: Any | None = None` to `__init__`, store it, and pass `correction_repository=self.correction_repository` in `regenerate_occurrences`'s `PreSplitPipelineService(...)` construction
  - [x] `src/api/dependencies/services.py#get_ddr_reprocess_service`: inject `CorrectionCRUDRepository` and pass to `DDRReprocessService(...)`

- [x] **Task 6: Tests** (AC: 1–6)
  - [x] New `tests/test_correction_context_builder.py` (style: `asyncio.run`, `AsyncMock`/`MagicMock`, no `pytest-asyncio` — match `tests/test_occurrence_generation.py` / `tests/test_corrections_schema.py`)
    - [x] 25-fixture cap test: mock `correction_repository.get_recent` returns 25 distinct `SimpleNamespace`/`MagicMock` rows (distinct keys, descending `created_at`) → `build()` yields exactly 20 lines; the 5 oldest keys are absent (AC 5)
    - [x] Grouping + count + format test: 3 rows sharing `(field_name, original_value, corrected_value)` with different reasons (newest first) → single line with `(3 times)` and `Reason: {newest reason}`, exact string match (AC 1)
    - [x] Empty store → `build()` returns `""` (AC 3)
    - [x] Fewer than 20 (e.g. 4 rows, 2 groups) → 2 lines, all used (AC 2)
    - [x] Assert `build()` requests at most 20 from the repo (`get_recent` called with `20`) AND output capped even if mock returns >20 (defensive slice)
  - [x] Prompt-injection test (new file or extend `tests/test_occurrence_generation.py`): patch `genai.Client`, supply a `correction_repository` mock whose `get_recent` returns ≥1 correction → assert the captured prompt (`generate_content.call_args.kwargs["contents"][0].text`) contains the summary line and the "PREVIOUSLY CORRECTED" label, and that `VALID TYPES` / `CURRENT TIME LOGS` are still present (AC 4)
  - [x] No-repo regression: a `generate_for_ddr` call with `correction_repository=None` produces a prompt without the correction block (AC 3/6) — confirm existing `test_pipeline_service_generate_occurrences_runs_service` and `test_pipeline_service_generate_occurrences_returns_zero_when_no_repo` still pass unchanged
  - [x] Run from `ces-ddr-platform/ces-backend/`: `source .venv/bin/activate && ruff check . && pytest` — all green (271 passed, 0 failed)

### Review Findings

- [x] [Review][Patch] Scope correction context by DDR/well before injection [ces-backend/src/services/correction/context_builder.py:11]
- [x] [Review][Patch] Correction-context failure hard-fails occurrence generation [ces-backend/src/services/occurrence/llm_generate.py:183]

## Dev Notes

### Reuse, Don't Recreate

- `CorrectionCRUDRepository.get_recent(limit: int = 20)` already exists (`src/repository/crud/correction.py:65-69`) and orders by `created_at desc` with `_MAX_LIMIT` cap. **Use it directly. Do not add a new "last 20" repo method.**
- `Correction` model fields available on each row: `field_name`, `original_value`, `corrected_value`, `reason`, `created_at` (epoch BigInteger), plus ids. `original_value`/`corrected_value`/`reason` are TEXT and NOT NULL (story 4-1), so no `None`-guarding needed for the format string.
- The keyword-hints conditional in `LLMPrompts.occurrence_generation` (`src/constants/prompts.py:33-44`) is the exact pattern to mirror for the correction block — keep the same "empty → contributes nothing" shape.

### Exact Summary Format (do not paraphrase)

```
Field '{field_name}': '{original_value}' corrected to '{corrected_value}' ({count} times). Reason: {most_recent_reason}
```

Pulled verbatim from `architecture.md:629` and epic AC. The test does an exact string compare — single quotes, the literal ` times). Reason: ` separator, no trailing period after the reason.

### Grouping & "most recent reason" mechanics

`get_recent` returns rows newest-first. Iterate once, keyed by `(field_name, original_value, corrected_value)` into an order-preserving dict:
- first time a key is seen → record `most_recent_reason = row.reason`, `count = 1`
- subsequent rows with same key → `count += 1` (do NOT overwrite the reason — first-seen is newest)

Emit groups in first-seen order (most-recent group first). This is deterministic and matches the desc ordering the AC specifies.

### Cap discipline (ARCH-10)

The cap is **20 source corrections**, applied before grouping. Grouping can only reduce the line count (≤20 lines), never increase it. Pass `MAX_INJECTED_CORRECTIONS` to `get_recent` AND slice `[:MAX_INJECTED_CORRECTIONS]` defensively so a future repo change or a test mock returning more rows can never bloat the prompt. `MAX_INJECTED_CORRECTIONS` lives as a class constant on `CorrectionContextBuilder` (encapsulated-in-class satisfies CLAUDE.md; a separate constants file is unnecessary for a single value).

### Backward-compatibility constraints (avoid new test failures)

Existing passing tests construct services positionally:
- `LLMOccurrenceGenerationService(ddr_date_repo, occurrence_repo)` (2 args) — `correction_repository` MUST be the 3rd, optional, default `None`.
- `PreSplitPipelineService(ddr_repository=..., ddr_date_repository=..., occurrence_repository=...)` — `correction_repository` MUST be optional kw, default `None`.
- `service._generate_occurrences("d1", "Well-X", None)` is called directly in `test_pipeline_service_generate_occurrences_runs_service`; do not change `_generate_occurrences`'s existing signature ordering.

When `correction_repository is None`, `build()` is skipped and `corrections_context=""`, so the prompt is byte-identical to today — that is what keeps the 25 currently-passing occurrence-generation tests green.

### Known pre-existing failure (NOT yours to fix)

`tests/test_occurrence_generation.py::test_llm_generation_allows_model_to_remove_previous_occurrences` is **already failing** on `main` — it asserts the prompt contains `"Validate previous occurrences against current time logs"`, which commit `5f8de4f` ("remove previous occurrences handling from occurrence generation logic") deleted. Baseline before this story: **1 failed, 25 passed**. Do not "fix" it by re-adding previous-occurrence handling — that behavior was intentionally removed. Just don't add new failures. (If trivial and clearly in-scope-adjacent, you may flag it for the reviewer, but leave it failing otherwise.)

### Live call path (trace)

`DDRProcessingTask.process` → `pipeline_service(session).run(ddr_id)` → … → `PreSplitPipelineService._generate_occurrences(ddr_id, well_name, surface_location)` (line ~607) → `LLMOccurrenceGenerationService(ddr_date_repository, occurrence_repository, correction_repository).generate_for_ddr(...)` → `_build_prompt(time_logs_text, corrections_context)` → `LLMPrompts.occurrence_generation(..., corrections_context=...)`. The reprocess path runs through `DDRReprocessService.regenerate_occurrences` → `PreSplitPipelineService(...).regenerate_occurrences(ddr_id)` (same `_generate_occurrences` under the hood). Both must receive `correction_repository`.

### Per-request shared session

In the request-scoped DI (`get_pipeline_service`, `get_ddr_reprocess_service`), `get_repository(CorrectionCRUDRepository)` resolves on the same per-request `AsyncSession` as the other repos (FastAPI caches `get_async_session` per request) — same pattern story 4-2 relied on. In the background task factory (`_default_pipeline_service_factory`), construct `CorrectionCRUDRepository(async_session=session)` against the task's session, exactly like the sibling repos there.

### `src/services/occurrence/generate.py` is NOT the live path

`OccurrenceGenerationService` (keyword-based, `src/services/occurrence/generate.py`) is legacy and only referenced by its own unit tests — the pipeline uses `LLMOccurrenceGenerationService`. **Do not** inject correction context there; it would be dead work and risks touching unrelated tests.

### Project Conventions (CLAUDE.md)

- No file comments. Everything encapsulated in classes/services — `CorrectionContextBuilder` is a service, not loose functions.
- Epoch (`BigInteger` seconds) timestamps — already how `created_at` works; you only read it, no new timestamps.
- Activate venv before running: `source .venv/bin/activate`.
- Reuse before writing new code (checked: `get_recent` exists; do not duplicate).
- `asyncio.to_thread` for blocking sync SDK calls — N/A here (Gemini calls are async; DB I/O is async SQLAlchemy).

### Project Structure Notes

- New service dir `src/services/correction/` mirrors the existing per-domain service folders (`occurrence/`, `keywords/`, `pipeline/`, `export/`). Architecture references this as `corrections/` (`architecture.md:687,831`); singular `correction/` matches the in-repo `occurrence/` convention and the existing `src/repository/crud/correction.py` / `src/models/db/correction.py` naming.
- Prompt text stays centralized in `src/constants/prompts.py` (`LLMPrompts`) — do not inline prompt strings in the service.
- No migration, no schema change, no new API route in this story (review API is story 4-4; inline-edit UI is story 4-5).

### References

- `_bmad-output/planning-artifacts/architecture.md:75` — corrections injected into **occurrence generation** prompts (authoritative injection point)
- `_bmad-output/planning-artifacts/architecture.md:627-630` — injection cap (last 20) + exact summary format (ARCH-10)
- `_bmad-output/planning-artifacts/architecture.md:1009-1012` — correction dataflow (`context_builder recomputes next prompt context (last 20)`)
- `_bmad-output/planning-artifacts/epics.md#Story 4.3` (lines 833-857) — AC source (apply the injection-point correction in Context section above)
- `stories/4-2-occurrence-edit-api-correction-store-write.md` — corrections write path + the fields actually stored
- `src/repository/crud/correction.py:65-69` — `get_recent(20)` to reuse
- `src/constants/prompts.py:27-66` — `LLMPrompts.occurrence_generation` (add `corrections_context`; mirror `keyword_context` conditional)
- `src/services/occurrence/llm_generate.py:88-93,144-151,159-178` — `LLMOccurrenceGenerationService.__init__`, `_build_prompt`, `generate_for_ddr`
- `src/services/pipeline_service.py:27-58,607-619` — `PreSplitPipelineService.__init__`, `_generate_occurrences`
- `src/api/dependencies/services.py:25-47` — `get_pipeline_service`, `get_ddr_reprocess_service` DI
- `src/services/ddr.py:53-59,123-164` — `_default_pipeline_service_factory`, `DDRReprocessService.regenerate_occurrences`
- `tests/test_occurrence_generation.py` — async/no-pytest-asyncio test style; the 2 `test_pipeline_service_*` tests that must stay green; the 1 known pre-existing failure
- `tests/test_corrections_schema.py` — `get_recent` / repo test style reference

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Created `CorrectionContextBuilder` service in `src/services/correction/` with `MAX_INJECTED_CORRECTIONS=20` class constant, `get_recent` reuse, defensive slice, order-preserving grouping, and exact AC-1 format string.
- Added `corrections_context: str = ""` param to `LLMPrompts.occurrence_generation`; non-empty context prepended as "PREVIOUSLY CORRECTED" block before expert body; empty → prompt byte-identical to baseline.
- Threaded `correction_repository: Any | None = None` through `LLMOccurrenceGenerationService`, `PreSplitPipelineService`, `DDRReprocessService`, `_default_pipeline_service_factory`, `get_pipeline_service`, and `get_ddr_reprocess_service`.
- 7 new tests in `tests/test_correction_context_builder.py` covering cap, grouping+format, empty, fewer-than-20, defensive-slice, prompt-injection, and no-repo regression.
- Full suite: 271 passed, 0 failed (note: the "1 pre-existing failure" referenced in story notes was already resolved on the current branch).

### File List

| File | Action |
|------|--------|
| `ces-backend/src/services/correction/__init__.py` | NEW — package init |
| `ces-backend/src/services/correction/context_builder.py` | NEW — `CorrectionContextBuilder` (cap + group + summarize) |
| `ces-backend/src/constants/prompts.py` | UPDATE — `occurrence_generation` gains `corrections_context` prepend |
| `ces-backend/src/services/occurrence/llm_generate.py` | UPDATE — optional `correction_repository`, build+inject context |
| `ces-backend/src/services/pipeline_service.py` | UPDATE — thread `correction_repository` into `_generate_occurrences` |
| `ces-backend/src/api/dependencies/services.py` | UPDATE — inject `CorrectionCRUDRepository` into pipeline + reprocess services |
| `ces-backend/src/services/ddr.py` | UPDATE — wire `correction_repository` in task factory + `DDRReprocessService` |
| `ces-backend/tests/test_correction_context_builder.py` | NEW — cap/group/format/empty tests + prompt-injection test |

## Change Log

- 2026-05-21: Story created
- 2026-05-21: Implemented CorrectionContextBuilder + prompt injection + full pipeline wiring; 7 tests added; 271/271 pass — correction context builder (last-20, grouped, exact summary format) injected into the occurrence-generation prompt; threaded `correction_repository` through pipeline + reprocess paths; injection point corrected from epic's "extraction" to architecture's occurrence-generation prompt.
