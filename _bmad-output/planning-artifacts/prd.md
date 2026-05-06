---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
releaseMode: single-release
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-Canadian Energy Service Internal Tool.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-05-01-001.md'
  - '_bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md'
workflowType: 'prd'
briefCount: 1
researchCount: 1
brainstormingCount: 1
projectDocsCount: 0
classification:
  projectType: 'web_app'
  domain: 'energy'
  complexity: 'high'
  projectContext: 'greenfield'
  notes: 'Dual backend track — Go and Python both built to feature parity; final backend selection deferred until post-PoC validation. Single user role — no RBAC.'
---

# Product Requirements Document - Canadian Energy Service Internal Tool

**Author:** Het
**Date:** 2026-05-05

## Executive Summary

Canadian Energy Services (CES) accumulates 10–15 Drilling Daily Report (DDR) PDFs per day from active field jobs — thousands per year. Each report is a 100–300 page Pason-generated PDF containing structured drilling data: hourly time logs, bit specs, mud weights, formation depths, and flagged problem events. Today, every insight locked in these PDFs requires manual extraction. Patterns spanning multiple jobs go undetected. Analysis is sample-based, not comprehensive. Client deliverables require hours of manual extraction per report.

The CES DDR Intelligence Platform eliminates this. It ingests DDR PDFs, extracts all structured field data through a validated AI pipeline, and delivers a queryable history of every well CES has worked. Management tracks drilling problems (stuck pipe, lost circulation, tight hole, kicks) across clients and time periods, benchmarks performance across jobs, and identifies patterns — in minutes, not days.

The platform is internal-only (V1). All users have identical full access — upload, query, edit, export, and pipeline management. No client-facing surface, no external data purchase — CES already holds the full archive.

### What Makes This Special

No commercial product solves DDR extraction for oilfield service companies. Pason's DataHub API is available to operators, not service companies. WellView, VERDAZO, Spotfire, and OpenWells assume data is already structured — none provide an extraction layer. SLB built an internal pipeline; it is not sold.

The core insight that collapsed the solution space: **DDR PDFs are native text, not scanned images.** Every prior extraction approach (Docling, LlamaExtract) treated these as OCR problems and paid the cost — 12+ minutes on a GPU, multi-stage ML pipelines. pdfplumber reads text coordinates directly. Gemini 2.5 Flash-Lite maps fields to schema. The result: a full 30-day DDR processed in under 90 seconds at ~$0.02/report.

The backend is built on a dual-track strategy — Go and Python implementations maintained in parallel to feature parity. Final backend selection is deferred until post-validation. This preserves optionality on performance vs. ecosystem tradeoffs without blocking early development.

## Project Classification

| Dimension | Value |
|---|---|
| Project Type | Web application (React frontend + backend pipeline + PostgreSQL) |
| Domain | Energy — oil & gas / oilfield services |
| Complexity | High (domain-specific PDF format, AI extraction pipeline, operational data) |
| Project Context | Greenfield |
| Backend Strategy | Dual-track: Go + Python (feature parity; selection deferred) |
| Access Model | Single role — all authenticated users have full access |

## Success Criteria

### User Success

- Upload DDR PDF → occurrence table generated without manual intervention
- Every occurrence row populated correctly: Well Name, Surface Location, Type, Section, mMD, Density, Notes
- User can edit any occurrence cell inline before export; edit triggers reason prompt + metadata capture
- Corrected occurrences exported to Excel with edit history preserved in a separate sheet
- NL query returns relevant time log / occurrence data in < 3s
- Client NPT summaries exportable as `.xlsx` in < 1 minute per report
- Any user can access structured time log and bit data for offset well analysis without archive dives
- No silent extraction failures — every failed date flagged visibly, raw response logged
- **Over time, occurrence classification improves** — same mistake not repeated after correction fed back as context

### Business Success

- All users adopt platform as **primary DDR tracking tool within 30 days of launch** — PDF-open rate for drilling problem review = 0
- Full historical DDR archive processed and queryable at go-live (not just new jobs)
- Client deliverable turnaround reduced by ≥ 80% (hours → minutes per report)
- Backend selection decision made before V1 launch — one codebase maintained, not two
- **Correction loop reduces manual edits over time** — measurable drop in edit rate per DDR after 30 corrections ingested

### Technical Success

| Metric | Target |
|---|---|
| Extraction field accuracy | ≥ 95% vs. Het's converter ground truth |
| Occurrence classification accuracy | ≥ 90% correct type from ~250-keyword rule engine |
| mMD inference accuracy | ≥ 85% within ±10m of true event depth (incl. backward scan) |
| Density lookup accuracy | Nearest-timestamp mud record correctly selected |
| Processing speed (30-day DDR) | < 90s sequential / < 30s parallel async |
| NL query response | < 3s end-to-end |
| AI compute cost | < $1/day at 10–15 DDRs/day |
| Go ↔ Python backend parity | Identical test suite passes both before selection |
| Pre-splitter date boundary detection | 100% on both sample PDFs (109-page + 229-page) |
| Correction context payload size | Minimal — summarized corrections only, not full history dump |

### Measurable Outcomes

- Occurrence Excel export matches target table format (Well Name / Surface Location / Type / Section / mMD / Density / Notes, dark header row)
- Edit history sheet included in exported Excel when corrections were made
- Zero occurrences silently dropped due to dedup logic errors
- Section classification (Surface / Int. / Main) correct ≥ 90% based on inferred casing shoe depths
- Master Excel aggregates correctly across all processed DDRs
- Correction store entries contain: original value, corrected value, field name, reason, DDR source, date, user

## Product Scope

### MVP

- React/Vite/Tailwind web UI — login, PDF upload, processing status, occurrence table
- Extraction pipeline: pdfplumber pre-split → per-date PDF chunks → Gemini 2.5 Flash-Lite (responseSchema) → Pydantic validation
- Occurrence engine: ~250-keyword classification → 15–17 parent types, mMD inference (description + backward scan), density nearest-timestamp join, dedup by (type, mMD)
- **Inline occurrence editing** — any field editable before export; edit triggers reason capture modal (field, original value, corrected value, reason, user, timestamp)
- **Correction store** — PostgreSQL table storing all edits with metadata; fed as minimal summarized context into future occurrence generation prompts
- PostgreSQL sessions store: raw Gemini response + final JSON + error log per date chunk
- Occurrence table: filterable by type, section, well, date range; color-coded type badges
- Excel export: per-report `.xlsx` (occurrences + edit history sheet if edits made) + master `occurrences_all.xlsx`
- NL query interface: BM25 keyword search + Qdrant vector search over time log records
- Error logging + per-date re-run capability with manual date override
- Keyword list management — update keyword→type mappings without code deploy
- Single authenticated user role — all users have full access to all features
- Dual-backend: Go + Python at feature parity (same API surface, same test suite)

### Growth Features (Post-MVP)

- Bit Size replacing Section in occurrence table (requires bit record join per occurrence)
- Performance benchmarking across wells (ROP, NPT %, stuck pipe frequency by operator)
- Bulk historical archive ingestion with progress tracking
- Advanced saved query presets and filter bookmarks
- Correction analytics — show which types/fields corrected most (signals keyword list or prompt gaps)

### Vision

- Proactive NPT pattern detection across active jobs in real time
- Pason live data feed integration
- Client-facing portal
- Extraction-as-a-service for other oilfield service companies

## User Journeys

### Journey 1 — Ryan (Upload → Occurrences → Edit → Export)

Ryan uploads `~QWT~AB_WDF_0508851.pdf`. Processing completes: 15 dates, 23 occurrences generated. He reviews — 22 correct. One row classified as "Ream" but the Details text said "backreamed to free" — it should be "Back Ream." He clicks the Type cell, selects "Back Ream" from the dropdown. A modal appears: "Reason for edit?" He types: "Original text said 'backreamed to free' — this is a Back Ream, not Ream. Stuck pipe context in surrounding rows." He submits. Edit indicator appears on the row.

He exports — gets `.xlsx` with a second sheet "Edit History" (field=Type, original=Ream, corrected=Back Ream, reason, timestamp, DDR source). Next time a DDR with similar text is processed, the correction summary is injected as minimal context into the occurrence generation prompt — same mistake not repeated.

**Capabilities revealed:** Inline cell editing, reason capture modal (field/original/corrected/reason/user/timestamp), correction store, edit indicator on row, Excel export with edit history sheet, correction context injection on next run.

---

### Journey 2 — Ryan (Cross-Job Query)

Three months in. Client asks for all lost circulation events on their wells last quarter. Ryan types: "Show all lost circ events on Operator ARC Resources Q1 2025." 11 events across 4 wells returned in < 3s. He switches to master occurrences view, filters by operator + type + date range. Exports filtered `occurrences_all.xlsx`. Done in 90 seconds.

**Capabilities revealed:** NL query (BM25 + vector), master occurrences view, filter by operator/type/date, master Excel export.

---

### Journey 3 — Ryan (Failed Extraction)

DDR from non-standard contractor header. Processing: "12 extracted, 2 failed." Error log shows Tour Sheet Serial not detected on pages 44–52. Raw Gemini response for `20241031` logged — `time_logs` empty, Pydantic error recorded. Ryan re-runs `20241101` with manual date override — succeeds. `20241031` stays flagged "extraction incomplete" in the dashboard — not silently dropped.

**Capabilities revealed:** Per-date status (success/warning/failed), error log with raw response + Pydantic error, manual re-run with date override, failed-date flag (no silent corruption).

---

### Journey 4 — Sarah (Offset Well Research)

Prepping for a new Montney well. Filters history by formation/area — finds 3 comparable CES wells. Time logs show ROP by bit run, bit sizes, depths. Two wells show tight hole events in the same 1500–1700m depth band. Deviation surveys show inclination buildup at that zone. She exports time log data as CSV. 12 minutes vs. emailing a field supervisor and waiting.

**Capabilities revealed:** Well/area history filter, time log + deviation survey + bit record view, CSV data export.

---

### Journey 5 — Het (Pipeline Monitoring + Correction Review)

Monday: 31 DDRs processed, 1 failed, 2 warnings. Gemini cost: $2.14 for the week. He reviews the Correction Store — 14 edits across 5 DDRs. Top corrected field: Type (8 corrections). Pattern: "back ream" variants misclassified as "Ream." He adds 3 new keyword variants to the keyword list. Next extraction run picks them up without a model change.

**Capabilities revealed:** Processing queue + cost monitor, correction store review, keyword list management, raw session data viewer.

---

### Journey Requirements Summary

| Capability | Revealed By |
|---|---|
| PDF upload + processing status | J1 |
| Per-date extraction + occurrence generation | J1 |
| Occurrence table (type/section/mMD/density/notes) | J1 |
| Inline cell editing with reason capture modal | J1 |
| Correction store (field/original/corrected/reason/user/timestamp) | J1 |
| Edit indicator on row | J1 |
| Excel export — per-report + edit history sheet | J1 |
| Correction context injection on next occurrence run | J1 |
| NL query (BM25 + vector) | J2 |
| Master occurrences view + export | J2 |
| Filter by operator/type/date | J2 |
| Error log + manual re-run + date override | J3 |
| Failed-date flag — no silent drops | J3 |
| Well/area history filter + data export | J4 |
| Processing queue + cost monitor | J5 |
| Correction store review dashboard | J5 |
| Keyword list management | J5 |

## Domain-Specific Requirements

### Data Integrity & Operational Trust

- Extracted data used for client billing, performance reporting, and safety investigations — errors have real consequences
- No silent data loss: failed extractions flagged, not omitted from aggregates
- Raw source data (Gemini responses, original PDFs) retained and accessible — audit trail for any disputed occurrence or NPT figure
- Correction store maintains full edit history: who changed what, when, and why

### Data Sensitivity & Access Control

- DDR data contains proprietary operational information (client well names, drilling performance, incident records)
- Internal-only access — no public endpoints, no unauthenticated routes
- **Single user role: all authenticated users have full access** — upload, query, edit, export, pipeline management, keyword list editing. No RBAC required for V1.
- No client data shared between operator accounts — DDR data scoped per job/client in queries and exports

### Domain Data Formats

- **Pason DDR PDF**: native text, CAOEC tour sheet standard — 5-column tour grid (Bits / Drilling Assembly / Mud Record / Deviation Surveys / Time Log). Non-standard contractor layouts exist and must be handled gracefully
- **Tour Sheet Serial Number format**: `XXXXXX_YYYYMMDD_XA` — primary date boundary signal; format variants across contractors logged and handled via manual override
- **Depth units**: metres throughout — no imperial conversion needed for V1 (Alberta metric standard)
- **Time format**: HH:MM 24-hour — tour boundaries cross midnight on some jobs
- **Mud density units**: kg/m³ throughout

### Occurrence Classification Constraints

- Type classification is a rule-based keyword engine (~250 keywords → 15–17 parent types) — not free-form NLP. Keyword list is the authoritative source; any user can update it without a code deploy
- mMD inference: prefer problem-line stated depth; backward scan through time log only when no depth on problem line (Igor's rule: hole depth ≠ problem depth during trips — problem-line depth takes priority)
- Section classification (Surface / Int. / Main) derived from inferred casing shoe depths — fallbacks: Surface = 600m, Intermediate = 2500m when not detectable
- Density: nearest-timestamp mud record within same tour — cross-tour density lookup not permitted
- Dedup: (type, mMD) pair — same type at same depth within a report = one occurrence

### Integration Constraints

- No external data dependencies at runtime — extraction runs from uploaded PDFs + Gemini API only
- Gemini API key stored as environment variable, never in code or logs
- Qdrant: vector store for NL query (self-hosted or Qdrant Cloud)
- PostgreSQL: primary store — JSONB for raw responses and final JSON
- Excel export: `excelize` (Go) / `openpyxl` (Python) — `.xlsx` is the primary client deliverable format

### Performance & Availability

- Internal tooling — no formal SLA for V1, but processing must not block navigation
- Processing queue: async, non-blocking — user can navigate away during processing
- Failed extractions must not block other dates in the same DDR from completing

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| Extraction error used in client NPT report | Inline edit + reason capture before export; raw source retained for verification |
| Keyword misclassification becomes systemic | Correction store surfaces patterns; any user can update keyword list without redeploy |
| Tour Sheet Serial format changes across contractors | Graceful fallback + manual date override on re-run; error logged with raw page content |
| mMD incorrectly inferred | Problem-line depth prioritized; backward scan only as fallback; mMD editable inline |
| Go vs. Python parity drift | Shared test suite; identical API contract; selection decision gates V1 launch |
| Multi-date overflow — Tour 3 of date X spills onto page containing date Y header | Pre-splitter must detect both serial numbers on same page and assign pages correctly; validated in PoC on 109-page + 229-page samples |
| TIME LOG row order disrupted — Gemini reorders rows when `Details` text is long | Validate row-order preservation in PoC; prompt instructs model to preserve input row sequence; Pydantic checks row count vs. page density |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Native-Text Reframing (Core Architectural Insight)**
Every prior DDR extraction attempt treated PDFs as scan/OCR problems. The breakthrough: Pason DDR PDFs are native text. pdfplumber reads coordinate-positioned words directly — no GPU, no vision model, no base64 image pipeline. This collapses a 12-minute multi-stage ML pipeline into a 2-step extract-and-map flow at ~$0.02/report. The innovation is the correct mental model, not a new technology.

**2. Self-Improving Occurrence Classification via Human Correction Loop**
Occurrences are generated by a deterministic keyword rule engine (~250 keywords). Users correct mistakes inline with structured reason metadata (field, original, corrected, reason, timestamp). Corrections are summarized and injected as minimal context on the next occurrence generation pass — not a model fine-tune, not full-history retrieval, just a targeted "here's what was wrong last time" prompt addition. Over time the system learns domain-specific edge cases that no general-purpose model would know.

**3. Keyword List as Deployable Domain Knowledge**
The ~250-keyword classification table is user-editable at runtime without a code deploy. This externalizes domain expertise from code into a data artifact that field experts can maintain directly. Standard ML systems require retraining; this system improves through expert curation.

**4. Dual-Backend Validation Pattern**
Go and Python backends built to identical feature parity and API contract, validated by a shared test suite. Selection deferred to post-PoC evidence. Deliberate architectural optionality — avoids premature lock-in where the right answer is genuinely unknown until measured.

### Market Context & Competitive Landscape

- Pason DataHub API: operator-facing only — service companies receive PDFs, not API access
- WellView, VERDAZO, Spotfire, OpenWells: require pre-structured data — no extraction layer
- SLB internal pipeline: not sold, not accessible to service companies
- Docling: accurate but 12+ min/report on T4 GPU — wrong tool for native PDFs
- LlamaExtract: degrades on 170+ page PDFs without DDR date-boundary awareness
- **White space**: no commercial extraction layer exists for oilfield service companies receiving Pason PDFs

### Validation Approach

| Innovation | Validation Method | Go/No-Go |
|---|---|---|
| Native-text pipeline | 3-day PoC on 109-page + 229-page sample PDFs | ≥ 95% field accuracy vs. ground truth |
| Occurrence keyword engine | Compare vs. Het's converter ground truth on known DDRs | ≥ 90% type classification accuracy |
| Correction context injection | 30 corrections ingested → measure edit rate on next 10 DDRs | Edit rate drops measurably |
| Dual-backend parity | Shared test suite must pass both before selection decision | 100% test parity |

### Innovation Risk Mitigation

| Risk | Mitigation |
|---|---|
| responseSchema rejects complex schema → Gemini 400 | Escalate to `responseJsonSchema` (supports `$ref`, added Nov 2025) |
| Correction context grows too large → prompt bloat | Hard cap: inject only last N corrections, summarized not verbatim |
| Keyword list diverges between Go + Python backends | Single source-of-truth file; both backends read same artifact |
| Native-text assumption wrong for some contractors | pdfplumber scan confirms text layer before pipeline starts; flag if empty |

## Web Application Specific Requirements

### Project-Type Overview

Single-page application (React/Vite/Tailwind). Internal tool behind authentication — no public access, no SEO, no mobile browser requirement. Desktop-first. Two distinct functional surfaces: pipeline operations (upload, monitor, edit occurrences) and query/history (NL search, filter, export).

### Technical Architecture Considerations

**Frontend stack (locked):** React + Vite + Tailwind CSS. Static credentials for V1 auth — no OAuth/SSO required.

**API contract:** Frontend talks to one backend URL. Same API surface served by both Go and Python backends — frontend must not assume language-specific behavior. JSON throughout.

**State management:** React `useState`/`useEffect` sufficient for V1. Processing status via polling (`useEffect` interval) or SSE — not WebSocket.

### Browser Matrix

| Browser | Support |
|---|---|
| Chrome (latest) | Required — primary |
| Edge (latest) | Required |
| Firefox (latest) | Required |
| Safari | Best-effort |
| Mobile browsers | Not required for V1 |
| IE / Legacy | Not supported |

### Responsive Design

Desktop-only for V1. Minimum viewport: 1280px. No mobile breakpoints. Occurrence table is data-dense — fixed column widths, horizontal scroll on overflow.

### Accessibility Level

Basic usability for V1 — keyboard navigation for primary flows, sufficient color contrast on type badges. No WCAG 2.1 AA compliance required.

### Implementation Considerations

- Type badge colors (`TYPE_COLOURS`) and section badge colors (`SECTION_COLOURS`: Surface=emerald, Int.=sky, Main=indigo) already defined — maintain consistency
- Login uses static credentials for V1 — no session refresh complexity
- Edit modal must not break table scroll position
- Keyword list editor: simple table UI, add/remove/edit rows, save triggers backend update

## Project Scoping

### Strategy & Philosophy

**Approach:** Problem-solving single release — deliver the complete core workflow (upload → extract → occurrences → edit → export) reliably. No partial feature delivery. Users get the full job-to-be-done on day one.

**Resource Requirements:** 1–2 developers. Dual-backend is the primary resource multiplier — explicit selection milestone gates indefinite parallel maintenance.

### Complete Feature Set

**Core User Journeys Supported:** All 5 journeys (upload+extract, cross-job query, failed extraction recovery, offset well research, pipeline monitoring).

**Must-Have Capabilities:** All capabilities listed in FR1–FR35 (Functional Requirements section). The complete tech-stack decisions backing these capabilities are in the Product Scope section.

**Nice-to-Have Capabilities** (include if capacity allows; not blocking launch):

| Capability | Why Deferrable |
|---|---|
| Bit Size replacing Section in occurrence table | Requires bit record join per occurrence; Scott confirmed either approach acceptable |
| Performance benchmarking across wells (ROP, NPT %) | Needs external data (Enverus/geoLOGIC) — no dependency exists yet |
| Bulk historical archive ingestion tooling | Manual upload sufficient for V1 volume |
| Advanced saved query presets and filter bookmarks | Quality-of-life, not core workflow |
| Correction analytics dashboard | Correction store itself is the value; analytics are visibility |

**Out of Scope (V2+):**

- Proactive NPT pattern detection across active jobs
- Pason live data feed integration
- Client-facing portal
- Extraction-as-a-service

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Mitigation |
|---|---|
| NL query (Qdrant) more complex than expected | BM25 keyword search ships first; Qdrant vector search added after. Journey 2 functions on BM25 alone. |
| Dual-backend doubles timeline | Hard gate: backend selection milestone before V1 launch. If parity not achieved, default to Python (AI ecosystem advantage). |
| Correction context injection degrades accuracy | A/B test: 10 DDRs with vs. without correction context. Revert if accuracy drops. |
| Gemini responseSchema rejects complex nested schema | Escalation path: responseJsonSchema (supports $ref, available Nov 2025). |
| Native-text assumption fails for some contractors | pdfplumber confirms text layer present before pipeline starts; flags empty pages. |

**Market Risks:**

| Risk | Mitigation |
|---|---|
| Extraction accuracy < 95% → management trust breaks | PoC validation gates the build. No launch until 95% hit on sample set. |
| Wrong NPT figure reaches client report | Inline edit + reason capture + edit history sheet in exported Excel. Every export is auditable. |

**Resource Risks:**

| Risk | Mitigation |
|---|---|
| Dual-backend consuming 2× development time | Selection decision is time-boxed — not indefinite. Gate is explicit. |
| NL query (Qdrant) bottlenecking launch | Qdrant is the most isolatable subsystem — can be deferred to post-launch without blocking occurrence table, edit, or Excel export. |

## Functional Requirements

### Document Ingestion & Processing

- **FR1:** Users can upload a DDR PDF to the platform for processing
- **FR2:** System can detect date boundaries within a DDR PDF and split it into per-date chunks
- **FR3:** System can extract structured drilling data from each per-date chunk using an AI model
- **FR4:** System can validate extracted data against a defined schema and record validation errors
- **FR5:** Users can view real-time processing status for an in-progress or completed DDR ingestion

### Occurrence Generation & Management

- **FR6:** System can generate an occurrence table from validated extracted data
- **FR7:** System can classify each occurrence by type using a rule-based keyword engine
- **FR8:** System can infer measured depth (mMD) for each occurrence from time log data
- **FR9:** System can determine mud density for each occurrence from the mud record using timestamp proximity
- **FR10:** System can deduplicate occurrences within a report by type and depth
- **FR11:** Users can view the occurrence table for a DDR filtered by type, section, well, and date range

### Inline Editing & Correction Store

- **FR12:** Users can edit any field of any occurrence row before export
- **FR13:** System can capture reason and metadata (field name, original value, corrected value, user, timestamp, DDR source) when a user edits an occurrence
- **FR14:** System can store all occurrence edits and associated metadata in a persistent correction store
- **FR15:** System can inject a summarized subset of correction history as context when generating occurrences for future DDRs
- **FR16:** Users can review all stored corrections across all DDRs

### Data Export

- **FR17:** Users can export occurrences for a single DDR as a formatted Excel file
- **FR18:** Exported Excel files include an edit history sheet when corrections were made to that DDR's occurrences
- **FR19:** Users can export all occurrences across all processed DDRs as a single master Excel file
- **FR20:** Users can export time log data for a well as a CSV file

### Query & History

- **FR21:** Users can search occurrence and time log data using natural language queries
- **FR22:** Users can filter occurrence history across all DDRs by well, area, operator, type, and date range
- **FR23:** Users can view structured time log data for any processed well
- **FR24:** Users can view deviation survey data for any processed well
- **FR25:** Users can view bit record data for any processed well

### Pipeline Operations & Monitoring

- **FR26:** Users can view a processing queue showing status of all DDR ingestion jobs
- **FR27:** Users can view per-date extraction status (success / warning / failed) for any processed DDR
- **FR28:** Users can view error logs including raw AI response and schema validation errors for any failed date
- **FR29:** Users can re-run extraction for a specific failed date, with an optional manual date boundary override
- **FR30:** System marks failed extraction dates visibly in the occurrence view — they are not silently omitted from aggregates or counts
- **FR31:** Users can view AI compute cost tracking for the processing pipeline

### System Configuration & Access

- **FR32:** Users can update keyword-to-type mappings in the classification engine without a code deployment
- **FR33:** System retains the raw AI response and validated JSON for every processed date chunk
- **FR34:** System requires authentication before granting access to any feature or data
- **FR35:** All authenticated users have identical full access to all system capabilities

## Non-Functional Requirements

### Performance

- **NFR-P1:** Natural language query results must be returned within 3 seconds end-to-end from query submission
- **NFR-P2:** Full 30-day DDR (100–300 pages) must complete extraction in under 90 seconds sequential; under 30 seconds parallel async
- **NFR-P3:** Occurrence table must render within 500ms for datasets up to 100 rows
- **NFR-P4:** Initial application page load must complete within 2 seconds on an internal network
- **NFR-P5:** PDF upload must be acknowledged (processing started) within 1 second of submission
- **NFR-P6:** Excel export must complete within 30 seconds for a full DDR occurrence set

### Security

- **NFR-S1:** All application routes and API endpoints must reject unauthenticated requests — no public surface
- **NFR-S2:** The Gemini API key must be stored as an environment variable and must never appear in application logs, error messages, or source code
- **NFR-S3:** User credentials must be stored hashed — plaintext passwords must not be persisted at any layer
- **NFR-S4:** The application must make no outbound network calls except to Gemini API and Qdrant — no third-party analytics, telemetry, or CDN calls that would transmit DDR content externally

### Reliability

- **NFR-R1:** Extraction failure for one date chunk must not block or abort processing of other date chunks in the same DDR
- **NFR-R2:** The system must not silently discard occurrences — any extraction failure must be flagged with its error reason and remain visible in the UI
- **NFR-R3:** Raw Gemini responses and validated JSON must be retained with no TTL — session data is the audit trail and must not be auto-purged
- **NFR-R4:** The processing queue must be durable across application restarts — in-progress or queued jobs must not be silently lost

### Integration

- **NFR-I1:** The system must handle Gemini API rate limit errors (HTTP 429) gracefully — retry with exponential backoff, log the failure, and surface it as a per-date warning rather than a hard crash
- **NFR-I2:** The NL query interface must degrade gracefully to BM25 keyword search if Qdrant is unavailable — users must not receive an error, only reduced result quality
- **NFR-I3:** All PostgreSQL writes during extraction must be transactional — partial state from a mid-extraction failure must not be committed
- **NFR-I4:** Excel exports must be compatible with Excel 2016+ and LibreOffice Calc — no proprietary formatting that breaks on open
