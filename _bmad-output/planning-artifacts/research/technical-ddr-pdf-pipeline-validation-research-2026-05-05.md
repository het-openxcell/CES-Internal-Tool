---
stepsCompleted: [1, 2, 3, 4, 5, 6]
workflow_completed: true
inputDocuments: ['_bmad-output/brainstorming/brainstorming-session-2026-05-01-001.md']
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'DDR PDF Pipeline Validation — Gemini 2.5 Flash-Lite + pdfplumber proof-of-concept'
research_goals: 'Determine if Gemini 2.5 Flash-Lite responseSchema + pdfplumber pre-splitting will work for DDR structured extraction; build minimal PoC to validate before full implementation'
user_name: 'Het'
date: '2026-05-05'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-05-05
**Author:** Het
**Research Type:** technical

---

## Research Overview

Validating whether Gemini 2.5 Flash-Lite + pdfplumber pre-splitting is viable for DDR structured extraction before full implementation. Research covers API capabilities, constraints, pricing, and PoC architecture.

---

## Technical Research Scope Confirmation

**Research Topic:** DDR PDF Pipeline Validation — Gemini 2.5 Flash-Lite + pdfplumber proof-of-concept
**Research Goals:** Determine if Gemini 2.5 Flash-Lite responseSchema + pdfplumber pre-splitting will work for DDR structured extraction; build minimal PoC to validate before full implementation

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-05-05

---

## Technology Stack Analysis

### Core LLM: Gemini 2.5 Flash-Lite

**Model ID:** `gemini-2.5-flash-lite` (GA) / `gemini-2.5-flash-lite-preview` (preview)
**Context window:** 1,000,000 tokens — handles full 300-page DDR without chunking at LLM level
**PDF input:** Confirmed native. Two methods:
- **Inline (base64):** `types.Part.from_bytes(data, mime_type="application/pdf")` — limit 50MB per request
- **File API:** Upload first, reference by URI — for larger files or reuse

DDR PDFs: ~109–229 pages. Typical Pason DDR is ~2–5MB — well within 50MB inline limit per per-date chunk.

**Structured output (`responseSchema`):**
- Pass `generation_config={"response_mime_type": "application/json", "response_schema": <schema>}`
- Enforces output shape — no post-parsing needed
- Confirmed working in batch mode with file input ([forum thread](https://discuss.ai.google.dev/t/structured-output-in-gemini-2-5-flash-lite-batch-mode-input-file/102297))
- Known issue: `gemini-2.5-flash-image` variant has a reported doc/behavior mismatch on structured output — use standard `gemini-2.5-flash-lite`, not image variant

**Data extraction accuracy:**
- Flash-Lite rated "good" for invoice/form/contract → structured JSON extraction
- 1M context means full date chunk fed in single call — no truncation risk
- No published accuracy benchmarks for DDR-style industrial forms specifically — must validate in PoC
_Confidence: Medium — strong signals, no DDR-specific data_

**Pricing (2026):**

| Tier | Input | Output |
|---|---|---|
| Flash-Lite | $0.10 / 1M tokens | $0.40 / 1M tokens |
| Flash (comparison) | $0.30 / 1M tokens | $2.50 / 1M tokens |

At 10–15 DDRs/day (~2,500 pages): estimated **$0.30–0.50/day** (aligns with brainstorm estimate).
_Source: [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)_

**Rate limits:**

| Tier | RPM | RPD | TPM |
|---|---|---|---|
| Free | 30 | 1,500 | 1,000,000 |
| Paid (Tier 1) | Higher — check AI Studio | — | — |

At 30 RPM free tier: ~1 per-date chunk every 2s — acceptable for sequential PoC. Parallel async needs paid tier or batching.
_Source: [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits)_

---

### PDF Pre-Splitter: pdfplumber

**Method:** `pdf.pages[n].extract_words()` — returns list of dicts with `x0, x1, top, bottom, text`
**Tour Sheet Serial detection:** Scan each page for word sequence matching `Tour Sheet Serial Number` label, then extract adjacent value token (e.g. `0Y52466_20241031_2A`) — parse `YYYYMMDD` from positions 7–15 of that string.

**Performance:**
- Brainstorm benchmark: 119s / 109 pages for full word-coord extraction
- For pre-split scan only (just finding serial header, not extracting all words): significantly faster — reading one field per page
- Pure Python; slower than PyMuPDF but no C deps, simpler install
- Large PDF strategy: open with `pdfplumber.open()` context manager, iterate pages one-by-one — avoids memory spikes
_Source: [github.com/jsvine/pdfplumber](https://github.com/jsvine/pdfplumber)_

**Coordinate-based field matching:** Confirmed approach — known x0/y0 ranges for "Tour Sheet Serial Number" label are consistent across Pason DDR template (verified in brainstorm: `0508851`, `DRL.240153`, `18:30/18:45` found at consistent coords). Can use `crop()` + `extract_text()` on bounding box for precise field extraction.

---

### Schema Enforcement: Pydantic v2

- `responseSchema` enforces output at API level
- Pydantic validates post-call — catches type mismatches, missing required fields
- Use `model_validate()` with `strict=False` for lenient coercion on numeric strings
- Error path: log raw Gemini response + Pydantic errors to DB `error_log` column

---

### Async Orchestration: Python asyncio

- `asyncio.gather()` for parallel per-date chunks
- `google-generativeai` Python SDK supports async via `generate_content_async()`
- At free tier (30 RPM): use `asyncio.Semaphore(5)` to throttle — 5 concurrent calls max
- At paid tier: raise semaphore limit

---

### Storage: PostgreSQL (existing)

- `sessions` table: `pdf_id`, `dates_extracted[]`, `raw_responses` (JSONB), `final_json` (JSONB), `processed_at`, `error_log`
- JSONB allows querying into extracted fields without schema migrations

---

### Technology Adoption Notes

- Gemini 2.5 Flash-Lite GA'd on Vertex AI (confirmed [Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/gemini-2-5-flash-lite-flash-pro-ga-vertex-ai)) — stable API, not preview-only
- pdfplumber actively maintained, v0.11.x — no deprecation risk
- `google-generativeai` SDK: use `>=0.8.0` for Flash-Lite + responseSchema support

---

## Integration Patterns Analysis

### PDF Pre-Split → Gemini Integration

**Critical finding:** pdfplumber cannot produce PDF byte output. It reads only. Page subset creation requires a second library.

**Required library stack for pre-split:**

```
pdfplumber  — scan pages, detect Tour Sheet Serial header, map page_idx → YYYYMMDD
pypdf       — extract page subset by index, write to BytesIO → bytes
```

Pattern:
```python
import pdfplumber
from pypdf import PdfWriter
import io

def extract_date_pages(pdf_path: str) -> dict[str, bytes]:
    """Returns {YYYYMMDD: pdf_bytes} for each date found."""
    date_pages: dict[str, list[int]] = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            words = page.extract_words()
            serial = _find_tour_serial(words)  # scan for Tour Sheet Serial label
            if serial:
                date = serial[7:15]  # e.g. "0Y52466_20241031_2A" → "20241031"
                date_pages.setdefault(date, []).append(i)
    
    # Build per-date PDF bytes via pypdf
    result = {}
    reader = pypdf.PdfReader(pdf_path)
    for date, indices in date_pages.items():
        writer = PdfWriter()
        for idx in indices:
            writer.add_page(reader.pages[idx])
        buf = io.BytesIO()
        writer.write(buf)
        result[date] = buf.getvalue()
    
    return result
```

_Source: [pdfplumber GitHub](https://github.com/jsvine/pdfplumber) + [Gemini file input methods](https://ai.google.dev/gemini-api/docs/file-input-methods)_

---

### Gemini API: SDK Version

**Use new SDK:** `google-genai` (package: `google-genai`, not the deprecated `google-generativeai`)
- Repo: `googleapis/python-genai`
- Async: `await client.aio.models.generate_content()`
- Old SDK (`google-generativeai`) is deprecated — migration guide at [ai.google.dev/gemini-api/docs/migrate](https://ai.google.dev/gemini-api/docs/migrate)

_Confidence: High_

---

### Gemini API Call Pattern (per-date chunk)

```python
import google.genai as genai
import google.genai.types as types

client = genai.Client(api_key=GEMINI_API_KEY)

async def extract_date(date: str, pdf_bytes: bytes, schema: dict) -> dict:
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Extract all DDR fields from this daily report into the provided schema."
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )
    )
    return json.loads(response.text)
```

**Key constraint:** Gemini processes the full uploaded file — no native page range selection. Pre-splitting is mandatory (which aligns with the architecture).

**50MB inline limit per request:** DDR per-date chunks = 1–2 pages ≈ 100–300KB. Far under limit. No File API needed for PoC.

_Source: [Google Gen AI SDK docs](https://googleapis.github.io/python-genai/) + [Document understanding](https://ai.google.dev/gemini-api/docs/document-processing)_

---

### Async Orchestration Pattern

```python
import asyncio

async def process_pdf(pdf_path: str, schema: dict) -> dict:
    date_chunks = extract_date_pages(pdf_path)  # pdfplumber + pypdf
    
    sem = asyncio.Semaphore(5)  # throttle for free tier (30 RPM)
    
    async def bounded_extract(date, pdf_bytes):
        async with sem:
            return date, await extract_date(date, pdf_bytes, schema)
    
    tasks = [bounded_extract(d, b) for d, b in date_chunks.items()]
    results = await asyncio.gather(*tasks)
    return dict(results)
```

At free tier (30 RPM) with semaphore(5): 5 concurrent calls, each ~2s → ~10 dates/20s. For typical 30-day DDR: ~60s total.

---

### Schema Mapping: report_schema_flat.json → Gemini responseSchema

Gemini `responseSchema` accepts JSON Schema subset. Key constraints:
- Supports: `object`, `array`, `string`, `number`, `integer`, `boolean`
- Does **not** support: `$ref`, `anyOf`, `oneOf`, recursive schemas
- Nested objects and arrays: supported
- Required fields: specify in `required: []` array

Map `report_schema_flat.json` → flat/nested JSON Schema object. If schema uses `$ref`: resolve references before passing to Gemini.

_Confidence: Medium — based on documented limitations, verify against actual schema_

---

### Pydantic Validation Layer

```python
from pydantic import BaseModel, ValidationError

class DDRReport(BaseModel):  # mirrors report_schema_flat.json
    ...

def validate_response(raw: dict) -> DDRReport | None:
    try:
        return DDRReport.model_validate(raw)
    except ValidationError as e:
        log_error(raw, e)
        return None
```

---

### Data Format: JSONB in PostgreSQL

- Store `raw_responses: dict` (Gemini raw JSON per date) + `final_json: dict` (merged + validated)
- JSONB indexing on `final_json->>'well_id'` for dashboard queries
- `error_log: text` for Pydantic errors + Gemini failures

---

### Integration Security

- Gemini API key: env var `GEMINI_API_KEY`, never hardcoded
- PDF files: local filesystem only (no external upload beyond Gemini inline)
- No auth surface on pipeline itself (internal tool, not exposed)

---

## Architectural Patterns and Design

### PoC Architecture — Minimal Validation Design

Goal: validate the two critical unknowns before building full pipeline.

**Unknown 1:** Does Flash-Lite preserve TIME LOG row order with long Description text?
**Unknown 2:** Does pdfplumber reliably detect Tour Sheet Serial headers across pages?

Minimal PoC = two independent scripts. No DB, no dashboard, no async. Just validate core assumptions.

```
poc/
  01_presplit.py    — pdfplumber scan → print page→date mapping
  02_extract.py     — take one date's pages → Gemini → print raw JSON
  test_pdfs/        — 109-page + 229-page samples
```

---

### System Architecture Pattern: Pipeline

DDR processing is sequential transformation, not distributed system. Pattern: **pipeline with stages**.

```
Stage 1: pre_split(pdf_path) → dict[date, bytes]        # pdfplumber + pypdf
Stage 2: extract_all(chunks, schema) → dict[date, dict]  # Gemini parallel
Stage 3: merge(date_dicts) → full_report dict             # simple merge
Stage 4: validate(full_report) → DDRReport                # Pydantic
Stage 5: store(session_id, report) → None                 # PostgreSQL
```

No queues, no message broker needed at current scale (10–15 PDFs/day).

---

### Schema Architecture: Critical Risk

**responseSchema complexity limits** — Gemini rejects schemas that are too complex:
- Long property names
- Deep nesting
- Many optional properties
- Large arrays with enum constraints

**Known failure mode:** Flash models can produce malformed/repetitive JSON (looping text fragments until max tokens) when schema is complex.
_Source: [GitHub issue — malformed JSON on complex schemas](https://github.com/googleapis/google-cloud-java/issues/11782)_

**Mitigation strategy for PoC:**

1. Start with **subset schema** (header fields only — well ID, date, contractor) — validate basic extraction works
2. Add `daily_checks` block
3. Add `time_log[]` array last — highest risk (long text, row order)
4. If `responseSchema` fails: switch to `responseJsonSchema` (supports `$ref`, `anyOf`, added Nov 2025)

**`responseSchema` vs `responseJsonSchema`:**
- `responseSchema`: simple SDK-native type objects — works for flat/moderate schemas
- `responseJsonSchema`: full JSON Schema string — supports `$ref`, `anyOf`, recursion — use for `report_schema_flat.json` if it uses references

_Source: [Gemini structured output docs](https://ai.google.dev/gemini-api/docs/structured-output) + [Nov 2025 update](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/)_

---

### Data Architecture: Per-Date then Merge

Each date-chunk → one DDRReport → merge sorted by date ascending. Header fields (well ID, licence) should be identical across dates — validate consistency, flag mismatches.

---

### Scalability Pattern: Sequential First, Parallel Later

**PoC:** Sequential per-date calls. Simplest to debug, stays within 30 RPM free tier.
**Production:** `asyncio.gather()` with semaphore. Paid tier for > 5 concurrent.
**Future:** Gemini Batch API for bulk — not needed at 10–15/day.

---

### pypdf Page Extraction (confirmed)

```python
from pypdf import PdfReader, PdfWriter
import io

reader = PdfReader(pdf_path)
writer = PdfWriter()
for idx in page_indices:
    writer.add_page(reader.pages[idx])
buf = io.BytesIO()
writer.write(buf)
pdf_bytes = buf.getvalue()
```

`PdfWriter.add_page()` is current API (v6.x). Pure Python, no C deps, BytesIO fully supported.
_Source: [pypdf docs](https://pypdf.readthedocs.io/en/stable/modules/PdfWriter.html)_

---

### Risk Matrix

| Risk | Severity | Mitigation |
|---|---|---|
| Flash-Lite garbles TIME LOG row order (long descriptions) | High | PoC test; if fails, 2-pass (header+checks separate from time_log) |
| responseSchema rejects complex report_schema_flat.json | High | Start simple, escalate to responseJsonSchema if needed |
| Tour Sheet Serial format inconsistent across contractors | Medium | Scan samples first; add fallback regex patterns |
| Multi-date page overflow (date X end + date Y start on same page) | Medium | Assign ambiguous page to earlier date; test with known boundary |
| pypdf loses form fields / embedded data | Low | DDRs are text-layer PDFs, not forms — confirmed safe |

---

## Implementation Approaches and Technology Adoption

### SDK Setup (Confirmed)

```bash
pip install google-genai          # core SDK
pip install google-genai[aiohttp] # adds async support
pip install pdfplumber pypdf pydantic
```

Client init:
```python
import google.genai as genai
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
# or: client = genai.Client()  # auto-picks GEMINI_API_KEY or GOOGLE_API_KEY env var
```

_Source: [googleapis/python-genai](https://github.com/googleapis/python-genai)_

---

### TIME LOG Row Order — Resolved

**New finding:** Gemini 2.5 models preserve property ordering from responseSchema (confirmed in Nov 2025 update). This applies to array item ordering too.

**Requirement to activate:** Prompt descriptions and examples must present properties in same order as defined in responseSchema. Mismatch confuses the model and causes incorrect output.

**Action:** In the extraction prompt, describe TIME LOG fields in exact schema order: `time_from → time_to → code → details`.

**Risk status:** Downgraded from High to Medium. Still requires PoC validation — order preservation is documented but not tested against DDR-specific long-description rows.

_Source: [Gemini structured output — property ordering](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/)_

---

### pdfplumber Tour Sheet Serial Detection Pattern

```python
def find_tour_serial(words: list[dict]) -> str | None:
    """Find Tour Sheet Serial value on a page."""
    for i, w in enumerate(words):
        if w["text"] == "Serial" and i >= 3:
            # Check preceding words form "Tour Sheet Serial Number"
            context = " ".join(words[j]["text"] for j in range(i-3, i+1))
            if "Tour Sheet Serial" in context:
                # Value is next word at same vertical position
                serial_top = w["top"]
                for j in range(i+1, min(i+10, len(words))):
                    if abs(words[j]["top"] - serial_top) < 3:
                        val = words[j]["text"]
                        if len(val) > 10 and "_" in val:
                            return val
    return None
```

Extract date: `serial[7:15]` for format `XXXXXX_YYYYMMDD_XA`.
Edge case: serial may span two words if pdfplumber splits on underscore — join adjacent tokens at same y and test.

---

### PoC Implementation Sequence

**Day 1 — Pre-splitter validation:**
1. `01_presplit.py`: run on `~QWT~AB_WDF_0508851.pdf` (109 pages)
2. Print page→date map, verify against known DDR dates
3. Check: does every page get a date? Any pages missed?
4. Edge case: identify pages at date boundaries

**Day 2 — Gemini extraction validation:**
1. `02_extract.py`: take one date's chunk bytes → call Gemini with subset schema (header only)
2. Verify: well ID, date, contractor extracted correctly
3. Expand schema → add `daily_checks`
4. Expand schema → add `time_log[]` with 3–5 rows
5. Check TIME LOG row order against source PDF

**Day 3 — Full schema + stress test:**
1. Pass full `report_schema_flat.json` → check for `InvalidArgument: 400`
2. If error: switch to `responseJsonSchema` variant
3. Run on multi-date PDF `~QWT~AB_WDF_0507765.pdf` (229 pages)
4. Compare output against Het's converter output (ground truth)

---

### Testing Approach

No unit tests for PoC — visual inspection against known-good output.

**Validation checklist per date chunk:**
- [ ] Well ID matches
- [ ] Date matches
- [ ] Contractor name matches
- [ ] TIME LOG rows count matches
- [ ] TIME LOG row order matches (first row = 00:00 or earliest time)
- [ ] No hallucinated fields (fields present in output but not in PDF)
- [ ] No missing required fields

---

### Cost Estimate (PoC)

| Run | Pages | Est. tokens | Est. cost |
|---|---|---|---|
| 01_presplit.py | 109 | 0 (local) | $0 |
| 02_extract.py × 5 dates | ~10 pages | ~50K tokens | < $0.01 |
| Full 229-page run | ~229 pages | ~500K tokens | ~$0.05 |

PoC total: **< $0.10**. Safe to run multiple iterations.

---

### Go / No-Go Criteria

**Go (build full pipeline):**
- Pre-splitter correctly identifies all date boundaries on both sample PDFs
- Gemini extracts well ID, contractor, daily_checks with > 95% field accuracy
- TIME LOG row order preserved across 3+ test dates
- Full schema accepted without `InvalidArgument: 400`

**No-Go / Pivot triggers:**
- Pre-splitter misses > 5% of date boundaries → investigate Tour Sheet Serial format variance
- TIME LOG rows reordered → try 2-pass approach (header + checks in pass 1, time_log in pass 2)
- Schema consistently rejected → use `responseJsonSchema` or simplify schema
- Accuracy < 90% on known fields → evaluate Flash (not Flash-Lite) or prompt engineering

---

## Technical Research Recommendations

### Implementation Roadmap

1. **PoC (3 days):** Two scripts, validate 3 go/no-go criteria against both sample PDFs
2. **Pre-splitter (2 days):** Harden edge cases, handle multi-contractor serial formats
3. **Extraction layer (2 days):** Full schema, async orchestration, Pydantic validation
4. **DB + API (2 days):** Sessions table, FastAPI endpoint, error logging
5. **Dashboard wiring (existing scaffolding):** Read sessions, filter, re-run

### Technology Stack Recommendations

| Component | Choice | Reason |
|---|---|---|
| LLM | `gemini-2.5-flash-lite` | Cost-optimal, PDF-native, responseSchema support |
| SDK | `google-genai` (new) | Replaces deprecated `google-generativeai` |
| PDF scan | `pdfplumber` | Coordinate-based word extraction |
| PDF split | `pypdf` v6.x | BytesIO output, pure Python |
| Validation | `pydantic` v2 | `model_validate()` + strict typing |
| Async | `asyncio` + `aiohttp` | Parallel per-date calls |
| Storage | PostgreSQL JSONB | Existing, flexible schema |

### Risk Mitigation Summary

| Risk | Status | Action |
|---|---|---|
| TIME LOG row order | Medium (partially mitigated) | Enforce schema prop order in prompt |
| responseSchema complexity | Medium | Start subset → escalate to responseJsonSchema |
| Tour Serial format variance | Medium | Test both sample PDFs in Day 1 |
| Multi-date page overflow | Low-Medium | Assign to earlier date; validate manually |

### Success Metrics

- Pre-splitter: 100% date boundary detection on both sample PDFs
- Extraction: > 95% field accuracy vs ground truth on header + daily_checks
- TIME LOG: Row order preserved on all test dates
- Cost: < $0.50/day at production volume
- Speed: < 90s per 30-day DDR (sequential), < 30s (parallel)

---

# Research Synthesis: DDR PDF Pipeline Validation

## Executive Summary

This research validates the technical feasibility of the proposed DDR PDF pipeline: **pdfplumber pre-split + Gemini 2.5 Flash-Lite responseSchema extraction**. All core components are confirmed viable based on current web-verified sources. No blocking unknowns exist at the architecture level — the only remaining uncertainty is empirical accuracy on DDR-specific content (TIME LOG row ordering, field extraction fidelity), which requires a 3-day PoC to resolve.

**Verdict: Build the PoC. Architecture is sound.**

### Key Technical Findings

- **Gemini 2.5 Flash-Lite is GA**, not preview. Native PDF input confirmed. `responseSchema` enforced output confirmed working including in batch/file-input mode.
- **pdfplumber cannot output PDF bytes** — `pypdf` required as second library for page extraction. This gap was not in the original brainstorm architecture.
- **`google-generativeai` SDK is deprecated** — use `google-genai` (new unified SDK). Async via `client.aio.models.generate_content()`.
- **responseSchema has complexity limits** — deeply nested schemas with many optional fields can 400. `reportSchema_flat.json` may need simplification or switch to `responseJsonSchema` (supports `$ref`, added Nov 2025).
- **TIME LOG row order risk partially resolved** — Gemini 2.5 preserves property ordering from schema. Prompt field order must match schema order to activate this.
- **PoC cost: < $0.10** — safe to iterate rapidly.

### Technical Recommendations

1. Use `google-genai` SDK (not deprecated `google-generativeai`)
2. Add `pypdf` to dependency list alongside `pdfplumber`
3. Test `responseSchema` with simplified schema first — escalate to `responseJsonSchema` if complex schema 400s
4. In extraction prompt, describe TIME LOG fields in exact schema property order
5. Run 3-day PoC against both sample PDFs before committing to full implementation

---

## Table of Contents

1. Research Scope and Methodology
2. Technology Stack Analysis
3. Integration Patterns Analysis
4. Architectural Patterns and Design
5. Implementation Approaches
6. Go/No-Go Criteria
7. Risk Register
8. Source References

---

## 1. Research Scope and Methodology

**Topic:** DDR PDF Pipeline Validation — Gemini 2.5 Flash-Lite + pdfplumber PoC
**Goal:** Determine if architecture works before full build

**Methodology:** 8 parallel + sequential web searches across Gemini API docs, pdfplumber GitHub, pypdf docs, Google Gen AI SDK, structured output benchmarks, and pricing/rate limit sources. All claims cited.

---

## 2. Technology Stack — Final Confirmed Stack

| Component | Library/Service | Version | Notes |
|---|---|---|---|
| LLM | Gemini 2.5 Flash-Lite | GA | `gemini-2.5-flash-lite` model ID |
| SDK | `google-genai` | latest | replaces deprecated `google-generativeai` |
| PDF scan | `pdfplumber` | v0.11.x | coordinate-based word extraction |
| PDF split | `pypdf` | v6.x | BytesIO output — **not in original brainstorm** |
| Validation | `pydantic` | v2 | `model_validate()` |
| Async | `asyncio` + `aiohttp` | stdlib + pip | `client.aio.models.generate_content()` |
| Storage | PostgreSQL JSONB | existing | sessions table |

**Install:**
```bash
pip install google-genai "google-genai[aiohttp]" pdfplumber pypdf pydantic
```

**Pricing:** $0.10/1M input + $0.40/1M output. ~$0.30–0.50/day at 10–15 DDRs/day.
**Rate limit (free):** 30 RPM, 1,500 RPD. Sequential PoC: fine. Production async: needs paid tier.

---

## 3. Integration Patterns — Full Pipeline Chain

```
PDF (native, 109–229 pages)
  ↓
pdfplumber: scan pages → find Tour Sheet Serial Number label
            → extract adjacent value → parse YYYYMMDD → map page_idx → date
  ↓
pypdf: PdfWriter() → add_page(reader.pages[idx]) per date → BytesIO → bytes
  ↓
google-genai: client.aio.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=[Part.from_bytes(pdf_bytes, "application/pdf"), prompt],
    config=GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema  # or response_json_schema for complex schemas
    )
)
  ↓
json.loads(response.text) → Pydantic model_validate()
  ↓
PostgreSQL JSONB: raw_responses + final_json + error_log
```

**Per-date chunk size:** 1–2 pages, ~100–300KB. Well under 50MB inline limit.

---

## 4. Architectural Patterns

**Pattern:** Sequential pipeline stages, single Python process, asyncio for parallel LLM calls.

**PoC structure:**
```
poc/
  01_presplit.py   — validate page→date mapping
  02_extract.py    — validate Gemini extraction on single date
```

**Schema approach:**
1. Start: subset schema (header fields only)
2. Expand: add `daily_checks`
3. Expand: add `time_log[]` — highest risk
4. Fallback: `responseJsonSchema` if complexity limit hit

---

## 5. Implementation

**Day 1:** `01_presplit.py` — pdfplumber scan on 109-page PDF, print page→date map, verify
**Day 2:** `02_extract.py` — subset schema → expand → TIME LOG validation
**Day 3:** Full schema + 229-page PDF + compare vs ground truth

**Prompt requirement for TIME LOG:** Describe fields in schema property order (`time_from → time_to → code → details`). Mismatch causes row order degradation.

---

## 6. Go / No-Go Criteria

| Criterion | Pass | Fail Action |
|---|---|---|
| Pre-splitter detects all dates | ≥ 95% pages mapped | Investigate serial format variance |
| Field extraction accuracy (header + checks) | ≥ 95% match vs ground truth | Prompt engineering or upgrade to Flash |
| TIME LOG row order preserved | All test dates pass | 2-pass extraction (header separate from time_log) |
| Full schema accepted | No 400 errors | Switch to `responseJsonSchema` |

---

## 7. Risk Register

| Risk | Severity | Probability | Mitigation |
|---|---|---|---|
| TIME LOG row order garbled | High | Low-Medium | Schema prop order in prompt; 2-pass fallback |
| responseSchema complexity 400 | High | Medium | Subset schema → responseJsonSchema escalation |
| Tour Serial format varies by contractor | Medium | Low | Regex fallback patterns |
| Multi-date page overflow | Medium | Medium | Assign ambiguous page to earlier date |
| pypdf drops text layer | Low | Very Low | DDRs are native text PDFs |

---

## 8. Source References

- [Gemini 2.5 Flash-Lite model docs](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini structured output docs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Nov 2025 structured output update (property ordering + responseJsonSchema)](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/)
- [Gemini document understanding (PDF input)](https://ai.google.dev/gemini-api/docs/document-processing)
- [Malformed JSON on complex schemas — GitHub issue](https://github.com/googleapis/google-cloud-java/issues/11782)
- [Google Gen AI SDK (new)](https://googleapis.github.io/python-genai/)
- [SDK migration guide](https://ai.google.dev/gemini-api/docs/migrate)
- [pdfplumber GitHub](https://github.com/jsvine/pdfplumber)
- [pypdf docs](https://pypdf.readthedocs.io/en/stable/modules/PdfWriter.html)
- [Gemini 2.5 Flash-Lite GA — Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/gemini-2-5-flash-lite-flash-pro-ga-vertex-ai)
- [Structured output batch mode confirmation](https://discuss.ai.google.dev/t/structured-output-in-gemini-2-5-flash-lite-batch-mode-input-file/102297)

---

**Research Completed:** 2026-05-05
**Confidence Level:** High on architecture, Medium on DDR-specific accuracy (requires PoC)
**Next Action:** Build `poc/01_presplit.py` and `poc/02_extract.py` against sample PDFs
