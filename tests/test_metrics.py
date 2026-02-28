"""Tests for deterministic metric computation."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.core.hashing import file_hash
from app.core.metrics.correlation import benchmark_correlation
from app.core.metrics.compute import compute_all_metrics, compute_fund_metrics
from app.core.metrics.returns import annualized_return, annualized_volatility
from app.core.metrics.risk import max_drawdown, sharpe_ratio
from app.core.schemas import BenchmarkSeries, MetricId
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    infer_column_mapping,
    read_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestAnnualizedReturn:
    def test_flat_returns(self):
        """1% per month for 12 months."""
        returns = pd.Series([0.01] * 12)
        result = annualized_return(returns)
        expected = (1.01**12) - 1  # ~12.68%
        assert abs(result - expected) < 1e-6

    def test_zero_returns(self):
        returns = pd.Series([0.0] * 12)
        assert annualized_return(returns) == 0.0

    def test_negative_returns(self):
        returns = pd.Series([-0.01] * 12)
        result = annualized_return(returns)
        assert result < 0

    def test_24_months(self):
        """Two years of 1% monthly."""
        returns = pd.Series([0.01] * 24)
        result = annualized_return(returns)
        expected = (1.01**12) - 1
        assert abs(result - expected) < 1e-6

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            annualized_return(pd.Series([], dtype=float))


class TestAnnualizedVolatility:
    def test_constant_returns(self):
        """No variation -> near-zero vol."""
        returns = pd.Series([0.01] * 12)
        assert annualized_volatility(returns) < 1e-12

    def test_known_volatility(self):
        """Known monthly std scaled by sqrt(12)."""
        returns = pd.Series([0.01, -0.01] * 6)
        monthly_std = returns.std(ddof=1)
        expected = monthly_std * np.sqrt(12)
        result = annualized_volatility(returns)
        assert abs(result - expected) < 1e-6

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            annualized_volatility(pd.Series([], dtype=float))


class TestSharpeRatio:
    def test_zero_rf(self):
        """Sharpe = ann_return / ann_vol when rf=0."""
        returns = pd.Series([0.02, -0.01, 0.015, -0.005] * 3)
        ann_ret = annualized_return(returns)
        ann_vol = annualized_volatility(returns)
        expected = ann_ret / ann_vol
        assert abs(sharpe_ratio(returns) - expected) < 1e-6

    def test_constant_returns_zero_sharpe(self):
        """Zero vol -> zero sharpe (not inf)."""
        returns = pd.Series([0.01] * 12)
        assert sharpe_ratio(returns) == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self):
        """Monotonically increasing -> no drawdown."""
        returns = pd.Series([0.01] * 12)
        assert max_drawdown(returns) == 0.0

    def test_known_drawdown(self):
        """Construct series with known max drawdown."""
        # Start at 1, go up to 1.1, drop to 0.88, recover
        # max DD = 0.88/1.1 - 1 = -0.2
        returns = pd.Series([0.10, -0.20, 0.05])
        result = max_drawdown(returns)
        # After +10%: 1.1, after -20%: 0.88, after +5%: 0.924
        # DD = 0.88/1.1 - 1 = -0.2
        assert abs(result - (-0.2)) < 1e-6

    def test_always_negative(self):
        """Max drawdown is always <= 0."""
        returns = pd.Series([0.05, -0.03, 0.02, -0.08, 0.04])
        assert max_drawdown(returns) <= 0.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            max_drawdown(pd.Series([], dtype=float))


class TestBenchmarkCorrelation:
    def test_perfect_correlation(self):
        idx = pd.PeriodIndex(["2022-01", "2022-02", "2022-03", "2022-04"], freq="M")
        fund = pd.Series([0.01, -0.02, 0.03, -0.01], index=idx)
        bench = pd.Series([0.01, -0.02, 0.03, -0.01], index=idx)
        assert abs(benchmark_correlation(fund, bench) - 1.0) < 1e-6

    def test_anti_correlation(self):
        idx = pd.PeriodIndex(["2022-01", "2022-02", "2022-03", "2022-04"], freq="M")
        fund = pd.Series([0.01, -0.02, 0.03, -0.01], index=idx)
        bench = pd.Series([-0.01, 0.02, -0.03, 0.01], index=idx)
        assert abs(benchmark_correlation(fund, bench) - (-1.0)) < 1e-6

    def test_insufficient_overlap_returns_nan(self):
        idx1 = pd.PeriodIndex(["2022-01", "2022-02"], freq="M")
        idx2 = pd.PeriodIndex(["2023-01", "2023-02"], freq="M")
        fund = pd.Series([0.01, -0.02], index=idx1)
        bench = pd.Series([0.01, -0.02], index=idx2)
        assert np.isnan(benchmark_correlation(fund, bench))


class TestComputeAllMetrics:
    def test_clean_universe_metrics(self):
        """Integration: compute metrics for all 3 funds in clean CSV."""
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        all_metrics = compute_all_metrics(universe.funds)
        assert len(all_metrics) == 3

        for fm in all_metrics:
            assert fm.get_value(MetricId.ANNUALIZED_RETURN) is not None
            assert fm.get_value(MetricId.ANNUALIZED_VOLATILITY) is not None
            assert fm.get_value(MetricId.SHARPE_RATIO) is not None
            assert fm.get_value(MetricId.MAX_DRAWDOWN) is not None
            assert fm.month_count == 24
            assert not fm.insufficient_history

    def test_metrics_deterministic(self):
        """Running twice produces identical results."""
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        run1 = compute_all_metrics(universe.funds)
        run2 = compute_all_metrics(universe.funds)

        for m1, m2 in zip(run1, run2):
            for metric_id in MetricId:
                v1, v2 = m1.get_value(metric_id), m2.get_value(metric_id)
                if v1 is None:
                    assert v2 is None
                elif np.isnan(v1):
                    assert np.isnan(v2)
                else:
                    assert v1 == v2

    def test_insufficient_history_flagged(self):
        """Fund with < 12 months should be flagged."""
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        # Set min_history to 36 so all 24-month funds are flagged
        all_metrics = compute_all_metrics(universe.funds, min_history_months=36)
        for fm in all_metrics:
            assert fm.insufficient_history

    def test_metric_results_have_lineage(self):
        """Each MetricResult should carry formula_text and period info."""
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        all_metrics = compute_all_metrics(universe.funds)
        fm = all_metrics[0]

        for mr in fm.metric_results:
            assert mr.formula_text != ""
            assert mr.period_start != ""
            assert mr.period_end != ""

        # Sharpe should depend on return and volatility
        sharpe_result = fm.get_result(MetricId.SHARPE_RATIO)
        assert sharpe_result is not None
        assert MetricId.ANNUALIZED_RETURN in sharpe_result.dependencies
        assert MetricId.ANNUALIZED_VOLATILITY in sharpe_result.dependencies
