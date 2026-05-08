# Deferred Work

## Deferred from: code review of 2-6-extraction-cost-tracking-time-log-embedding (2026-05-08)

- `QDRANT_API_KEY` should use `SecretStr` — pre-existing pattern: all settings secrets use plain `str`; upgrade to `SecretStr` across all settings in a single pass
- `mark_failed`/`mark_warning` lack `commit=False` param — asymmetric vs `mark_success`; add when a future story needs failure path to participate in a larger transaction
- `_commit_outcome` commits both repo sessions — pre-existing behavior from Story 2.4; revisit if session-per-request lifecycle is refactored
- Other startup files / test fixtures may still call `create_all` — full audit needed; `events.py` removal satisfies AC7 but fixtures not checked
