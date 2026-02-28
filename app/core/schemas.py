from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Metric version — bump when metric formulas change
# ---------------------------------------------------------------------------
METRIC_VERSION = "1.0.0"


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


# ---------------------------------------------------------------------------
# Per-metric result with lineage (aligned with tech spec MetricResult)
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """Single metric computation result with formula and lineage."""

    metric_id: MetricId
    value: float
    period_start: str
    period_end: str
    formula_text: str
    dependencies: list[MetricId] = Field(default_factory=list)


class FundMetrics(BaseModel):
    """Computed metrics for a single fund."""

    fund_name: str
    metric_results: list[MetricResult]
    date_range_start: str
    date_range_end: str
    month_count: int
    insufficient_history: bool = False

    def get_value(self, metric_id: MetricId) -> float | None:
        """Look up a single metric value by id."""
        for r in self.metric_results:
            if r.metric_id == metric_id:
                return r.value
        return None

    def get_result(self, metric_id: MetricId) -> MetricResult | None:
        """Look up the full MetricResult by id."""
        for r in self.metric_results:
            if r.metric_id == metric_id:
                return r
        return None

    def values_dict(self) -> dict[MetricId, float]:
        """Flat dict view for convenience (display, export)."""
        return {r.metric_id: r.value for r in self.metric_results}


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

    name: str = "Untitled Mandate"
    min_liquidity_days: int | None = None
    max_drawdown_tolerance: float | None = None  # e.g., -0.20 for 20% max DD
    target_volatility: float | None = None
    strategy_include: list[str] = Field(default_factory=list)
    strategy_exclude: list[str] = Field(default_factory=list)
    weights: dict[MetricId, float] = Field(
        default_factory=lambda: {
            MetricId.ANNUALIZED_RETURN: 0.4,
            MetricId.SHARPE_RATIO: 0.4,
            MetricId.MAX_DRAWDOWN: 0.2,
        }
    )


# ---------------------------------------------------------------------------
# Score breakdown (aligned with tech spec score_result.score_breakdown_json)
# ---------------------------------------------------------------------------


class ScoreComponent(BaseModel):
    """Breakdown of one metric's contribution to the composite score."""

    metric_id: MetricId
    raw_value: float
    normalized_value: float
    weight: float
    weighted_contribution: float  # = normalized_value * weight


class ScoredFund(BaseModel):
    """A fund with its composite score and constraint results."""

    fund_name: str
    metric_values: dict[MetricId, float]  # all raw metrics for display
    score_breakdown: list[ScoreComponent]
    composite_score: float
    rank: int
    constraint_results: list[ConstraintResult]
    all_constraints_passed: bool


# ---------------------------------------------------------------------------
# Run candidate tracking (aligned with tech spec run_candidate)
# ---------------------------------------------------------------------------


class RunCandidate(BaseModel):
    """Tracks whether a fund was included or excluded from ranking."""

    fund_name: str
    included: bool
    exclusion_reason: str | None = None


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
    metric_version: str
    universe: NormalizedUniverse
    benchmark: BenchmarkSeries | None = None
    mandate: MandateConfig
    all_fund_metrics: list[FundMetrics]
    run_candidates: list[RunCandidate]
    ranked_shortlist: list[ScoredFund]
    memo: MemoOutput | None = None
    fact_pack: FactPack | None = None
