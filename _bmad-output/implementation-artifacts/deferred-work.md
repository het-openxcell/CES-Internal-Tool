# Deferred Work

## Deferred from: code review of 3-4-occurrence-generation-api-pipeline-integration (2026-05-11)

- **W1: `OccurrenceInDB` self-inheritance** — `occurrence.py` schemas has `class OccurrenceInDB(OccurrenceInDB)` — pre-existing, likely copy-paste error. Will cause NameError at import if class is moved/renamed. Fix when touching schemas.
- **W2: `density_join` non-numeric guard missing** — `density_join.py` does `float(r["depth_md"])` without try/except; LLM can emit `"N/A"` strings, causing ValueError that aborts generation. Pre-existing in density_join.py.
- **W3: `classify_type` keyword ordering** — First-match wins on dict iteration; if a text matches multiple keywords, classification depends on load order. Pre-existing; add priority/weight to keyword schema to make deterministic.
- **W4: `infer_mmd` stale-depth risk** — Backward scan within one day's `time_logs` can return a depth from hours earlier in the same day. Pre-existing design limitation in infer_mmd.py.
- **W5: No DDR ownership authorization** — `GET /ddrs/{id}/occurrences` (and other DDR endpoints) verify auth token but not that the user owns the DDR. Any authenticated user can enumerate all DDRs by ID. Pre-existing pattern across all routes; needs multi-tenancy story.
- **W6: `classify_section` unguarded ValueError** — Raises if `surface_shoe >= intermediate_shoe`. Production always uses defaults (600/2500) so safe now, but `generate_for_ddr` exposes shoe params. Defer until shoe depths become configurable.
- **W7: `OccurrenceInResponse` omits `is_exported`/`ddr_date_id`** — Intentional per AC3 field list. Revisit in Story 5-x (export) when `is_exported` status becomes relevant to UI.
