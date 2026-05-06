---
title: "Product Brief: CES DDR Intelligence Platform"
status: "complete"
created: "2026-05-05"
updated: "2026-05-05"
version: "1.2"
inputs:
  - "_bmad-output/brainstorming/brainstorming-session-2026-05-01-001.md"
  - "_bmad-output/planning-artifacts/research/technical-ddr-pdf-pipeline-validation-research-2026-05-05.md"
  - "old_brainstorming/README.md"
  - "AGENTS.md"
  - "Web research: competitive landscape, market sizing, industry pain points"
---

# Product Brief: CES DDR Intelligence Platform

## Executive Summary

Canadian Energy Services (CES) runs drilling operations across dozens of wells in Alberta. After every rig-day in the field, a Pason system generates a Drilling Daily Report (DDR) — a 100–300 page PDF that contains everything that happened on that well: time logs, bit performance, mud records, deviation surveys, and drilling problem events. Today, the only way for CES management to understand what happened across jobs is to read these PDFs by hand.

The CES DDR Intelligence Platform transforms this process. It automatically ingests DDR PDFs, extracts all structured field data using a validated AI pipeline, and delivers a queryable history of every well CES has worked. Management can track drilling problems (stuck pipe, lost circulation, tight hole, kicks) across clients and time periods, benchmark performance across jobs, and identify patterns — in minutes, not days.

No commercially available tool solves this problem for oilfield services companies. Operators get API access to Pason data; service companies get PDFs. CES is building the extraction layer that does not exist off the shelf.

---

## The Problem

CES accumulates 10–15 DDR PDFs per day from active jobs — thousands per year. Each PDF is a 100–300 page Pason-generated report packed with structured drilling data: hourly time logs, bit specs, mud weights, formation depths, and flagged events like stuck pipe and lost circulation.

**Today's workflow is entirely manual.** When a manager wants to understand drilling performance across recent jobs — or answer a client's question about NPT history — someone opens PDFs and reads them. Data goes into Excel, if it's captured at all. Analysis is based on samples, not the full record.

The consequences are significant:
- **Slow decisions.** Drilling problem patterns that span multiple jobs go undetected until they surface as a client complaint or a safety incident.
- **Lost institutional knowledge.** Insights locked in PDFs never become searchable history.
- **Scale problem.** At 10-15 DDRs/day, manual review is already impractical. It does not improve.
- **Client deliverable burden.** Every NPT summary or performance report sent to clients requires a manual extraction pass — typically hours of work per report.

The industry feels this broadly — SLB documented processing "tens of thousands of reports" manually before building their own internal automation, which they described as eliminating a multi-million dollar drag. No equivalent product exists for oilfield services companies that aren't SLB.

---

## The Solution

The CES DDR Intelligence Platform has three layers:

**1. Extraction Pipeline**
DDR PDFs are uploaded via a web interface (React/Vite) and automatically processed. A date-aware pre-splitter (using pdfplumber) detects Pason's Tour Sheet Serial Number on each page and groups pages by drilling date. Each date chunk is sent to Gemini 2.5 Flash-Lite, which extracts all DDR fields into a validated JSON schema — header, daily checks, tours, time logs, bit records, mud data, and occurrence events. A Pydantic validation layer catches extraction errors before data is stored. Full processing of a 30-day DDR: under 90 seconds, at ~$0.02/report.

**2. History Dashboard**
Every processed report is stored in a searchable session database (PostgreSQL). The dashboard lets management filter by date range, well, client, and problem type — giving a complete structured history of all CES drilling activity.

**3. Natural Language Query**
A query layer (backed by vector search) lets users ask questions in plain English: "How many stuck pipe events did we have last quarter?", "Which wells had the highest NPT on Tour 1?", "Show me all lost circulation events on Operator X jobs." No SQL, no spreadsheet pivots.

---

## What Makes This Different

**No existing product solves this.** Pason's own DataHub API is available to operators, not service companies. WellView, VERDAZO, Spotfire, and OpenWells all assume data is already structured — they provide no extraction layer. SLB built their own internal pipeline; it is not sold externally. The white space is real.

**CES already has the data.** Every DDR processed by CES is an asset that currently provides no analytical value after the job closes. This tool makes the entire archive queryable — not as a data purchase or third-party integration, but from existing internal files.

**Cost is negligible at scale.** The chosen AI approach (Gemini 2.5 Flash-Lite) costs approximately $0.30–$0.50/day at full production volume (10–15 DDRs/day, ~2,500 pages). This is not a meaningful operational cost.

**The PDF-native insight.** Prior approaches (Docling, LlamaExtract, Document AI) failed because they applied OCR and vision pipelines to PDFs that contain native text. The validated architecture reads text directly — eliminating the 12-minute GPU pipeline and the architectural complexity it required.

---

## Who This Serves

**Primary: CES Management**
Managers responsible for job performance and client relationships. Currently reliant on selective manual review to understand drilling problems across active and historical jobs. Needs: fast answers to cross-job questions, reliable NPT tracking, and a defensible record of drilling performance per client.

**Secondary: Drilling Engineers and Supervisors**
Technical users who review offset well performance before and during new jobs. Currently search archived PDFs manually. Benefit: instant access to structured time log, bit, and deviation data for comparable wells.

---

## Success Criteria

- **Extraction coverage:** ≥95% of DDR fields extracted accurately vs. ground-truth review (validated against existing converter output as ground truth)
- **Processing time:** Full 30-day DDR (100–300 pages) processed in under 90 seconds (sequential) / under 30 seconds (parallel async)
- **Query response:** Natural language queries return results in under 3 seconds
- **Adoption:** Management team uses platform as primary DDR tracking tool within 30 days of launch — drilling problem review no longer requires opening source PDFs
- **Cost:** Under $1/day in AI compute at production volume (~$0.02–0.05 per DDR)

---

## Scope

**V1 includes:**
- Web UI (React/Vite/Tailwind) for PDF upload and processing status
- Extraction pipeline: pdfplumber pre-split + Gemini 2.5 Flash-Lite + Pydantic validation
- Structured storage of all DDR fields (headers, tours, time logs, bits, mud, occurrences)
- History dashboard — filter by well, date, client, problem type
- Natural language query interface over processed DDR history
- Client reporting — export NPT and drilling problem summaries per client/job
- Error logging and re-run capability for failed extractions

**V1 does not include:**
- Real-time rig data feed (Pason live data integration)
- Client-facing portal (internal CES use only)
- Predictive analytics or anomaly detection
- Multi-language support

---

## Roadmap Thinking

V1 establishes the data foundation. Once structured DDR data is accumulating at scale, the platform becomes something more valuable:

- **Performance benchmarking** — compare CES drilling metrics against industry (via Enverus / geoLOGIC public data integration)
- **Proactive insights** — flag early indicators of recurring problem types across active jobs before they escalate
- **Commercial angle** — if CES processes DDRs at sufficient scale, the extraction capability itself has potential value as a service to other operators or service companies facing the same problem

The white space CES is entering — Pason PDF → structured, queryable data for oilfield service companies — has no commercial incumbent. V1 builds the internal moat. The two-year path converts that internal capability into competitive differentiation.
