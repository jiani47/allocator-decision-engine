# Stress Test Plan – Tightened MVP (Allocator Decision Engine)

This package includes **synthetic but realistic** sample inputs that simulate the messy fund-universe files analysts receive.

## Files included
- `01_clean_universe.csv` – clean monthly returns + optional attributes
- `02_messy_universe.csv` – mixed date formats, percent strings, whitespace/casing fund names, duplicates, missing months, outlier return
- `03_mixed_frequency.csv` – includes some non-month-start dates (should warn/reject as mixed frequency)
- `04_summary_only.csv` – summary stats only (should reject in V1)
- `benchmark_spy_monthly.csv` – offline benchmark series for testing alignment logic (for local dev without external APIs)

## What we are stress-testing

### A) Ingestion & Schema Mapping
**Goal:** user can map columns to canonical fields with minimal friction.

**Must handle (V1):**
- date column in multiple formats (YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY)
- return column as decimals or percent strings (e.g., `1.23%`)
- optional columns present or missing

**Acceptance criteria:**
- system proposes mapping for `fund_name`, `date`, `monthly_return`
- user can confirm mapping
- unmapped optional columns don’t block run

### B) Normalization
**Goal:** produce a canonical `NormalizedUniverse`.

**Must normalize:**
- dates → monthly period (YYYY-MM)
- returns → float decimal (e.g., 0.0123)
- fund identifiers → trimmed + standardized (case/whitespace normalization)

**Acceptance criteria:**
- `02_messy_universe.csv` normalizes without manual spreadsheet edits
- duplicates detected and surfaced (dedupe policy must be explicit)
- missing months detected per fund (warning-level)
- outlier detection flags extreme values (warning-level)

### C) Frequency Validation (Guardrail)
**Goal:** V1 supports monthly frequency only.

**Acceptance criteria:**
- `03_mixed_frequency.csv` produces a clear error or blocking warning:
  - "Mixed frequency / non-monthly dates detected" 
  - and points to sample offending rows

### D) Reject Summary-Only Inputs
**Goal:** enforce narrow MVP boundary.

**Acceptance criteria:**
- `04_summary_only.csv` is rejected with a message:
  - "Monthly return time series required in V1"

### E) Metric Engine
**Goal:** deterministic metrics computed from normalized monthly returns.

**Metrics (V1):**
- annualized return
- annualized vol
- sharpe (rf=0)
- max drawdown
- correlation to benchmark

**Acceptance criteria:**
- metrics compute for all funds with ≥ 12 months data (policy defined)
- funds with insufficient history are flagged and optionally excluded from ranking

### F) Benchmark Alignment
**Goal:** benchmark series aligned to fund date range.

**Acceptance criteria:**
- benchmark monthly returns computed from adj_close
- alignment uses overlapping date range only
- missing overlap is flagged

### G) Mandate Form → Constraints
**Goal:** small set of constraints works end-to-end.

**Acceptance criteria:**
- liquidity constraint filters funds when liquidity_days is present
- max drawdown constraint filters funds
- strategy include/exclude works

### H) Ranking & Shortlist
**Goal:** stable, explainable ranking.

**Acceptance criteria:**
- ranking uses normalized metric scores and configured weights
- constraint violations are visible in the table
- shortlist is reproducible for same run inputs

### I) Memo + Audit
**Goal:** every memo claim links to metric IDs and raw data rows.

**Acceptance criteria:**
- memo generation fails closed if output JSON invalid
- every claim references existing metric IDs
- audit panel shows:
  - metric value + formula + date range
  - raw rows used (with original row index preserved)

## Suggested manual test script (15–20 minutes)
1. Run with `01_clean_universe.csv` → ensure “happy path” works.
2. Run with `02_messy_universe.csv` → verify warnings:
   - duplicates
   - missing months
   - outlier
3. Run with `03_mixed_frequency.csv` → verify guardrail.
4. Run with `04_summary_only.csv` → verify hard reject.
5. Validate benchmark alignment using `benchmark_spy_monthly.csv` (offline mode).

## Open design decisions to document in README
- Dedupe policy: drop exact duplicates vs keep latest
- Missing month policy: warning vs exclusion
- Minimum history policy: e.g., ≥12 months required for ranking
- Outlier threshold: e.g., |return| > 25% flag
