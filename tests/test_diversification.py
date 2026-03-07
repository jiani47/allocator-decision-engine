"""Tests for the portfolio diversification metric."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.core.metrics.diversification import marginal_diversification_benefit
from app.core.metrics.portfolio_data import get_default_portfolio
from app.core.metrics.compute import (
    _portfolio_to_return_series,
    compute_fund_metrics,
)
from app.core.schemas import NormalizedFund


def _make_series(values: list[float], start: str = "2023-01") -> pd.Series:
    """Create a pd.Series with PeriodIndex from a list of values."""
    year, month = map(int, start.split("-"))
    periods = []
    for i in range(len(values)):
        m = month + i
        y = year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        periods.append(f"{y}-{m:02d}")
    s = pd.Series(values, index=pd.PeriodIndex(periods, freq="M"))
    return s


class TestMarginalDiversificationBenefit:
    def test_uncorrelated_reduces_vol(self):
        """Uncorrelated candidate should reduce portfolio vol (positive benefit)."""
        rng = np.random.default_rng(42)
        portfolio = _make_series(rng.normal(0.01, 0.03, 24).tolist())
        candidate = _make_series(rng.normal(0.01, 0.03, 24).tolist())

        benefit = marginal_diversification_benefit(candidate, portfolio)
        assert benefit > 0, "Uncorrelated fund should provide diversification benefit"

    def test_identical_series_no_benefit(self):
        """Candidate identical to portfolio gives ~0 benefit."""
        values = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.01, -0.03, 0.02, 0.01, 0.02, -0.01]
        portfolio = _make_series(values)
        candidate = _make_series(values)

        benefit = marginal_diversification_benefit(candidate, portfolio)
        assert abs(benefit) < 1e-10, "Identical series should give zero benefit"

    def test_anti_correlated_high_benefit(self):
        """Negatively correlated candidate gives highest benefit."""
        values = [0.03, -0.02, 0.04, -0.01, 0.03, -0.02, 0.01, -0.03, 0.02, -0.01, 0.03, -0.02]
        portfolio = _make_series(values)
        candidate = _make_series([-v for v in values])

        benefit = marginal_diversification_benefit(candidate, portfolio)
        assert benefit > 0.05, "Anti-correlated fund should provide large diversification benefit"

    def test_insufficient_overlap_returns_nan(self):
        """Fewer than 6 overlapping periods returns NaN."""
        portfolio = _make_series([0.01, 0.02, 0.03, 0.04, 0.05])
        candidate = _make_series([0.01, 0.02, 0.03, 0.04, 0.05])

        benefit = marginal_diversification_benefit(candidate, portfolio)
        assert math.isnan(benefit)

    def test_deterministic(self):
        """Running twice produces identical results."""
        rng = np.random.default_rng(99)
        portfolio = _make_series(rng.normal(0.01, 0.03, 24).tolist())
        candidate = _make_series(rng.normal(0.01, 0.03, 24).tolist())

        b1 = marginal_diversification_benefit(candidate, portfolio)
        b2 = marginal_diversification_benefit(candidate, portfolio)
        assert b1 == b2

    def test_zero_vol_portfolio_returns_zero(self):
        """Portfolio with zero volatility returns 0 benefit."""
        portfolio = _make_series([0.01] * 12)
        candidate = _make_series([0.01, -0.02, 0.03, 0.01, -0.01, 0.02,
                                   0.01, -0.03, 0.02, 0.01, 0.02, -0.01])

        benefit = marginal_diversification_benefit(candidate, portfolio)
        assert benefit == 0.0

    def test_custom_marginal_allocation(self):
        """Different marginal allocation should change the result."""
        rng = np.random.default_rng(42)
        portfolio = _make_series(rng.normal(0.01, 0.03, 24).tolist())
        candidate = _make_series(rng.normal(0.01, 0.03, 24).tolist())

        b_5pct = marginal_diversification_benefit(candidate, portfolio, 0.05)
        b_20pct = marginal_diversification_benefit(candidate, portfolio, 0.20)
        # Larger allocation should have a larger effect
        assert abs(b_20pct) > abs(b_5pct)


class TestPortfolioToReturnSeries:
    def test_default_portfolio_produces_series(self):
        """get_default_portfolio() should produce a valid weighted return series."""
        portfolio = get_default_portfolio()
        series = _portfolio_to_return_series(portfolio)
        assert len(series) == 36
        assert all(not math.isnan(v) for v in series)

    def test_weights_sum_to_one(self):
        """Default portfolio weights should sum to ~1.0."""
        portfolio = get_default_portfolio()
        total = sum(h.weight for h in portfolio.holdings)
        assert abs(total - 1.0) < 0.01


class TestComputeFundMetricsWithPortfolio:
    def test_includes_diversification_metric(self):
        """compute_fund_metrics with portfolio should include PORTFOLIO_DIVERSIFICATION."""
        fund = NormalizedFund(
            fund_name="Test Fund",
            monthly_returns={f"2023-{m:02d}": 0.01 * (m % 3 - 1) for m in range(1, 13)},
            date_range_start="2023-01",
            date_range_end="2023-12",
            month_count=12,
        )
        portfolio = get_default_portfolio()
        metrics = compute_fund_metrics(fund, existing_portfolio=portfolio)

        div_value = metrics.get_value("portfolio_diversification")
        assert div_value is not None
        assert not math.isnan(div_value)

    def test_without_portfolio_returns_none(self):
        """compute_fund_metrics without portfolio should return None for diversification."""
        fund = NormalizedFund(
            fund_name="Test Fund",
            monthly_returns={f"2023-{m:02d}": 0.01 for m in range(1, 13)},
            date_range_start="2023-01",
            date_range_end="2023-12",
            month_count=12,
        )
        metrics = compute_fund_metrics(fund)

        div_value = metrics.get_value("portfolio_diversification")
        assert div_value is None
