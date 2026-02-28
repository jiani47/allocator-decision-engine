"""Adapter: maps domain models to core engine primitives (pd.Series)."""

from __future__ import annotations

import pandas as pd

from app.core.schemas import NormalizedFund, NormalizedUniverse


def fund_to_return_series(fund: NormalizedFund) -> pd.Series:
    """Convert a NormalizedFund's monthly_returns dict to a sorted pd.Series."""
    series = pd.Series(fund.monthly_returns, dtype=float)
    series.index = pd.PeriodIndex(series.index, freq="M")
    return series.sort_index()


def universe_to_fund_return_dict(
    universe: NormalizedUniverse,
) -> dict[str, pd.Series]:
    """Convert entire universe to dict of fund_name -> pd.Series of returns."""
    return {fund.fund_name: fund_to_return_series(fund) for fund in universe.funds}
