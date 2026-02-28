"""Benchmark fetching and alignment."""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from app.core.exceptions import BenchmarkAlignmentError
from app.core.schemas import BenchmarkSeries, NormalizedUniverse

logger = logging.getLogger("equi.benchmark")


def fetch_benchmark_yfinance(
    symbol: str,
    start_date: str,
    end_date: str,
) -> BenchmarkSeries:
    """Fetch monthly adjusted close from yfinance, convert to returns."""
    logger.info("Fetching benchmark %s from %s to %s", symbol, start_date, end_date)

    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start_date, end=end_date, interval="1mo")

    if hist.empty:
        raise BenchmarkAlignmentError(
            f"No data returned from yfinance for {symbol} ({start_date} to {end_date})"
        )

    # Resample to month-end and compute returns from Close
    monthly_close = hist["Close"].resample("ME").last().dropna()
    monthly_returns = monthly_close.pct_change().dropna()

    # Convert to period string keys
    returns_dict: dict[str, float] = {
        str(date.to_period("M")): float(ret)
        for date, ret in monthly_returns.items()
    }

    logger.info("Fetched %d monthly returns for %s", len(returns_dict), symbol)
    return BenchmarkSeries(
        symbol=symbol,
        monthly_returns=returns_dict,
        source="yfinance",
    )


def align_benchmark_to_universe(
    benchmark: BenchmarkSeries,
    universe: NormalizedUniverse,
) -> BenchmarkSeries:
    """Trim benchmark to overlapping date range with universe."""
    # Collect all period strings from all funds
    all_periods: set[str] = set()
    for fund in universe.funds:
        all_periods.update(fund.monthly_returns.keys())

    if not all_periods:
        raise BenchmarkAlignmentError("Universe has no periods to align to")

    # Keep only benchmark periods that overlap with universe
    aligned_returns = {
        period: ret
        for period, ret in benchmark.monthly_returns.items()
        if period in all_periods
    }

    if len(aligned_returns) < 3:
        raise BenchmarkAlignmentError(
            f"Only {len(aligned_returns)} overlapping periods between "
            f"benchmark {benchmark.symbol} and universe (need at least 3)"
        )

    logger.info(
        "Aligned benchmark %s: %d -> %d periods",
        benchmark.symbol,
        len(benchmark.monthly_returns),
        len(aligned_returns),
    )
    return BenchmarkSeries(
        symbol=benchmark.symbol,
        monthly_returns=aligned_returns,
        source=benchmark.source,
    )
