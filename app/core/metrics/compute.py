"""Orchestrator: compute all V1 metrics for a fund or universe."""

from __future__ import annotations

import logging

import pandas as pd

from app.core.schemas import (
    BenchmarkSeries,
    FundMetrics,
    MetricId,
    NormalizedFund,
)
from app.core.metrics.correlation import benchmark_correlation
from app.core.metrics.returns import annualized_return, annualized_volatility
from app.core.metrics.risk import max_drawdown, sharpe_ratio
from app.domains.alt_invest.adapter import fund_to_return_series

logger = logging.getLogger("equi.metrics")


def _benchmark_to_series(benchmark: BenchmarkSeries) -> pd.Series:
    """Convert BenchmarkSeries to pd.Series with PeriodIndex."""
    series = pd.Series(benchmark.monthly_returns, dtype=float)
    series.index = pd.PeriodIndex(series.index, freq="M")
    return series.sort_index()


def compute_fund_metrics(
    fund: NormalizedFund,
    benchmark: BenchmarkSeries | None = None,
    min_history_months: int = 12,
) -> FundMetrics:
    """Compute all V1 metrics for a single fund."""
    returns = fund_to_return_series(fund)
    insufficient = fund.month_count < min_history_months

    metrics: dict[MetricId, float] = {
        MetricId.ANNUALIZED_RETURN: annualized_return(returns),
        MetricId.ANNUALIZED_VOLATILITY: annualized_volatility(returns),
        MetricId.SHARPE_RATIO: sharpe_ratio(returns),
        MetricId.MAX_DRAWDOWN: max_drawdown(returns),
    }

    if benchmark is not None:
        bench_series = _benchmark_to_series(benchmark)
        metrics[MetricId.BENCHMARK_CORRELATION] = benchmark_correlation(
            returns, bench_series
        )
    else:
        metrics[MetricId.BENCHMARK_CORRELATION] = float("nan")

    logger.info(
        "Computed metrics for %s (%d months, insufficient=%s)",
        fund.fund_name,
        fund.month_count,
        insufficient,
    )
    return FundMetrics(
        fund_name=fund.fund_name,
        metrics=metrics,
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
