from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Row classification for raw file parsing
# ---------------------------------------------------------------------------


class RowClassification(str, Enum):
    HEADER = "header"
    DATA = "data"
    AGGREGATED = "aggregated"
    EMPTY = "empty"


class RawRow(BaseModel):
    """A single row from a raw file with classification."""

    row_index: int
    cells: list[str | None]
    classification: RowClassification


class RawFileContext(BaseModel):
    """Raw parsed file context preserving maximum information."""

    filename: str
    file_hash: str
    headers: list[str]
    header_row_index: int
    data_rows: list[RawRow]
    aggregated_rows: list[RawRow] = Field(default_factory=list)
    empty_rows: list[RawRow] = Field(default_factory=list)
    total_rows: int


class LLMExtractedFund(BaseModel):
    """A single fund extracted by the LLM from raw file context."""

    fund_name: str
    strategy: str | None = None
    liquidity_days: int | None = None
    management_fee: float | None = None
    performance_fee: float | None = None
    monthly_returns: dict[str, float]  # "YYYY-MM" -> decimal return
    source_row_indices: list[int] = Field(default_factory=list)


class LLMIngestionResult(BaseModel):
    """Structured result from LLM fund extraction."""

    funds: list[LLMExtractedFund]
    interpretation_notes: str = ""
    ambiguities: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Metric version — bump when metric formulas change
# ---------------------------------------------------------------------------
METRIC_VERSION = "1.1.0"


class ColumnMapping(BaseModel):
    """User-confirmed mapping from CSV columns to canonical fields."""

    fund_name: str
    date: str
    monthly_return: str
    strategy: str | None = None
    liquidity_days: str | None = None
    management_fee: str | None = None
    performance_fee: str | None = None


class WarningResolution(BaseModel):
    """Analyst resolution for a validation warning."""

    category: str  # "duplicate", "missing_month", "outlier"
    fund_name: str | None = None
    original_message: str
    action: str  # "ignored" | "acknowledged"
    analyst_note: str = ""


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
    source_row_indices: list[int] = Field(default_factory=list)


class NormalizedUniverse(BaseModel):
    """Canonical output of the normalization layer."""

    funds: list[NormalizedFund]
    warnings: list[ValidationWarning] = Field(default_factory=list)
    source_file_hash: str
    column_mapping: ColumnMapping | None = None
    normalization_timestamp: str
    ingestion_method: str = "deterministic"  # "deterministic" | "llm"
    raw_context: RawFileContext | None = None
    llm_interpretation_notes: str | None = None


class MetricId(str, Enum):
    ANNUALIZED_RETURN = "annualized_return"
    ANNUALIZED_VOLATILITY = "annualized_volatility"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    BENCHMARK_CORRELATION = "benchmark_correlation"
    PORTFOLIO_DIVERSIFICATION = "portfolio_diversification"


# ---------------------------------------------------------------------------
# Per-metric result with lineage (aligned with tech spec MetricResult)
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """Single metric computation result with formula and lineage."""

    metric_id: MetricId
    value: float | None = None
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


class PortfolioHolding(BaseModel):
    """A single holding in the existing portfolio."""

    fund_name: str
    weight: float  # allocation weight, should sum to ~1.0 across holdings
    monthly_returns: dict[str, float]  # "YYYY-MM" -> decimal return


class ExistingPortfolio(BaseModel):
    """Existing fund-of-funds portfolio for diversification analysis."""

    holdings: list[PortfolioHolding]
    name: str = "Existing Portfolio"


class PortfolioContext(BaseModel):
    """Portfolio context for memo generation (governance + holdings summary)."""

    portfolio_name: str
    strategy: str
    aum: float | None = None
    holdings: list[dict] = Field(default_factory=list)  # [{fund_name, strategy, weight}]
    governance: dict = Field(default_factory=dict)  # governance mandate floors

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
    min_annualized_return: float | None = None  # e.g., 0.05 for 5%
    min_sharpe_ratio: float | None = None  # e.g., 0.5
    min_history_months: int = 12
    weights: dict[MetricId, float] = Field(
        default_factory=lambda: {
            MetricId.ANNUALIZED_RETURN: 0.4,
            MetricId.SHARPE_RATIO: 0.4,
            MetricId.MAX_DRAWDOWN: 0.2,
            MetricId.BENCHMARK_CORRELATION: 0.0,
            MetricId.PORTFOLIO_DIVERSIFICATION: 0.0,
        }
    )
    shortlist_top_k: int = 3  # Top N funds included in memo
    strategy_include: list[str] = Field(default_factory=list)
    strategy_exclude: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Score breakdown (aligned with tech spec score_result.score_breakdown_json)
# ---------------------------------------------------------------------------


class ScoreComponent(BaseModel):
    """Breakdown of one metric's contribution to the composite score."""

    metric_id: MetricId
    raw_value: float | None = None
    normalized_value: float
    weight: float
    weighted_contribution: float  # = normalized_value * weight


class ScoredFund(BaseModel):
    """A fund with its composite score and constraint results."""

    fund_name: str
    metric_values: dict[MetricId, float | None]  # all raw metrics for display
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


class FundEligibility(BaseModel):
    """Mandate-based eligibility classification per fund."""

    fund_name: str
    eligible: bool
    failing_constraints: list[ConstraintResult] = Field(default_factory=list)


class GroupingCriteria(BaseModel):
    """User-provided criteria for LLM fund grouping."""

    standard_criteria: list[str] = Field(default_factory=list)
    free_text: str = ""
    max_groups: int = 2


class FundGroup(BaseModel):
    """A group of funds with its own benchmark."""

    group_name: str
    group_id: str
    fund_names: list[str]
    benchmark_symbol: str | None = None
    benchmark: BenchmarkSeries | None = None
    grouping_rationale: str = ""


class Claim(BaseModel):
    """A single claim extracted from an LLM-generated memo."""

    claim_id: str
    claim_text: str
    source_text: str = ""  # Verbatim sentence from the memo for text matching
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
    analyst_notes: list[WarningResolution] = Field(default_factory=list)
    instructions: dict = Field(
        default_factory=lambda: {
            "no_new_numbers": True,
            "all_claims_require_evidence": True,
            "reference_metric_ids": True,
        }
    )
    group_name: str = ""
    group_rationale: str = ""
    ai_rationales: list["ReRankRationale"] = Field(default_factory=list)
    portfolio_context: PortfolioContext | None = None


class ReRankRationale(BaseModel):
    """LLM rationale for a single fund's re-ranked position."""

    fund_name: str
    llm_rank: int
    deterministic_rank: int
    rationale: str  # 2-4 sentence explanation
    key_factors: list[str]  # e.g., ["low_fees", "strategy_fit"]
    referenced_metric_ids: list[MetricId]


class LLMReRankResult(BaseModel):
    """Structured result from LLM re-ranking."""

    reranked_funds: list[ReRankRationale]
    overall_commentary: str  # 1-2 paragraph summary
    model_used: str


class GroupRun(BaseModel):
    """Per-group ranking, metrics, and memo."""

    group: FundGroup
    fund_metrics: list[FundMetrics]
    ranked_shortlist: list[ScoredFund]
    run_candidates: list[RunCandidate]
    memo: MemoOutput | None = None
    fact_pack: FactPack | None = None
    llm_rerank: LLMReRankResult | None = None


class LLMGroupingResult(BaseModel):
    """Structured result from LLM fund grouping."""

    groups: list[FundGroup]
    rationale: str
    ambiguities: list[str] = Field(default_factory=list)


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
    fund_eligibility: list[FundEligibility] = Field(default_factory=list)
    group_runs: list[GroupRun] = Field(default_factory=list)


# Rebuild forward references (FactPack references ReRankRationale defined after it)
FactPack.model_rebuild()
