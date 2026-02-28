
# Allocator Decision Engine – Tightened MVP Definition
## Analyst Workflow (Fund-of-Funds Focus)

---

# 1. MVP Philosophy

Version 1 focuses on:

- Efficiency in preprocessing
- Deterministic, reproducible evaluation
- Minimal but strict auditability
- Narrow surface area

We explicitly avoid building a broad analytics suite.

---

# 2. Canonical Input Definition (V1 Constraint)

## Supported Input

We support only:

- A single CSV file
- Monthly return time series per fund

Required Columns (after mapping):

- fund_name
- date (monthly frequency)
- monthly_return (percentage or decimal)

Optional Columns:

- strategy
- liquidity_days
- management_fee
- performance_fee

We do NOT support:

- Summary-only statistics files
- Multi-asset files in same run
- Mixed frequency data
- Multi-currency handling
- Automated vendor ingestion

---

# 3. Upstream Assumption

The input file is typically:

- Manager performance export
- Portfolio admin CSV
- Email attachment from GP
- CRM export

V1 assumes manual upload.

---

# 4. Data Normalization Scope (V1)

The system must:

- Infer likely schema
- Allow user to confirm column mapping
- Normalize date formats
- Normalize return formats (% vs decimal)
- Detect missing months
- Detect duplicate records
- Detect extreme outliers
- Align date ranges across funds
- Produce canonical NormalizedUniverse object

We do NOT:

- Build auto-healing reconciliation
- Perform complex statistical cleaning
- Infer multi-table relationships

---

# 5. Metrics Included in V1

The deterministic metric engine computes:

1. Annualized Return
2. Annualized Volatility
3. Sharpe Ratio (risk-free = 0 for V1)
4. Maximum Drawdown
5. Correlation to Benchmark

Optional if trivial:

6. Downside Deviation
7. Sortino Ratio

Excluded:

- Rolling metrics
- Factor models
- VaR / CVaR
- Regime detection
- Multi-benchmark comparison

---

# 6. Benchmark Integration (V1)

Supported:

- Single benchmark per run
- Fetched from public API (Yahoo Finance / FRED)
- Monthly adjusted close converted to returns
- Date-aligned to fund series

We do NOT:

- Maintain historical benchmark database
- Support multiple benchmarks per run
- Handle complex frequency conversions

---

# 7. Mandate Form (V1 Constraint Model)

Single mandate object with:

- Minimum liquidity (days)
- Max drawdown tolerance (%)
- Target volatility (%)
- Strategy include list
- Strategy exclude list
- Weight sliders:
    - Return weight
    - Sharpe weight
    - Drawdown penalty weight

We do NOT:

- Support nested constraint logic
- Allow multiple mandates per run
- Perform portfolio optimization

---

# 8. Ranking Logic (V1)

- Normalize metric scores
- Apply weight configuration
- Penalize constraint violations
- Produce ranked shortlist

No ML models.
No adaptive scoring.
No optimization solver.

---

# 9. Memo + Audit Scope (V1)

Memo:

- Generated from deterministic fact pack
- Structured IC-style format
- Claims must reference metric IDs

Audit View:

Click a claim → display:

- Metric referenced
- Formula description
- Computed value
- Date range used
- Raw data rows used
- Benchmark alignment rows (if applicable)

We do NOT:

- Visualize full lineage DAG
- Implement graph database
- Provide advanced drill-down analytics

---

# 10. Data Lineage (V1 Minimal Definition)

For each DecisionRun store:

- Universe file hash
- Normalization mapping
- Metric version
- Benchmark ID + date range
- Mandate configuration
- Scoring weights
- LLM prompt version
- Timestamp

For each Metric:

- Fund ID
- Date range
- Formula description

For each Claim:

- Claim text
- Referenced metric IDs
- Referenced fund IDs

---

# 11. Explicit Non-Goals

V1 is NOT:

- A full analytics suite
- A portfolio management system
- A capital allocation optimizer
- A multi-user enterprise product
- A DDQ automation platform
- A robo advisor

---

# 12. Final MVP Definition

Upload → Normalize → Validate → Apply Mandate → Rank → Draft Memo → Audit Claims → Export

Nothing beyond this is required for V1.
