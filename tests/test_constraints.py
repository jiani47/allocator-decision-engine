"""Tests for constraints and ranking."""

from pathlib import Path

from app.core.constraints.drawdown import MaxDrawdownConstraint
from app.core.constraints.liquidity import MinLiquidityConstraint
from app.core.constraints.strategy import StrategyConstraint
from app.core.constraints.volatility import TargetVolatilityConstraint
from app.core.hashing import file_hash
from app.core.metrics.compute import compute_all_metrics
from app.core.schemas import (
    FundMetrics,
    MandateConfig,
    MetricId,
    NormalizedFund,
)
from app.core.scoring.ranking import rank_universe
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    infer_column_mapping,
    read_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _make_fund(
    name: str = "Test Fund",
    strategy: str | None = "Equity",
    liquidity_days: int | None = 30,
) -> NormalizedFund:
    return NormalizedFund(
        fund_name=name,
        strategy=strategy,
        liquidity_days=liquidity_days,
        management_fee=None,
        performance_fee=None,
        monthly_returns={"2022-01": 0.01, "2022-02": -0.005},
        date_range_start="2022-01",
        date_range_end="2022-02",
        month_count=2,
    )


def _make_metrics(name: str = "Test Fund", dd: float = -0.10, vol: float = 0.12) -> FundMetrics:
    return FundMetrics(
        fund_name=name,
        metrics={
            MetricId.ANNUALIZED_RETURN: 0.08,
            MetricId.ANNUALIZED_VOLATILITY: vol,
            MetricId.SHARPE_RATIO: 0.67,
            MetricId.MAX_DRAWDOWN: dd,
            MetricId.BENCHMARK_CORRELATION: 0.75,
        },
        date_range_start="2022-01",
        date_range_end="2022-12",
        month_count=12,
    )


class TestLiquidityConstraint:
    def test_pass(self):
        fund = _make_fund(liquidity_days=30)
        result = MinLiquidityConstraint(30).evaluate(fund, _make_metrics())
        assert result.passed

    def test_fail(self):
        fund = _make_fund(liquidity_days=60)
        result = MinLiquidityConstraint(45).evaluate(fund, _make_metrics())
        assert not result.passed

    def test_no_data_passes(self):
        fund = _make_fund(liquidity_days=None)
        result = MinLiquidityConstraint(30).evaluate(fund, _make_metrics())
        assert result.passed


class TestDrawdownConstraint:
    def test_within_tolerance(self):
        result = MaxDrawdownConstraint(-0.20).evaluate(
            _make_fund(), _make_metrics(dd=-0.10)
        )
        assert result.passed

    def test_exceeds_tolerance(self):
        result = MaxDrawdownConstraint(-0.05).evaluate(
            _make_fund(), _make_metrics(dd=-0.10)
        )
        assert not result.passed

    def test_exact_threshold(self):
        result = MaxDrawdownConstraint(-0.10).evaluate(
            _make_fund(), _make_metrics(dd=-0.10)
        )
        assert result.passed


class TestVolatilityConstraint:
    def test_below_target(self):
        result = TargetVolatilityConstraint(0.15).evaluate(
            _make_fund(), _make_metrics(vol=0.12)
        )
        assert result.passed

    def test_above_target(self):
        result = TargetVolatilityConstraint(0.10).evaluate(
            _make_fund(), _make_metrics(vol=0.12)
        )
        assert not result.passed


class TestStrategyConstraint:
    def test_include_pass(self):
        fund = _make_fund(strategy="Equity")
        result = StrategyConstraint(include=["Equity"], exclude=[]).evaluate(
            fund, _make_metrics()
        )
        assert result.passed

    def test_include_fail(self):
        fund = _make_fund(strategy="Credit")
        result = StrategyConstraint(include=["Equity"], exclude=[]).evaluate(
            fund, _make_metrics()
        )
        assert not result.passed

    def test_exclude_fail(self):
        fund = _make_fund(strategy="Credit")
        result = StrategyConstraint(include=[], exclude=["Credit"]).evaluate(
            fund, _make_metrics()
        )
        assert not result.passed

    def test_exclude_pass(self):
        fund = _make_fund(strategy="Equity")
        result = StrategyConstraint(include=[], exclude=["Credit"]).evaluate(
            fund, _make_metrics()
        )
        assert result.passed


class TestRanking:
    def _load_universe_and_metrics(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))
        all_metrics = compute_all_metrics(universe.funds)
        return universe, all_metrics

    def test_ranking_produces_all_funds(self):
        universe, all_metrics = self._load_universe_and_metrics()
        mandate = MandateConfig()
        ranked = rank_universe(universe, all_metrics, mandate)
        assert len(ranked) == 3

    def test_ranks_are_sequential(self):
        universe, all_metrics = self._load_universe_and_metrics()
        mandate = MandateConfig()
        ranked = rank_universe(universe, all_metrics, mandate)
        assert [sf.rank for sf in ranked] == [1, 2, 3]

    def test_ranking_is_deterministic(self):
        universe, all_metrics = self._load_universe_and_metrics()
        mandate = MandateConfig()
        run1 = rank_universe(universe, all_metrics, mandate)
        run2 = rank_universe(universe, all_metrics, mandate)
        assert [sf.fund_name for sf in run1] == [sf.fund_name for sf in run2]

    def test_constraint_failure_pushes_to_bottom(self):
        universe, all_metrics = self._load_universe_and_metrics()
        # Exclude "Global Macro" — Birch should be pushed to bottom
        mandate = MandateConfig(strategy_exclude=["Global Macro"])
        ranked = rank_universe(universe, all_metrics, mandate)
        birch = next(sf for sf in ranked if sf.fund_name == "Birch Global Macro")
        assert not birch.all_constraints_passed
        assert birch.rank == 3

    def test_weight_sensitivity(self):
        """Changing weights should change scores for non-dominant funds."""
        universe, all_metrics = self._load_universe_and_metrics()
        ranked_a = rank_universe(
            universe, all_metrics, MandateConfig(weight_return=1.0, weight_sharpe=0.0, weight_drawdown_penalty=0.0)
        )
        ranked_b = rank_universe(
            universe, all_metrics, MandateConfig(weight_return=0.0, weight_sharpe=0.0, weight_drawdown_penalty=1.0)
        )
        # Second-place fund should have different scores under different weights
        scores_a = {sf.fund_name: sf.composite_score for sf in ranked_a}
        scores_b = {sf.fund_name: sf.composite_score for sf in ranked_b}
        # At least one non-top fund should differ
        diffs = [scores_a[n] != scores_b[n] for n in scores_a if scores_a[n] < 1.0 or scores_b[n] < 1.0]
        assert any(diffs)
