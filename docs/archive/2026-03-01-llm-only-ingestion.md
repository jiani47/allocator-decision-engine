# LLM-Only Ingestion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove deterministic ingestion path and API key input UI; the app always uses LLM extraction with the key from `.env.local`.

**Architecture:** Single ingestion path: upload → `parse_raw_file` → `step_llm_extract` → `step_normalize_from_llm`. Settings always provides the API key. `api_key_override` param removed from service functions. Deterministic `ingest.py` functions stay as test utilities.

**Tech Stack:** Streamlit, pydantic-settings, pytest

---

### Task 1: Remove `step_upload` and `step_normalize` from services

**Files:**
- Modify: `app/services.py:14-105`

**Step 1: Remove dead service functions and their imports**

Remove `step_upload()` (lines 54-61) and `step_normalize()` (lines 98-105). Remove unused imports: `ColumnMapping`, `build_normalized_universe`, `infer_column_mapping`, `read_csv`, `pd` (pandas). Also remove `api_key_override` param from `step_llm_extract()` and `step_generate_memo()` — just use `settings` directly.

The resulting `app/services.py` should have these functions only:
- `step_parse_raw`
- `step_llm_extract` (no `api_key_override`)
- `step_normalize_from_llm`
- `step_fetch_benchmark`
- `step_compute_metrics`
- `step_rank`
- `step_generate_memo` (no `api_key_override`)
- `step_create_run`
- `step_build_evidence`
- `step_export_markdown`
- `step_export_json`

**Step 2: Run tests to see what breaks**

Run: `pytest tests/ -v --tb=short 2>&1 | head -80`

Expected: `test_integration.py` tests that import `step_upload`/`step_normalize` will fail. All other tests pass.

**Step 3: Commit**

```
git add app/services.py
git commit -m "Remove step_upload and step_normalize from services"
```

---

### Task 2: Update integration tests

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Rewrite tests that used `step_upload`/`step_normalize`**

- `TestFullPipelineClean.test_upload_to_export` → rewrite to use `build_normalized_universe` directly from `ingest.py` (not via services)
- `TestFullPipelineClean.test_source_row_indices_present` → same rewrite
- `TestFullPipelineClean.test_source_row_indices_with_raw_context` → same rewrite
- `TestFullPipelineMessy.test_messy_csv_normalizes` → same rewrite
- `TestFullPipelineMessy.test_constraint_filtering` → same rewrite
- `TestTopKIntegration.test_top_k_limits_shortlist` → same rewrite
- `TestTopKIntegration.test_warning_resolutions_flow_to_fact_pack` → same rewrite

Replace the pattern:
```python
from app.services import step_upload, step_normalize
df, mapping, fhash = step_upload(content, filename)
universe = step_normalize(df, mapping, fhash)
```

With:
```python
from app.core.hashing import file_hash
from app.domains.alt_invest.ingest import build_normalized_universe, infer_column_mapping, read_csv
df = read_csv(content, filename)
mapping = infer_column_mapping(df)
universe = build_normalized_universe(df, mapping, file_hash(content))
```

Update imports at the top of the file: remove `step_upload`, `step_normalize` from the services import. Add imports from `ingest.py` and `hashing.py`.

**Step 2: Run tests**

Run: `pytest tests/test_integration.py -v --tb=short`

Expected: All pass.

**Step 3: Commit**

```
git add tests/test_integration.py
git commit -m "Update integration tests to use ingest functions directly"
```

---

### Task 3: Simplify UI Step 0 (Upload)

**Files:**
- Modify: `app/ui.py:430-549`

**Step 1: Rewrite Step 0**

Replace the entire Step 0 block. The new flow:
1. Title + format expander (keep as-is)
2. File uploader (keep as-is)
3. On upload: parse raw file, show success message, show single "Extract with LLM" button
4. No API key input, no deterministic fallback, no two-column button choice

```python
if st.session_state["step"] == 0:
    st.title("Equi")
    st.subheader("Allocator Decision Engine")
    st.markdown(
        "Turn messy manager data into normalized, validated, "
        "and defendable investment decisions."
    )

    with st.expander("Supported file format", expanded=True):
        st.markdown(
            "**CSV or Excel file** with **monthly** return time series per fund.\n\n"
            "Required data (column names are flexible):\n"
            "- **Fund name** — manager or fund identifier\n"
            "- **Date** — monthly frequency (e.g. 2022-01-01, 01/2022)\n"
            "- **Monthly return** — decimal (0.012) or percentage (1.2%)\n\n"
            "Optional: strategy, liquidity days, management fee, performance fee.\n\n"
            "*Not supported: summary-only files, daily/weekly data, "
            "multi-currency, or multiple asset classes in one file.*"
        )

    uploaded = st.file_uploader(
        "Upload fund universe", type=["csv", "xlsx", "xls"]
    )

    if uploaded:
        content = uploaded.getvalue()
        filename = uploaded.name

        try:
            from app.services import step_parse_raw

            settings = Settings()
            raw_context = step_parse_raw(
                content, filename, max_rows=settings.ingestion_max_rows
            )
            st.session_state["uploaded_content"] = content
            st.session_state["uploaded_name"] = filename
            st.session_state["raw_context"] = raw_context

            st.success(
                f"Parsed {raw_context.total_rows} rows, "
                f"{len(raw_context.headers)} columns, "
                f"{len(raw_context.data_rows)} data rows"
            )

            if st.button("Extract with LLM", type="primary"):
                try:
                    from app.services import step_llm_extract

                    with st.spinner("Extracting fund data with LLM..."):
                        result, errors = step_llm_extract(
                            raw_context, settings,
                        )
                    st.session_state["llm_result"] = result
                    st.session_state["llm_validation_errors"] = errors
                    _go_to(1)
                    st.rerun()
                except DecisionEngineError as e:
                    st.error(f"LLM extraction failed: {e}")

        except Exception as e:
            st.error(f"Failed to parse file: {e}")
```

**Step 2: Clean up `_reset_from`**

Remove stale keys from the reset map: `raw_df`, `mapping`, `file_hash`, `api_key`, `ingestion_method`.

New step 0 reset list:
```python
0: ["universe", "benchmark", "fund_metrics",
    "mandate", "ranked", "run_candidates", "memo", "fact_pack", "decision_run",
    "raw_context", "llm_result", "llm_validation_errors",
    "dismissed_warnings", "warning_resolutions"],
```

**Step 3: Remove unused import**

Remove `ColumnMapping` from the imports at the top of `ui.py` (line 13) since the column mapping UI is gone.

**Step 4: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('app/ui.py', doraise=True)"`

Expected: No errors.

**Step 5: Commit**

```
git add app/ui.py
git commit -m "Simplify Step 0: LLM-only upload flow, remove API key input"
```

---

### Task 4: Remove `_render_column_mapping_step` and simplify Step 1

**Files:**
- Modify: `app/ui.py:88-167` (column mapping helper) and `app/ui.py:551-563` (Step 1 block)

**Step 1: Delete `_render_column_mapping_step` function**

Remove the entire function definition (lines 88-166).

**Step 2: Simplify Step 1 block**

Replace the `ingestion_method` branching:
```python
elif st.session_state["step"] == 1:
    st.header("Step 2: Review LLM Interpretation")
    _render_llm_review_step()
```

**Step 3: Clean up `_render_llm_review_step` re-extract button**

In `_render_llm_review_step`, simplify the re-extract button (around line 282-292). Remove `api_key` resolution logic. Just use `settings` directly:

```python
    with bc2:
        if st.button("Re-extract with LLM"):
            try:
                from app.services import step_llm_extract

                settings = Settings()
                with st.spinner("Re-extracting with LLM..."):
                    result, errors = step_llm_extract(raw_context, settings)
                st.session_state["llm_result"] = result
                st.session_state["llm_validation_errors"] = errors
                st.rerun()
            except DecisionEngineError as e:
                st.error(f"LLM extraction failed: {e}")
```

**Step 4: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('app/ui.py', doraise=True)"`

**Step 5: Commit**

```
git add app/ui.py
git commit -m "Remove column mapping step, simplify Step 1 to LLM-only"
```

---

### Task 5: Simplify Memo step (Step 7)

**Files:**
- Modify: `app/ui.py` — Step 7 block (memo generation)

**Step 1: Rewrite Step 7**

Remove all API key resolution. Use `settings` directly. Remove `api_key_override` passing.

```python
elif st.session_state["step"] == 7:
    st.header("Step 8: IC Memo Generation")

    st.markdown(
        "Generate an IC memo using Claude to draft narrative "
        "from the deterministic fact pack produced in the previous steps."
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back", key="memo_back"):
            _reset_from(6)
            _go_to(6)
            st.rerun()
    with bc2:
        if st.button("Skip to Export", key="memo_skip"):
            _go_to(9)
            st.rerun()

    if st.button("Generate Memo", type="primary"):
        try:
            from app.services import step_generate_memo

            settings = Settings()
            with st.spinner("Generating IC memo via Claude..."):
                memo, fact_pack = step_generate_memo(
                    st.session_state["ranked"],
                    st.session_state["universe"],
                    st.session_state["mandate"],
                    st.session_state.get("benchmark_symbol", "SPY"),
                    settings,
                    warning_resolutions=st.session_state.get("warning_resolutions"),
                )
            st.session_state["memo"] = memo
            st.session_state["fact_pack"] = fact_pack
            _go_to(8)
            st.rerun()
        except DecisionEngineError as e:
            st.error(f"Memo generation failed: {e}")
```

**Step 2: Verify syntax**

Run: `python -c "import py_compile; py_compile.compile('app/ui.py', doraise=True)"`

**Step 3: Commit**

```
git add app/ui.py
git commit -m "Simplify memo step: remove API key input"
```

---

### Task 6: Run full test suite and verify

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`

Expected: All tests pass. No imports of `step_upload` or `step_normalize` remain in services or UI.

**Step 2: Verify no dead references**

Run: `grep -r "step_upload\|step_normalize[^_]\|api_key_override\|api_key_input\|ingestion_method\|raw_df\|_render_column_mapping" app/`

Expected: No matches in `app/` (only in `tests/` for `build_normalized_universe` usage).

**Step 3: Final commit**

```
git add -A
git commit -m "Remove deterministic path and API key UI — LLM-only ingestion"
```
