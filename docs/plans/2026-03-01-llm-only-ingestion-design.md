# Design: LLM-Only Ingestion

## Problem

The UI has two ingestion paths (LLM extraction and deterministic column mapping) plus API key input fields in two places. Since a dev API key is now always available via `.env.local`, the deterministic path and key input UI are unnecessary complexity.

## Changes

### UI (`app/ui.py`)

**Step 0 (Upload):**
- Remove API key text input and all `api_key` / `api_key_input` logic
- Remove deterministic fallback parsing (`step_upload`, `raw_df`, `mapping`, `file_hash`)
- Remove two-button choice. Single flow: upload -> parse raw -> "Extract with LLM" button
- Remove `ingestion_method` session state tracking

**Step 1 (Review Interpretation):**
- Remove `_render_column_mapping_step()` helper entirely
- Always render `_render_llm_review_step()`, remove `ingestion_method` branching

**Step 7 (Memo Generation):**
- Remove API key input UI and resolution logic (`env_key` / `stored_key` / prompt)
- Use `settings.anthropic_api_key` directly, remove `api_key_override` passing

**`_reset_from`:**
- Remove stale session keys: `raw_df`, `mapping`, `file_hash`, `api_key`, `ingestion_method`

### Services (`app/services.py`)
- Remove `step_upload()` and `step_normalize()`
- Remove their imports (`infer_column_mapping`, `read_csv`, `build_normalized_universe`)

### Backend (`app/domains/alt_invest/ingest.py`)
- No changes. Deterministic functions kept as internal utilities for tests.

### Tests
- Remove integration tests that exercise the deterministic service path (`step_upload`, `step_normalize`)
- Existing unit tests using `build_normalized_universe` directly are unchanged
