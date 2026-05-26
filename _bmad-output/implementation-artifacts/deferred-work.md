# Deferred Work

## Deferred from: code review of 4-0-well-name-surface-location-extraction (2026-05-12)

- **W5 (from story 3-4) / P1: DDR ownership authorization** — Any authenticated user can access/retry any DDR. Cannot implement without adding `user_id`/`created_by` column to `ddrs` table and a user-DDR association story. Single-tenant internal tool for now; requires its own story when multi-user isolation is needed.

## Deferred from: code review of 4-1-corrections-database-schema (2026-05-18)

- **`CorrectionInResponse` exposes raw `user_id` UUID** — No user name/email embedded. Story 4-4 GET /corrections API should embed a user sub-schema to avoid N+1 lookups by consumers.
- **`field_name` is free-text with no enum** — Valid correction field names not validated against a known set. Story 4-2 service layer should validate against known occurrence field names.

## Deferred from: code review of 7-5-rbac-schema-seeded-admin-user-management-api (2026-05-26)

- **W1: JWT role staleness post-issuance** — Roles embedded at token issuance; role changes or deactivation not reflected until token expiry. Pre-existing JWT architecture trade-off. Requires token revocation (blocklist) or short TTLs to address.
- **W2: Test body assertions too weak** — `test_post_users_creates_user` checks only status code, not response body. `StubUserRepo` hardcodes `"new-id"` masking duplicate-create bugs. Strengthen when test coverage pass is scheduled.
- **W3: `UserResponse.id` string format not canonical UUID** — No hyphen/case enforcement on serialized UUIDs. Pre-existing pattern across codebase; fix in a schema normalization story.

## Deferred from: LLM occurrence generation (llm_generate.py, 2026-05-13)

- **Observability: silent return 0 on parse failure** — When `json.loads` or Pydantic validation fails, `generate_for_ddr` logs an error and returns 0. Caller cannot distinguish "DDR has no occurrences" from "LLM response was unparseable." Consider adding a failure status flag or raising a typed exception so the pipeline can surface this to the UI.
- **Prompt injection via unescaped DDR content** — `_format_time_logs` and `_format_existing` interpolate `row.final_json` content directly into the prompt with no delimiters. A malformed DDR PDF could contain instruction-injection text. Low risk for internal single-tenant tool, but consider XML-tag delimiters (`<time_logs>...</time_logs>`) when hardening.
- **`genai.Client` instantiated per DDR run** — `LLMOccurrenceGenerationService.__init__` creates a new HTTP client on each `_generate_occurrences` call. For high-throughput pipelines, make the client a module-level singleton or injectable dependency.
