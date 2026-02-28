"""Orchestrator: compute all V1 metrics for a fund or universe."""

from __future__ import annotations

import logging

import pandas as pd

from app.core.schemas import (
    BenchmarkSeries,
    FundMetrics,
    MetricId,
    MetricResult,
    NormalizedFund,
)
from app.core.metrics.correlation import benchmark_correlation
from app.core.metrics.returns import annualized_return, annualized_volatility
from app.core.metrics.risk import max_drawdown, sharpe_ratio
from app.domains.alt_invest.adapter import fund_to_return_series

logger = logging.getLogger("equi.metrics")

# ---------------------------------------------------------------------------
# Formula descriptions and dependency graph (used for MetricResult lineage)
# ---------------------------------------------------------------------------

METRIC_FORMULAS: dict[MetricId, str] = {
    MetricId.ANNUALIZED_RETURN: "(product(1 + r_i))^(12/n) - 1",
    MetricId.ANNUALIZED_VOLATILITY: "std(r_i) * sqrt(12)",
    MetricId.SHARPE_RATIO: "annualized_return / annualized_volatility (rf=0)",
    MetricId.MAX_DRAWDOWN: "min(cumulative_wealth / running_max - 1)",
    MetricId.BENCHMARK_CORRELATION: "pearson_corr(fund_returns, benchmark_returns)",
}

METRIC_DEPENDENCIES: dict[MetricId, list[MetricId]] = {
    MetricId.ANNUALIZED_RETURN: [],
    MetricId.ANNUALIZED_VOLATILITY: [],
    MetricId.SHARPE_RATIO: [MetricId.ANNUALIZED_RETURN, MetricId.ANNUALIZED_VOLATILITY],
    MetricId.MAX_DRAWDOWN: [],
    MetricId.BENCHMARK_CORRELATION: [],
}


def _benchmark_to_series(benchmark: BenchmarkSeries) -> pd.Series:
    """Convert BenchmarkSeries to pd.Series with PeriodIndex."""
    series = pd.Series(benchmark.monthly_returns, dtype=float)
    series.index = pd.PeriodIndex(series.index, freq="M")
    return series.sort_index()


def _make_result(
    metric_id: MetricId,
    value: float,
    period_start: str,
    period_end: str,
) -> MetricResult:
    """Build a MetricResult with formula and dependency metadata."""
    return MetricResult(
        metric_id=metric_id,
        value=value,
        period_start=period_start,
        period_end=period_end,
        formula_text=METRIC_FORMULAS[metric_id],
        dependencies=METRIC_DEPENDENCIES[metric_id],
    )


def compute_fund_metrics(
    fund: NormalizedFund,
    benchmark: BenchmarkSeries | None = None,
    min_history_months: int = 12,
) -> FundMetrics:
    """Compute all V1 metrics for a single fund."""
    returns = fund_to_return_series(fund)
    insufficient = fund.month_count < min_history_months

    results: list[MetricResult] = [
        _make_result(
            MetricId.ANNUALIZED_RETURN,
            annualized_return(returns),
            fund.date_range_start,
            fund.date_range_end,
        ),
        _make_result(
            MetricId.ANNUALIZED_VOLATILITY,
            annualized_volatility(returns),
            fund.date_range_start,
            fund.date_range_end,
        ),
        _make_result(
            MetricId.SHARPE_RATIO,
            sharpe_ratio(returns),
            fund.date_range_start,
            fund.date_range_end,
        ),
        _make_result(
            MetricId.MAX_DRAWDOWN,
            max_drawdown(returns),
            fund.date_range_start,
            fund.date_range_end,
        ),
    ]

    if benchmark is not None:
        bench_series = _benchmark_to_series(benchmark)
        corr_value = benchmark_correlation(returns, bench_series)
    else:
        corr_value = float("nan")

    results.append(
        _make_result(
            MetricId.BENCHMARK_CORRELATION,
            corr_value,
            fund.date_range_start,
            fund.date_range_end,
        )
    )

    logger.info(
        "Computed metrics for %s (%d months, insufficient=%s)",
        fund.fund_name,
        fund.month_count,
        insufficient,
    )
    return FundMetrics(
        fund_name=fund.fund_name,
        metric_results=results,
        date_range_start=fund.date_range_start,
        date_range_end=fund.date_range_end,
        month_count=fund.month_count,
        insufficient_history=insufficient,
    )


def compute_all_metrics(
    funds: list[NormalizedFund],
    benchmark: BenchmarkSeries | None = None,
    min_history_months: int = 12,
) -> list[FundMetrics]:
    """Compute metrics for entire universe."""
    return [
        compute_fund_metrics(fund, benchmark, min_history_months) for fund in funds
    ]
