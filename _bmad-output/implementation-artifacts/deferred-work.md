# Deferred Work

## Deferred from: code review of 3-4-occurrence-generation-api-pipeline-integration (2026-05-11)

- **W4: `infer_mmd` backward scan can return stale same-day depth** — If a time log entry has no `depth_md`, the backward scan returns the last known depth from earlier in the same day. This is intentional algorithm design but can produce an MMD that is hours stale. Requires rethinking the algorithm (e.g., max-lookback limit, or requiring depth on classified entries) before changing. Pre-existing in `infer_mmd.py`.
- **W5: No DDR ownership authorization** — Any authenticated user can read any DDR's occurrences (and other DDR data) by ID. The `DDR` model has no `user_id`/`created_by` column — cannot add ownership checks without a DB schema migration and user-DDR association story. Single-tenant internal tool for now; revisit when multi-user isolation is required.
