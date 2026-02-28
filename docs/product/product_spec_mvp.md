# Allocator Decision Engine — MVP Product Spec
## Analyst Workflow (Fund-of-Funds Focus)

---

## 1. Product Goal & Philosophy

Turn messy manager data into a normalized, validated, and defendable investment decision workflow.

V1 focuses on:

- Efficiency in preprocessing
- Deterministic, reproducible evaluation
- Minimal but strict auditability
- Narrow surface area

We explicitly avoid building a broad analytics suite.

---

## 2. Success Metrics

MVP is successful when:

1. Analyst can upload a messy CSV and normalize it within 5 minutes.
2. No manual spreadsheet editing is required post-upload.
3. Deterministic metrics are generated consistently.
4. Memo claims can be traced to raw data rows.
5. Analyst voluntarily reuses tool for subsequent evaluation cycles.

---

## 3. Scope

Included:

- CSV ingestion
- Schema inference + mapping confirmation
- Data validation warnings
- Canonical normalization
- Deterministic metrics
- Constraint engine
- Ranking logic
- IC memo draft
- Claim-evidence audit view
- Exportable memo
- Immutable DecisionRun record

Out of Scope:

- Multi-user collaboration
- Enterprise auth / RBAC
- Automated vendor ingestion
- Real-time portfolio tracking
- Capital allocation execution
- Advanced ML scoring
- External CRM integration

---

## 4. User Workflow

### Current Workflow

Manager CSV → Excel cleanup → Excel metrics → Word memo → IC review

### New Workflow (With Product)

1. Upload CSV
2. Confirm schema mapping
3. Review validation warnings
4. Normalize universe
5. Configure constraints + weights
6. Run decision engine
7. Review shortlist + metrics
8. Generate memo
9. Audit claims
10. Export memo + archive run

### Integration Point

The product integrates at:

- Data preprocessing
- Metric computation
- IC memo drafting layer

It does not replace:

- Portfolio accounting systems
- CRM systems
- Market data providers

---

## 5. Canonical Input Definition

### Supported Input

We support only:

- A single CSV file
- Monthly return time series per fund

Required columns (after mapping):

- `fund_name`
- `date` (monthly frequency)
- `monthly_return` (percentage or decimal)

Optional columns:

- `strategy`
- `liquidity_days`
- `management_fee`
- `performance_fee`

### Upstream Assumption

The input file is typically:

- Manager performance export
- Portfolio admin CSV
- Email attachment from GP
- CRM export

V1 assumes manual upload.

### We do NOT support:

- Summary-only statistics files
- Multi-asset files in same run
- Mixed frequency data
- Multi-currency handling
- Automated vendor ingestion

---

## 6. Data Normalization Scope

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

## 7. Metrics

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

## 8. Benchmark Integration

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

## 9. Mandate (Constraint Model)

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

## 10. Ranking Logic

- Normalize metric scores
- Apply weight configuration
- Penalize constraint violations
- Produce ranked shortlist

No ML models. No adaptive scoring. No optimization solver.

---

## 11. Memo + Audit

### Memo

- Generated from deterministic fact pack
- Structured IC-style format
- Claims must reference metric IDs

### Audit View

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

## 12. Data Lineage (Minimal)

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

## 13. Product Architecture

### Layer 1 — Data Normalization

- Schema inference, mapping validation, data cleaning
- Missing value handling, anomaly detection
- Output: `NormalizedUniverse`

### Layer 2 — Deterministic Decision Engine

- Metric computation, constraint evaluation, weighted ranking
- Output: Structured fact pack + `DecisionRun`

### Layer 3 — Memo & Audit

- Memo drafting via LLM, claim extraction, claim-to-evidence mapping
- Output: Defendable IC memo + audit graph

### Design Principles

- Deterministic core, generative edge
- Immutable decision runs
- Clear separation of normalization and evaluation layers
- Auditability by default

---

## 14. MVP Milestones

### Milestone 1 — Ingestion & Normalization

CSV upload, column inference, user mapping confirmation, date/return normalization, missing data + anomaly detection, canonical NormalizedUniverse.

### Milestone 2 — Deterministic Metric Engine

Annualized return, volatility, Sharpe ratio, max drawdown, benchmark correlation.

### Milestone 3 — Constraint & Ranking Layer

Liquidity constraint, max drawdown threshold, strategy exclusion, weighted ranking.

### Milestone 4 — Memo + Claim Structuring

Generate memo from fact pack, extract structured claims, enforce claim-to-metric linkage.

### Milestone 5 — Audit View + Export

Claim → metric → raw data mapping view, DecisionRun storage, export to Markdown / JSON.

---

## 15. Explicit Non-Goals

V1 is NOT:

- A full analytics suite
- A portfolio management system
- A capital allocation optimizer
- A multi-user enterprise product
- A DDQ automation platform
- A robo advisor

---

## 16. Final MVP Definition

Upload → Normalize → Validate → Apply Mandate → Rank → Draft Memo → Audit Claims → Export

Nothing beyond this is required for V1.
