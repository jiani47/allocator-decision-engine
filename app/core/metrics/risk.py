"""Risk metric functions (pure, deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.metrics.returns import annualized_return, annualized_volatility


def sharpe_ratio(monthly_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Compute Sharpe ratio.

    Formula: (annualized_return - rf) / annualized_volatility
    """
    ann_ret = annualized_return(monthly_returns)
    ann_vol = annualized_volatility(monthly_returns)
    if ann_vol < 1e-12:
        return 0.0
    return float((ann_ret - risk_free_rate) / ann_vol)


def max_drawdown(monthly_returns: pd.Series) -> float:
    """Compute maximum drawdown from monthly returns.

    Returns negative value (e.g., -0.15 for 15% drawdown).
    Formula: min(cumulative_wealth / running_max - 1)
    """
    r = monthly_returns.dropna().astype(float).to_numpy()
    if r.size == 0:
        raise ValueError("No returns provided")
    cumulative = np.cumprod(1.0 + r)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative / running_max - 1.0
    return float(np.min(drawdowns))
