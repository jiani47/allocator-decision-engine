# Equi MVP — Architecture & Implementation Plan

## Overview

Equi is a decision-structuring platform for fund-of-funds analysts. The MVP pipeline:

```
Upload CSV → Confirm Schema → Review Warnings → Normalize Universe
→ Configure Benchmark → Compute Metrics → Configure Mandate & Weights
→ Rank Shortlist → Generate Memo → Audit Claims → Export
```

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 3: Memo & Audit                          │
│  LLM memo from fact pack, claim extraction,     │
│  claim-to-evidence mapping, export              │
├─────────────────────────────────────────────────┤
│  Layer 2: Deterministic Decision Engine         │
│  Metric computation, constraint evaluation,     │
│  weighted ranking, DecisionRun creation         │
├─────────────────────────────────────────────────┤
│  Layer 1: Data Normalization                    │
│  Schema inference, column mapping, date/return  │
│  normalization, anomaly detection               │
└─────────────────────────────────────────────────┘
```

**Key invariant:** Deterministic core, generative edge. All financial calculations are pure functions. LLM only drafts narrative from structured JSON fact packs.

## Dependency Direction

```
ui.py → services.py → domains/ → core/
                     → llm/    → core/

Core never imports UI, API, domains, or LLM.
Domains never import API or UI.
LLM never computes metrics.
```

## Project Structure

```
app/
  __init__.py
  config.py                      # Settings via pydantic-settings
  services.py                    # Thin orchestration layer for UI
  ui.py                          # Streamlit 10-step wizard (thin, declarative)
  core/
    __init__.py
    exceptions.py                # Domain-specific exceptions
    schemas.py                   # All Pydantic v2 models
    hashing.py                   # Stable hash utilities
    decision_run.py              # Immutable DecisionRun assembly
    export.py                    # Markdown/JSON export
    metrics/
      __init__.py
      returns.py                 # annualized_return, annualized_volatility
      risk.py                    # sharpe_ratio, max_drawdown
      correlation.py             # benchmark_correlation
      compute.py                 # Orchestrator: compute all metrics per fund
    constraints/
      __init__.py
      base.py                    # BaseConstraint ABC
      liquidity.py               # MinLiquidityConstraint
      drawdown.py                # MaxDrawdownConstraint
      volatility.py              # TargetVolatilityConstraint
      strategy.py                # StrategyConstraint
    scoring/
      __init__.py
      normalize.py               # Min-max metric normalization
      ranking.py                 # Weighted scoring + ranking orchestrator
    evidence/
      __init__.py
      fact_pack.py               # FactPack builder + memo prompt
      audit.py                   # Claim-to-evidence mapping
  domains/
    __init__.py
    alt_invest/
      __init__.py
      ingest.py                  # CSV ingestion, schema inference, normalization
      adapter.py                 # Domain models → core engine primitives
      benchmark.py               # yfinance benchmark fetching + alignment
  llm/
    __init__.py
    anthropic_client.py          # Anthropic API wrapper with retries
    memo_service.py              # Fact pack → memo generation + validation
tests/
  __init__.py
  fixtures/                      # Synthetic CSV test data
  test_ingestion.py
  test_metrics.py
  test_benchmark.py
  test_constraints.py
  test_memo.py
  test_audit.py
  test_integration.py
```

## Data Flow & Pydantic Schemas

```
CSV bytes
  ↓ read_csv()
pd.DataFrame + ColumnMapping
  ↓ build_normalized_universe()
NormalizedUniverse
  ├── funds: list[NormalizedFund]
  │     └── monthly_returns: dict[str, float]  # "2022-01" → 0.023
  └── warnings: list[ValidationWarning]

NormalizedUniverse + BenchmarkSeries
  ↓ compute_all_metrics()
list[FundMetrics]
  └── metrics: dict[MetricId, float]

list[FundMetrics] + MandateConfig
  ↓ rank_universe()
list[ScoredFund]
  ├── composite_score, rank
  ├── constraint_results: list[ConstraintResult]
  └── normalized_scores: dict[MetricId, float]

list[ScoredFund] + metadata
  ↓ build_fact_pack()
FactPack
  ↓ generate_memo()
MemoOutput
  ├── memo_text: str
  └── claims: list[Claim]
       └── referenced_metric_ids, referenced_fund_names

Everything assembled into → DecisionRun (immutable)
```

## V1 Metrics

| Metric | Function | Formula |
|--------|----------|---------|
| Annualized Return | `annualized_return()` | `(∏(1 + rᵢ))^(12/n) - 1` |
| Annualized Volatility | `annualized_volatility()` | `σ(rᵢ) × √12` |
| Sharpe Ratio | `sharpe_ratio()` | `ann_return / ann_vol` (rf=0) |
| Max Drawdown | `max_drawdown()` | `min(cumulative_wealth / running_max - 1)` |
| Benchmark Correlation | `benchmark_correlation()` | `pearson_corr(fund, benchmark)` |

## V1 Mandate Model

```python
MandateConfig:
  min_liquidity_days: int | None
  max_drawdown_tolerance: float | None    # e.g., -0.20
  target_volatility: float | None
  strategy_include: list[str]
  strategy_exclude: list[str]
  weight_return: float = 0.4
  weight_sharpe: float = 0.4
  weight_drawdown_penalty: float = 0.2
```

## V1 Input Format

Single CSV, monthly return time series.

| Column | Required | Format |
|--------|----------|--------|
| fund_name | Yes | String |
| date | Yes | Monthly (various formats accepted) |
| monthly_return | Yes | Decimal or percentage string |
| strategy | No | String |
| liquidity_days | No | Integer |
| management_fee | No | Decimal |
| performance_fee | No | Decimal |

## Deployment

- **Platform:** Streamlit Community Cloud
- **State:** `st.session_state` (ephemeral, per-session)
- **Persistence:** None (JSON export for archival)
- **Entry point:** `app/ui.py`
- **Secrets:** Configured in Streamlit Cloud dashboard (TOML format)

## Implementation Milestones

### M0: Foundation
Config, exceptions, Pydantic schemas, hashing, package structure.

### M1: Ingestion & Normalization
CSV parsing, schema inference, date/return normalization, duplicate/outlier/missing-month detection, `NormalizedUniverse` output.

### M2: Metrics + Benchmark
5 pure metric functions, yfinance benchmark fetching, date alignment, correlation computation.

### M3: Constraints & Ranking
4 constraint classes (liquidity, drawdown, volatility, strategy), min-max normalization, weighted composite scoring, ranked shortlist.

### M4: Memo + Audit + Export
Fact pack construction, Anthropic client with retries, memo generation with Pydantic validation, claim-to-evidence mapping, Markdown/JSON export, immutable DecisionRun assembly.

### M5: Streamlit UI
services.py orchestration layer, 10-step wizard with sidebar progress, session state management, error handling.

## Design Decisions

1. **No DB layer** — `DecisionRun` is a Pydantic model in session state. JSON export for archival.
2. **`monthly_returns` as `dict[str, float]`** — period string keys ("2022-01") for Pydantic serialization; adapter converts to `pd.Series` for computation.
3. **Min-max normalization** for scoring. Drawdown inverted so less-negative = higher score.
4. **Fact pack is the LLM contract** — LLM never sees raw data, only precomputed `FactPack` JSON.
5. **Fail-closed memo validation** — invalid JSON or orphaned claim references raise `MemoGenerationError`.
6. **12-month minimum history** — funds below threshold flagged `insufficient_history`, excluded from ranking.
7. **Outlier threshold: |return| > 25%** — flagged as warnings, not removed.
8. **Deduplication: keep first occurrence** — warn about dropped duplicates.
