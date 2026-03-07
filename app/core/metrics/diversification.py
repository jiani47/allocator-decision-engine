"""Portfolio diversification metric (pure, deterministic)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def marginal_diversification_benefit(
    candidate_returns: pd.Series,
    portfolio_returns: pd.Series,
    marginal_allocation: float = 0.05,
) -> float:
    """Compute marginal vol reduction from adding candidate to existing portfolio.

    Blends candidate into portfolio at *marginal_allocation* weight and measures
    the resulting change in annualized volatility.

    Returns (vol_portfolio - vol_combined) / vol_portfolio.
    Positive value means the candidate reduces portfolio vol (good diversifier).
    Returns NaN if fewer than 6 overlapping periods.
    """
    aligned = pd.concat(
        [candidate_returns.rename("candidate"), portfolio_returns.rename("portfolio")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 6:
        return float("nan")

    cand = aligned["candidate"].to_numpy()
    port = aligned["portfolio"].to_numpy()

    alpha = marginal_allocation
    combined = (1.0 - alpha) * port + alpha * cand

    vol_port = float(np.std(port, ddof=1) * np.sqrt(12))
    vol_combined = float(np.std(combined, ddof=1) * np.sqrt(12))

    if vol_port < 1e-12:
        return 0.0

    return float((vol_port - vol_combined) / vol_port)
