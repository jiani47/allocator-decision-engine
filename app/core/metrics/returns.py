"""Return-based metric functions (pure, deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def annualized_return(monthly_returns: pd.Series) -> float:
    """Compute annualized return from monthly return series.

    Formula: (product(1 + r_i))^(12/n) - 1
    """
    r = monthly_returns.dropna().astype(float).to_numpy()
    if r.size == 0:
        raise ValueError("No returns provided")
    growth = np.prod(1.0 + r)
    years = r.size / 12.0
    return float(growth ** (1.0 / years) - 1.0)


def annualized_volatility(monthly_returns: pd.Series) -> float:
    """Compute annualized volatility.

    Formula: std(monthly_returns) * sqrt(12)
    """
    r = monthly_returns.dropna().astype(float).to_numpy()
    if r.size == 0:
        raise ValueError("No returns provided")
    return float(np.std(r, ddof=1) * np.sqrt(12))
