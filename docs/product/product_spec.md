# Equi — Product Spec

## Product Goal

Turn messy manager performance data into normalized, validated, ranked, and traceable investment decisions — without manual spreadsheet editing.

## Primary User

Investment analyst at a fund-of-funds or RIA who owns data preprocessing, metric computation, and IC memo drafting.

## Current Capabilities

- **LLM-powered ingestion** — Upload any CSV/Excel format; Claude extracts fund names, dates, returns, and metadata from arbitrary layouts
- **Validation & warnings** — Automated detection of duplicates, missing months, outlier returns, with analyst resolution workflow
- **Deterministic metrics** — Annualized return, volatility, Sharpe ratio, max drawdown, benchmark correlation
- **Mandate constraints** — Configurable thresholds (liquidity, drawdown, volatility, return, Sharpe, history) with strategy include/exclude
- **Weighted ranking** — Composite scoring with analyst-configured metric weights
- **Fund grouping** — Per-group benchmarks and independent rankings
- **LLM re-ranking** — Optional qualitative overlay with per-fund rationales
- **Streaming memos** — Real-time IC memo generation via SSE with two-phase approach (text + claims)
- **Citation badges** — Inline claim annotations linking memo sentences to underlying metrics
- **Export** — Excel spreadsheet with ranked metrics, PDF memo, JSON decision record

## User Workflow

The React frontend implements a 4-step wizard:

### Step 1: Configure Mandate
- Set hard constraints (min liquidity, max drawdown, target volatility, min return, min Sharpe)
- Configure metric weights for composite scoring
- Set strategy include/exclude filters
- Choose shortlist size (top K for memo)

### Step 2: Upload & Review
- Drag-and-drop CSV/Excel upload
- LLM extracts fund data — analyst reviews interpretation
- Review validation warnings (duplicates, gaps, outliers)
- Dismiss or acknowledge warnings with notes
- View fund eligibility against mandate constraints

### Step 3: Metrics & Ranking
- Select benchmark ticker (default: SPY, fetched from Yahoo Finance)
- View computed metrics for all funds with score breakdowns
- Review ranked shortlist with constraint pass/fail indicators
- Optionally trigger LLM re-ranking for qualitative judgment
- Compare deterministic vs. AI rankings side-by-side

### Step 4: Memo & Export
- Stream IC memo generation in real-time
- View inline citation badges linking claims to evidence
- Click badges to see evidence popovers with metric values
- Export ranked data as Excel spreadsheet
- Export memo as PDF

## Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| Annualized Return | `(prod(1 + ri))^(12/n) - 1` | Geometric compounding |
| Annualized Volatility | `std(ri) * sqrt(12)` | Monthly std annualized |
| Sharpe Ratio | `ann_return / ann_vol` | Risk-free rate = 0 |
| Max Drawdown | `min(cumulative_wealth / running_max - 1)` | Peak-to-trough |
| Benchmark Correlation | `pearson_corr(fund, benchmark)` | Aligned monthly periods |

## Constraints

Each constraint is an independent pass/fail evaluation with explanation:

- **Min liquidity days** — Fund must have liquidity terms ≥ threshold
- **Max drawdown tolerance** — Fund's max drawdown must not exceed limit (e.g., -20%)
- **Target volatility** — Fund's annualized vol must not exceed target
- **Min annualized return** — Fund must meet minimum return threshold
- **Min Sharpe ratio** — Fund must meet minimum risk-adjusted return
- **Min history months** — Fund must have at least N months of data (default: 12)
- **Strategy filters** — Include/exclude lists for strategy classification

Funds failing constraints are marked ineligible but remain visible in the UI.

## Benchmark

- Single benchmark per group, fetched from Yahoo Finance via yfinance
- Aligned to universe date range (intersection of available periods)
- Default: SPY
- Benchmark metrics displayed alongside fund metrics for comparison

## Memo Generation

Two-phase approach:

1. **Streaming** — Fact pack assembled from precomputed metrics → streamed to UI via SSE
2. **Claims extraction** — Structured claims parsed from completed memo, each with `source_text` for citation matching

Guardrails enforced via fact pack:
- No numbers that don't appear in the fact pack
- All claims must reference metric IDs
- All claims must be traceable to evidence

## Re-ranking

Optional LLM overlay on deterministic rankings:
- LLM receives full context: metrics, fees, strategy, warnings, benchmark
- Returns per-fund rationale with key factors
- Analyst can adopt AI ranking or keep deterministic order
- If adopted, memo generation uses AI-ranked order

## Input Format

Single CSV or Excel file with monthly return time series per fund. The LLM handles arbitrary layouts — no fixed column requirements. Extracted fields:

| Field | Required | Description |
|-------|----------|-------------|
| Fund name | Yes | Manager/fund identifier |
| Date | Yes | Monthly period |
| Monthly return | Yes | Decimal or percentage |
| Strategy | No | Investment strategy classification |
| Liquidity days | No | Redemption terms |
| Management fee | No | Annual management fee |
| Performance fee | No | Performance/incentive fee |

## Explicit Non-Goals

- Multi-user collaboration or enterprise auth
- Automated vendor data ingestion (API feeds)
- Real-time portfolio tracking or monitoring
- Capital allocation execution or trade generation
- Advanced ML models (factor models, regime detection)
- Rolling/windowed metrics
- VaR/CVaR or other advanced risk measures
- Database persistence across sessions
