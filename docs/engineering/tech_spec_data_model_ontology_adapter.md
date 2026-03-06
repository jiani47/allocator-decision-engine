# Tech Spec — Data Model Reference

All Pydantic models live in `app/core/schemas.py` (single source of truth). This document organizes them by pipeline stage.

---

## Ingestion

Models for raw file parsing and LLM-based fund extraction.

### `RowClassification` (Enum)
Row type classification: `HEADER`, `DATA`, `AGGREGATED`, `EMPTY`.

### `RawRow`
A single row from a raw file with classification.

| Field | Type | Description |
|-------|------|-------------|
| `row_index` | `int` | Position in original file |
| `cells` | `list[str \| None]` | Cell values |
| `classification` | `RowClassification` | Row type |

### `RawFileContext`
Raw parsed file context preserving maximum information for LLM extraction.

| Field | Type | Description |
|-------|------|-------------|
| `filename` | `str` | Original filename |
| `file_hash` | `str` | SHA-256 of file content |
| `headers` | `list[str]` | Header row values |
| `header_row_index` | `int` | Index of the header row |
| `data_rows` | `list[RawRow]` | Data rows |
| `aggregated_rows` | `list[RawRow]` | Summary/total rows (excluded from extraction) |
| `empty_rows` | `list[RawRow]` | Empty rows |
| `total_rows` | `int` | Total row count in file |

### `LLMExtractedFund`
A single fund extracted by the LLM from raw file context.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Extracted fund name |
| `strategy` | `str \| None` | Investment strategy |
| `liquidity_days` | `int \| None` | Liquidity terms in days |
| `management_fee` | `float \| None` | Management fee (decimal) |
| `performance_fee` | `float \| None` | Performance fee (decimal) |
| `monthly_returns` | `dict[str, float]` | `"YYYY-MM"` → decimal return |
| `source_row_indices` | `list[int]` | Rows this fund was extracted from |

### `LLMIngestionResult`
Structured result from LLM fund extraction.

| Field | Type | Description |
|-------|------|-------------|
| `funds` | `list[LLMExtractedFund]` | Extracted funds |
| `interpretation_notes` | `str` | LLM notes on how it interpreted the file |
| `ambiguities` | `list[str]` | Ambiguous aspects flagged by LLM |

---

## Normalization

Models for schema mapping, validation, and the canonical normalized universe.

### `ColumnMapping`
User-confirmed mapping from CSV columns to canonical fields.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Column name for fund name |
| `date` | `str` | Column name for date |
| `monthly_return` | `str` | Column name for monthly return |
| `strategy` | `str \| None` | Column name for strategy |
| `liquidity_days` | `str \| None` | Column name for liquidity |
| `management_fee` | `str \| None` | Column name for mgmt fee |
| `performance_fee` | `str \| None` | Column name for perf fee |

### `ValidationWarning`
A single validation warning from normalization.

| Field | Type | Description |
|-------|------|-------------|
| `category` | `str` | `"duplicate"`, `"missing_month"`, `"outlier"`, etc. |
| `fund_name` | `str \| None` | Affected fund (None if file-level) |
| `message` | `str` | Human-readable warning |
| `row_indices` | `list[int]` | Related source rows |
| `severity` | `str` | `"warning"` or `"error"` |

### `WarningResolution`
Analyst resolution for a validation warning.

| Field | Type | Description |
|-------|------|-------------|
| `category` | `str` | Warning category being resolved |
| `fund_name` | `str \| None` | Affected fund |
| `original_message` | `str` | Original warning message |
| `action` | `str` | `"ignored"` or `"acknowledged"` |
| `analyst_note` | `str` | Free-text analyst note |

### `NormalizedFund`
A single fund's normalized data.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `strategy` | `str \| None` | Strategy classification |
| `liquidity_days` | `int \| None` | Liquidity terms |
| `management_fee` | `float \| None` | Management fee |
| `performance_fee` | `float \| None` | Performance fee |
| `monthly_returns` | `dict[str, float]` | `"YYYY-MM"` → decimal return |
| `date_range_start` | `str` | Earliest period |
| `date_range_end` | `str` | Latest period |
| `month_count` | `int` | Number of months with data |
| `source_row_indices` | `list[int]` | Source rows from raw file |

### `NormalizedUniverse`
Canonical output of the normalization layer. This is the primary data structure passed to all downstream stages.

| Field | Type | Description |
|-------|------|-------------|
| `funds` | `list[NormalizedFund]` | All normalized funds |
| `warnings` | `list[ValidationWarning]` | Validation warnings |
| `source_file_hash` | `str` | SHA-256 of source file |
| `column_mapping` | `ColumnMapping \| None` | Column mapping (if deterministic) |
| `normalization_timestamp` | `str` | ISO timestamp |
| `ingestion_method` | `str` | `"deterministic"` or `"llm"` |
| `raw_context` | `RawFileContext \| None` | Preserved raw context |
| `llm_interpretation_notes` | `str \| None` | LLM notes (if LLM ingestion) |

---

## Metrics

Models for metric computation results.

### `MetricId` (Enum)
Identifier for each computed metric:
- `ANNUALIZED_RETURN`
- `ANNUALIZED_VOLATILITY`
- `SHARPE_RATIO`
- `MAX_DRAWDOWN`
- `BENCHMARK_CORRELATION`

### `MetricResult`
Single metric computation result with formula and lineage.

| Field | Type | Description |
|-------|------|-------------|
| `metric_id` | `MetricId` | Which metric |
| `value` | `float \| None` | Computed value (None if insufficient data) |
| `period_start` | `str` | Start of computation period |
| `period_end` | `str` | End of computation period |
| `formula_text` | `str` | Human-readable formula used |
| `dependencies` | `list[MetricId]` | Metrics this depends on |

### `FundMetrics`
Computed metrics for a single fund.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `metric_results` | `list[MetricResult]` | All computed metrics |
| `date_range_start` | `str` | Period start |
| `date_range_end` | `str` | Period end |
| `month_count` | `int` | Months of data |
| `insufficient_history` | `bool` | True if below minimum history |

Helper methods: `get_value(metric_id)`, `get_result(metric_id)`, `values_dict()`.

### `BenchmarkSeries`
Normalized benchmark return series.

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Ticker symbol (e.g., `"SPY"`) |
| `monthly_returns` | `dict[str, float]` | `"YYYY-MM"` → return |
| `source` | `str` | `"yfinance"` or `"csv_upload"` |

---

## Constraints

Models for mandate-based constraint evaluation.

### `ConstraintResult`
Result of a single constraint evaluation on a fund.

| Field | Type | Description |
|-------|------|-------------|
| `constraint_name` | `str` | Constraint identifier |
| `passed` | `bool` | Whether the fund passed |
| `explanation` | `str` | Human-readable explanation |
| `threshold` | `float \| None` | Configured threshold |
| `actual_value` | `float \| None` | Fund's actual value |

### `FundEligibility`
Mandate-based eligibility classification per fund.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `eligible` | `bool` | Passes all constraints |
| `failing_constraints` | `list[ConstraintResult]` | Failed constraints |

### `MandateConfig`
User-configured mandate for a decision run.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"Untitled Mandate"` | Mandate name |
| `min_liquidity_days` | `int \| None` | None | Minimum liquidity |
| `max_drawdown_tolerance` | `float \| None` | None | e.g., -0.20 for 20% |
| `target_volatility` | `float \| None` | None | Target vol |
| `min_annualized_return` | `float \| None` | None | e.g., 0.05 for 5% |
| `min_sharpe_ratio` | `float \| None` | None | e.g., 0.5 |
| `min_history_months` | `int` | 12 | Minimum data months |
| `weights` | `dict[MetricId, float]` | Return: 0.4, Sharpe: 0.4, DD: 0.2, Corr: 0.0 | Scoring weights |
| `shortlist_top_k` | `int` | 3 | Top N for memo |
| `strategy_include` | `list[str]` | [] | Allowed strategies |
| `strategy_exclude` | `list[str]` | [] | Excluded strategies |

### `RunCandidate`
Tracks whether a fund was included or excluded from ranking.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `included` | `bool` | Included in ranking |
| `exclusion_reason` | `str \| None` | Why excluded |

---

## Scoring

Models for weighted ranking output.

### `ScoreComponent`
Breakdown of one metric's contribution to the composite score.

| Field | Type | Description |
|-------|------|-------------|
| `metric_id` | `MetricId` | Which metric |
| `raw_value` | `float \| None` | Original metric value |
| `normalized_value` | `float` | Min-max normalized [0, 1] |
| `weight` | `float` | Weight from mandate |
| `weighted_contribution` | `float` | `normalized_value * weight` |

### `ScoredFund`
A fund with its composite score and constraint results.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `metric_values` | `dict[MetricId, float \| None]` | All raw metrics |
| `score_breakdown` | `list[ScoreComponent]` | Per-metric scoring |
| `composite_score` | `float` | Final weighted score |
| `rank` | `int` | Position in ranking |
| `constraint_results` | `list[ConstraintResult]` | Constraint evaluations |
| `all_constraints_passed` | `bool` | All constraints passed |

---

## Grouping

Models for fund grouping (e.g., by strategy) with per-group benchmarks.

### `GroupingCriteria`
User-provided criteria for LLM fund grouping.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `standard_criteria` | `list[str]` | [] | Predefined criteria |
| `free_text` | `str` | `""` | Free-text grouping instruction |
| `max_groups` | `int` | 2 | Maximum number of groups |

### `FundGroup`
A group of funds with its own benchmark.

| Field | Type | Description |
|-------|------|-------------|
| `group_name` | `str` | Group display name |
| `group_id` | `str` | Unique group identifier |
| `fund_names` | `list[str]` | Funds in this group |
| `benchmark_symbol` | `str \| None` | Per-group benchmark ticker |
| `benchmark` | `BenchmarkSeries \| None` | Fetched benchmark data |
| `grouping_rationale` | `str` | Why these funds are grouped |

### `LLMGroupingResult`
Structured result from LLM fund grouping.

| Field | Type | Description |
|-------|------|-------------|
| `groups` | `list[FundGroup]` | Identified groups |
| `rationale` | `str` | Overall grouping rationale |
| `ambiguities` | `list[str]` | Ambiguous aspects |

### `GroupRun`
Per-group ranking, metrics, and memo. This is the primary unit for the ranking and memo stages.

| Field | Type | Description |
|-------|------|-------------|
| `group` | `FundGroup` | Group definition |
| `fund_metrics` | `list[FundMetrics]` | Metrics for group's funds |
| `ranked_shortlist` | `list[ScoredFund]` | Ranked funds |
| `run_candidates` | `list[RunCandidate]` | Inclusion/exclusion tracking |
| `memo` | `MemoOutput \| None` | Generated memo |
| `fact_pack` | `FactPack \| None` | Fact pack used for memo |
| `llm_rerank` | `LLMReRankResult \| None` | Re-ranking result |

---

## Re-ranking

Models for LLM-based qualitative re-ranking overlay.

### `ReRankRationale`
LLM rationale for a single fund's re-ranked position.

| Field | Type | Description |
|-------|------|-------------|
| `fund_name` | `str` | Fund name |
| `llm_rank` | `int` | LLM-assigned rank |
| `deterministic_rank` | `int` | Original deterministic rank |
| `rationale` | `str` | 2-4 sentence explanation |
| `key_factors` | `list[str]` | e.g., `["low_fees", "strategy_fit"]` |
| `referenced_metric_ids` | `list[MetricId]` | Metrics referenced in rationale |

### `LLMReRankResult`
Structured result from LLM re-ranking.

| Field | Type | Description |
|-------|------|-------------|
| `reranked_funds` | `list[ReRankRationale]` | Per-fund rationales |
| `overall_commentary` | `str` | 1-2 paragraph summary |
| `model_used` | `str` | LLM model identifier |

---

## Memo

Models for memo generation and claim-based audit.

### `FactPack`
Deterministic fact pack fed to LLM for memo generation. The LLM must only reference data present in this structure.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique run identifier |
| `shortlist` | `list[ScoredFund]` | Ranked funds for memo |
| `universe_summary` | `dict` | Universe statistics |
| `mandate` | `MandateConfig` | Active mandate |
| `benchmark_symbol` | `str` | Benchmark ticker |
| `analyst_notes` | `list[WarningResolution]` | Analyst warning resolutions |
| `instructions` | `dict` | LLM guardrails (no_new_numbers, etc.) |
| `group_name` | `str` | Group name (if per-group) |
| `group_rationale` | `str` | Group rationale |
| `ai_rationales` | `list[ReRankRationale]` | Re-rank rationales (if adopted) |

### `MemoOutput`
Structured output from LLM memo generation.

| Field | Type | Description |
|-------|------|-------------|
| `memo_text` | `str` | Full memo markdown |
| `claims` | `list[Claim]` | Extracted verifiable claims |

### `Claim`
A single claim extracted from an LLM-generated memo.

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | `str` | Unique claim identifier |
| `claim_text` | `str` | The factual assertion |
| `source_text` | `str` | Verbatim sentence from memo (for text matching) |
| `referenced_metric_ids` | `list[MetricId]` | Metrics backing this claim |
| `referenced_fund_names` | `list[str]` | Funds mentioned |

The `source_text` field is critical for citation badges — the frontend uses it to locate and annotate the exact sentence in the rendered memo.

---

## Decision

### `DecisionRun`
Immutable record of a complete decision run. Top-level output of the entire pipeline.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique run identifier |
| `input_hash` | `str` | Hash of inputs for reproducibility |
| `timestamp` | `str` | ISO timestamp |
| `metric_version` | `str` | Version of metric formulas |
| `universe` | `NormalizedUniverse` | Full normalized universe |
| `benchmark` | `BenchmarkSeries \| None` | Benchmark data |
| `mandate` | `MandateConfig` | Mandate configuration |
| `all_fund_metrics` | `list[FundMetrics]` | All computed metrics |
| `run_candidates` | `list[RunCandidate]` | Inclusion tracking |
| `ranked_shortlist` | `list[ScoredFund]` | Final ranked funds |
| `memo` | `MemoOutput \| None` | Generated memo |
| `fact_pack` | `FactPack \| None` | Fact pack used |
| `fund_eligibility` | `list[FundEligibility]` | Eligibility results |
| `group_runs` | `list[GroupRun]` | Per-group results |

---

## Constants

- `METRIC_VERSION = "1.0.0"` — Bumped when metric formulas change. Stored in `DecisionRun` for reproducibility.

---

## Adapter Pattern

The domain layer (`app/domains/alt_invest/`) bridges external data formats to core engine models:

- `raw_parser.py` — Raw file bytes → `RawFileContext`
- `ingest.py` — `LLMIngestionResult` → `NormalizedUniverse`
- `benchmark.py` — yfinance data → `BenchmarkSeries`
- `adapter.py` — Domain-specific transformations

The core engine (`app/core/`) operates only on its own Pydantic models and never imports domain or LLM modules.

## Frontend Type Mirroring

TypeScript types in `frontend/src/context/WizardContext.tsx` mirror the Python Pydantic models above. Key convention:

- Python `snake_case` fields map to TypeScript `snake_case` (no camelCase conversion — JSON serialization preserves field names)
- Python `Enum` types become TypeScript string union types
- `openapi-typescript` codegen (`npm run codegen`) generates API request/response types from the FastAPI OpenAPI spec
