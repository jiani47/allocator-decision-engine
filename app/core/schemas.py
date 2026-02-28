from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ColumnMapping(BaseModel):
    """User-confirmed mapping from CSV columns to canonical fields."""

    fund_name: str
    date: str
    monthly_return: str
    strategy: str | None = None
    liquidity_days: str | None = None
    management_fee: str | None = None
    performance_fee: str | None = None


class ValidationWarning(BaseModel):
    """A single validation warning from normalization."""

    category: str  # "duplicate", "missing_month", "outlier", etc.
    fund_name: str | None = None
    message: str
    row_indices: list[int] = Field(default_factory=list)
    severity: str = "warning"  # "warning" | "error"


class NormalizedFund(BaseModel):
    """A single fund's normalized data."""

    fund_name: str
    strategy: str | None = None
    liquidity_days: int | None = None
    management_fee: float | None = None
    performance_fee: float | None = None
    monthly_returns: dict[str, float]  # period "2022-01" -> return as decimal
    date_range_start: str
    date_range_end: str
    month_count: int


class NormalizedUniverse(BaseModel):
    """Canonical output of the normalization layer."""

    funds: list[NormalizedFund]
    warnings: list[ValidationWarning] = Field(default_factory=list)
    source_file_hash: str
    column_mapping: ColumnMapping
    normalization_timestamp: str


class MetricId(str, Enum):
    ANNUALIZED_RETURN = "annualized_return"
    ANNUALIZED_VOLATILITY = "annualized_volatility"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    BENCHMARK_CORRELATION = "benchmark_correlation"


class FundMetrics(BaseModel):
    """Computed metrics for a single fund."""

    fund_name: str
    metrics: dict[MetricId, float]
    date_range_start: str
    date_range_end: str
    month_count: int
    insufficient_history: bool = False


class BenchmarkSeries(BaseModel):
    """Normalized benchmark return series."""

    symbol: str
    monthly_returns: dict[str, float]  # period "2022-01" -> return
    source: str  # "yfinance" or "csv_upload"


class ConstraintResult(BaseModel):
    """Result of a single constraint evaluation on a fund."""

    constraint_name: str
    passed: bool
    explanation: str
    threshold: float | None = None
    actual_value: float | None = None


class MandateConfig(BaseModel):
    """User-configured mandate for a decision run."""

    min_liquidity_days: int | None = None
    max_drawdown_tolerance: float | None = None  # e.g., -0.20 for 20% max DD
    target_volatility: float | None = None
    strategy_include: list[str] = Field(default_factory=list)
    strategy_exclude: list[str] = Field(default_factory=list)
    weight_return: float = 0.4
    weight_sharpe: float = 0.4
    weight_drawdown_penalty: float = 0.2


class ScoredFund(BaseModel):
    """A fund with its composite score and constraint results."""

    fund_name: str
    metrics: dict[MetricId, float]
    normalized_scores: dict[MetricId, float]
    composite_score: float
    rank: int
    constraint_results: list[ConstraintResult]
    all_constraints_passed: bool


class Claim(BaseModel):
    """A single claim extracted from an LLM-generated memo."""

    claim_id: str
    claim_text: str
    referenced_metric_ids: list[MetricId]
    referenced_fund_names: list[str]


class MemoOutput(BaseModel):
    """Structured output from LLM memo generation."""

    memo_text: str
    claims: list[Claim]


class FactPack(BaseModel):
    """Deterministic fact pack fed to LLM for memo generation."""

    run_id: str
    shortlist: list[ScoredFund]
    universe_summary: dict
    mandate: MandateConfig
    benchmark_symbol: str
    instructions: dict = Field(
        default_factory=lambda: {
            "no_new_numbers": True,
            "all_claims_require_evidence": True,
            "reference_metric_ids": True,
        }
    )


class DecisionRun(BaseModel):
    """Immutable record of a complete decision run."""

    run_id: str
    input_hash: str
    timestamp: str
    universe: NormalizedUniverse
    benchmark: BenchmarkSeries | None = None
    mandate: MandateConfig
    all_fund_metrics: list[FundMetrics]
    ranked_shortlist: list[ScoredFund]
    memo: MemoOutput | None = None
    fact_pack: FactPack | None = None
