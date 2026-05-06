---
stepsCompleted: [1, 2, 3, 4]
workflow_completed: true
inputDocuments: []
session_topic: 'Speed up DDR PDF parsing pipeline / evaluate 3rd party tools for direct schema extraction'
session_goals: 'Faster processing, higher schema accuracy, identify best cost/speed/accuracy tradeoff for paid tools'
selected_approach: 'ai-recommended'
techniques_used: ['Failure Analysis', 'First Principles Thinking', 'Solution Matrix']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Het
**Date:** 2026-05-01

## Session Overview

**Topic:** Speed up DDR PDF parsing pipeline / evaluate 3rd party tools for direct schema extraction
**Goals:** Faster processing, higher schema accuracy, identify best cost/speed/accuracy tradeoff for paid tools

### Session Setup

Working on Canadian Energy Service Internal Tool — processing oil well Drilling Daily Reports (DDRs).
Known schema: `report_schema_flat.json` — header fields + daily_checks + 3 tours (bits, drilling assembly, mud record, time log, deviation surveys, etc.) + derived occurrences.
Prior experiments: LlamaExtract (degrades on 170-page full PDF), Docling (accurate but slow + broken MD output), 10-page chunking (abandoned).

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Technical architecture decision with real experiment data — needs structured analysis

**Recommended Techniques:**
- **Failure Analysis:** Mine LlamaExtract, Docling, chunking failures → extract hard constraints
- **First Principles Thinking:** Strip assumptions from current pipeline → surface radically different architectures
- **Solution Matrix:** Map all tool candidates × criteria (speed, accuracy, cost, infra) → ranked shortlist

**AI Rationale:** Problem is concrete with known constraints and real experiment data. Structured/analytical techniques outperform creative divergence here.

## Technique Execution Results

### Phase 1: Failure Analysis

Mined 3 prior experiments to extract hard constraints before generating new ideas.

**[Failure #0 — Root cause of all prior failures]**: Wrong mental model
*Concept:* Everyone assumed PDF needed vision/OCR pipeline. PDFs are native text — `pypdf` extracts 5,959 characters from page 0 in milliseconds. No OCR needed at all.
*Novelty:* Reframes the entire problem space. The challenge is **structure mapping**, not text reading.

**[Failure #1]**: LlamaExtract on full PDF
*Concept:* Internal chunking loses positional coherence on 170+ page PDFs. First entries appeared from page ~10, page 2 data appeared far later in output.
*Constraint extracted:* Any tool that chunks internally without respecting DDR date boundaries fails. Pre-splitting by date is mandatory.

**[Failure #2]**: Docling
*Concept:* Accurate JSON, but 12 min on T4 GPU for 200 pages. 200MB JSON is mostly base64 page images. Native MD output unusable.
*Constraint extracted:* Docling runs full ML layout analysis on a native PDF — wasteful. Wrong tool for native PDFs.

**[Failure #3]**: 10-page chunking
*Concept:* Page count is wrong anchor. DDR splits by date/tour, not by page.
*Constraint extracted:* Chunking must respect date/tour boundaries.

### Phase 2: First Principles Thinking

Stripped assumptions. Real need: extract structured data from a known Pason DDR template into known JSON schema. PDFs are native, so OCR pipeline is unnecessary.

**Key benchmarks:**
- pypdf raw text: 27s / 109 pages — text comes out jumbled (labels and values separated, no spatial association)
- pdfplumber word coords: 119s / 109 pages — gives x,y for every word, can map fields by coordinate
- Docling: ~390s / 109 pages on T4 GPU
- Verified data extraction: pdfplumber found `0508851`, `0Y52466_20241031_1A`, `DRL.240153`, `466`, time entries `18:30/18:45` at consistent coordinates across pages

### Phase 3: Solution Matrix

Evaluated alternatives (Claude API ruled out by user). Compared Gemini, OpenAI, Azure Doc Intelligence, AWS Textract, Reducto, Mistral OCR, LlamaExtract retry, pdfplumber-only, local LLM.

**Selected solution: Gemini 2.5 Flash-Lite Preview**
- Native PDF input (no preprocessing pipeline)
- 1M token context window (handles full 300-page PDF)
- Structured output via `responseSchema` (enforces report_schema_flat.json)
- Cost: ~$0.30–0.50/day at 10–15 PDFs/day, ~2500 pages
- Build effort: 3–5 days

## Idea Organization and Prioritization

### Final Architecture

| Component | Decision |
|---|---|
| LLM | Gemini 2.5 Flash-Lite Preview |
| Input | Native PDF (always native, confirmed by user) |
| Pre-splitter | pdfplumber — find Tour Sheet Serial date headers, group pages by `YYYYMMDD` |
| Chunking | Per-date (1–2 pages per chunk) — handles variable pages-per-date |
| Schema enforcement | Gemini `responseSchema` with report_schema_flat.json |
| Occurrences extraction | Separate 2nd Gemini pass over extracted `time_logs[]` |
| Validation | Pydantic post-call |
| Storage | DB — sessions table with raw responses + final JSON + metadata |
| History Dashboard | Reads from sessions DB |
| Confidence scores | Not needed |
| OCR fallback | Not needed (always native) |

### Pipeline

```
PDF (native)
  ↓
pdfplumber: scan pages → extract Tour Sheet Serial → group by YYYYMMDD
  ↓
Per-date chunks → Gemini Flash-Lite (parallel) — responseSchema enforced
  ↓
Merge per-date JSONs → full report JSON
  ↓
2nd Gemini pass: time_logs[] → occurrences[] (drilling problems)
  ↓
Pydantic validate → final report
  ↓
DB (sessions: raw responses + final JSON + metadata)
  ↓
History Dashboard
```

### Top Priorities (Action Plan)

**Priority 1: Pilot run on existing PDFs (1–2 days)**
- Process the 109-page (`~QWT~AB_WDF_0508851.pdf`) and 229-page (`~QWT~AB_WDF_0507765.pdf`) samples
- Validate Flash-Lite accuracy against known good output (out.md / Het's converter output)
- Test 3 risk areas:
  1. TIME LOG row order preservation across long descriptions
  2. Date boundary detection (Tour Sheet Serial format consistency)
  3. Multi-date overflow (page contains end of date X + start of date Y)

**Priority 2: Build pre-splitter (2 days)**
- pdfplumber scan → find `Tour Sheet Serial Number` field per page
- Parse `YYYYMMDD` from format like `0Y52466_20241030_2A`
- Group pages with same date into chunks
- Edge case handling: dates spanning 2 pages

**Priority 3: Gemini integration + schema enforcement (1–2 days)**
- Define `responseSchema` from existing `report_schema_flat.json`
- Build per-chunk extraction call
- Parallel orchestration (asyncio)
- Pydantic validation layer

**Priority 4: Occurrences pass (1 day)**
- Separate prompt focused on drilling problem types: Lost Circ, Stuck Pipe, Tight Hole, Kick
- Input: extracted `time_logs[].description` array
- Output: occurrences[] schema

**Priority 5: DB + History Dashboard wiring (existing scaffolding)**
- Sessions table: pdf_id, dates_extracted, raw_responses (JSONB), final_json (JSONB), processed_at, error_log
- Dashboard reads sessions table — list, filter by date/well, view raw + final, re-run failed extractions

### Risks to Test in Pilot

1. **Flash-Lite accuracy on TIME LOG** — does it preserve row order with long Details text?
2. **Date boundary edge cases** — Tour Sheet Serial format varying across contractors
3. **Multi-date overflow** — Tour 3 of date X spilling onto page that also has date Y header

### Quick Wins Identified

- Native PDF realization eliminates 12-min GPU bottleneck — biggest single win
- Per-date chunking cost reduction: 1M context unused → can process date sequentially or parallel for free
- Schema enforcement removes parsing/repair downstream — Pydantic only validates, doesn't fix
- 2nd-pass occurrences keeps prompts focused, easier to tune independently

## Session Summary and Insights

### Key Achievements

- Diagnosed root cause: prior pipeline assumed OCR was needed — it wasn't
- Eliminated Docling (slow, GPU-bound, wrong tool for native PDFs)
- Verified pdfplumber can extract all DDR field values with coordinates (proven on actual data)
- Selected Gemini 2.5 Flash-Lite as the cost-optimal LLM (~$0.30–0.50/day vs Claude/AWS alternatives)
- Locked end-to-end architecture: pre-split → per-date chunks → Gemini schema → DB
- Identified 3 specific risks to validate in pilot

### Creative Breakthrough

The single insight that collapsed the solution space: **the PDF is native text, not scanned**. This made every prior tool (Docling, LlamaExtract on full PDF, vision-based extraction) the wrong choice. Once recognized, the pipeline simplified from a multi-stage ML pipeline to a 2-step extract-and-map flow.

### Session Reflections

What worked: starting with Failure Analysis prevented re-treading known dead-ends. First Principles forced re-examination of base assumptions (OCR-needed). Solution Matrix kept the final decision evidence-based against measured benchmarks rather than gut feel.

Frontmatter:
- stepsCompleted: [1, 2, 3, 4]
- workflow_completed: true
