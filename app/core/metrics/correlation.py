"""Benchmark correlation metric (pure, deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def benchmark_correlation(
    fund_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Compute Pearson correlation between fund and benchmark over overlapping periods.

    Aligns by index (period strings). Returns NaN if fewer than 3 overlapping periods.
    """
    aligned = pd.concat(
        [fund_returns.rename("fund"), benchmark_returns.rename("bench")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 3:
        return float("nan")

    return float(np.corrcoef(aligned["fund"], aligned["bench"])[0, 1])
