# Deferred Work

## Deferred from: code review of 4-0-well-name-surface-location-extraction (2026-05-12)

- **W5 (from story 3-4) / P1: DDR ownership authorization** — Any authenticated user can access/retry any DDR. Cannot implement without adding `user_id`/`created_by` column to `ddrs` table and a user-DDR association story. Single-tenant internal tool for now; requires its own story when multi-user isolation is needed.
