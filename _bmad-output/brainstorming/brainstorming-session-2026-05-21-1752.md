---
stepsCompleted: [1, 2]
inputDocuments: []
session_topic: 'Compact correction-context format for model prompts'
session_goals: 'Find ways to encode maximum correction history/context in minimal text so future extraction models learn from user edits without bloating prompts.'
selected_approach: 'progressive-flow'
techniques_used: ['First Principles Thinking', 'Solution Matrix', 'SCAMPER Method', 'Decision Tree Mapping']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** pi
**Date:** 2026-05-21

## Session Overview

**Topic:** Compact correction-context format for model prompts
**Goals:** Find ways to encode maximum correction history/context in minimal text so future extraction models learn from user edits without bloating prompts.

### Context Guidance

CES DDR extraction stores corrections as field-level edits with original value, corrected value, reason, DDR/occurrence metadata, and timestamps. Current UI shows raw old/new text, but for model prompts long notes and repeated corrections can waste tokens.

### Session Setup

Fresh session focused on prompt-context compression, correction memory, and compact model-readable representations.

## Technique Selection

**Approach:** Progressive Technique Flow
**Journey Design:** Systematic development from raw correction history to compact prompt-ready memory.

**Progressive Techniques:**

- **Phase 1 - Exploration:** First Principles Thinking for stripping correction context to irreducible signal.
- **Phase 2 - Pattern Recognition:** Solution Matrix for mapping context dimensions to compact encodings.
- **Phase 3 - Development:** SCAMPER Method for improving candidate schema formats.
- **Phase 4 - Action Planning:** Decision Tree Mapping for choosing implementation path and refresh behavior.

**Journey Rationale:** This problem is token-economy design. We need identify what the model truly needs, compress repeated evidence, preserve examples that teach extraction behavior, and avoid sending raw long text unless it changes model decisions.
