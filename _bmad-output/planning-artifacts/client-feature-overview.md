# CES DDR Intelligence Platform — Feature Overview

**Prepared for:** Canadian Energy Services  
**Document type:** Internal Platform — Feature Summary  
**Date:** 2026-05-05

---

## What This Platform Does

The CES DDR Intelligence Platform turns your Drilling Daily Reports into a searchable, queryable record of every well CES has worked. Instead of opening PDFs by hand to find drilling problem history, you upload a report and get a structured table of events — ready to review, correct, and send to clients.

---

## Features

### 1. Report Upload & Automatic Processing

- Upload a DDR report file to the platform
- The system automatically reads and processes the report
- Each day within the report is extracted individually
- Processing status is shown in real time — you can see which days succeeded, which had issues, and why
- Multiple reports can be in the queue at the same time

---

### 2. Occurrences Table

The core deliverable. For every report uploaded, the platform generates a table of drilling problem events — one row per occurrence.

Each occurrence row contains:

| Field | What it shows |
|---|---|
| Well Name | Name of the well |
| Surface Location | Legal surface location |
| Type | Problem type (Lost Circulation, Stuck Pipe, Tight Hole, Kick, Back Ream, Cement Plug, etc.) |
| Section | Hole section where the event occurred |
| Measured Depth (mMD) | Depth at time of event, in metres |
| Mud Density | Mud weight at time of event |
| Notes | Summary of what happened, from the tour sheet |

Events are automatically classified from ~250 known problem keywords. The system infers depth and mud density from the surrounding data when they are not stated directly on the problem line.

---

### 3. Inline Editing & Reason Tracking

Before exporting, any field in the occurrence table can be edited directly on screen.

- Click any cell to edit it
- A prompt asks for the reason for the change
- The original value, corrected value, reason, and timestamp are all recorded
- An edit indicator marks which rows were changed
- This history is included in the exported file as a separate sheet

**Why this matters:** Over time, the corrections you make are fed back into future report processing — so the same mistake is not repeated.

---

### 4. Export to Excel

- Export occurrences for a single report as a formatted `.xlsx` file
- If edits were made, the export includes an "Edit History" sheet
- Export all occurrences across every processed report as a single master file
- Export raw time log data as a spreadsheet for your own analysis

---

### 5. Search & Query

Type a plain-English question to search across your full report history:

> *"Show all lost circulation events on Operator ARC Resources in Q1 2025"*  
> *"Which wells had stuck pipe events above 2000m in the last 6 months?"*

Results come back in seconds, across all uploaded reports.

---

### 6. History Dashboard & Filtering

Browse and filter the full occurrence history across all reports:

- Filter by well name, area, operator, problem type, section, or date range
- View time logs, deviation surveys, and bit records for any well — without opening the source report
- Export filtered data to Excel

---

### 7. Error Handling & Re-Processing

If any day within a report fails to process:

- The failure is flagged clearly — never silently dropped
- The raw extracted data and the specific error are logged and viewable
- Any failed day can be re-processed, with the option to manually specify the date if the report format was non-standard
- Failed days are marked in the occurrence view so counts are never misleading

---

### 8. Processing Monitor & Cost Tracking

- View a live queue of all report processing jobs
- See status for every day within every report (success / warning / failed)
- Track weekly processing costs to stay on budget
- Review the raw extracted data for any report, any day

---

### 9. Classification Rule Management

The problem-type keyword list (~250 keywords → ~15–17 parent types) is fully editable by any user — no developer required. When a keyword is missing or a type mapping is wrong, it can be fixed directly in the platform. The next report processed will use the updated rules.

---

## Summary

| Capability | Included |
|---|---|
| Upload reports + real-time processing status | ✅ |
| Auto-generated occurrence table (7 fields) | ✅ |
| Inline editing with reason tracking | ✅ |
| Excel export — per-report + master + edit history | ✅ |
| Natural language search across all reports | ✅ |
| Filter & browse full occurrence history | ✅ |
| Time log, deviation survey, bit record viewer | ✅ |
| Error log + re-processing with date override | ✅ |
| Processing monitor + cost tracking | ✅ |
| Keyword classification rule editing | ✅ |
