"""Tests for step_classify_eligibility service function."""

from __future__ import annotations

from app.core.metrics.compute import compute_all_metrics
from app.core.schemas import (
    FundEligibility,
    MandateConfig,
    NormalizedFund,
    NormalizedUniverse,
)
from app.services import step_classify_eligibility


def _make_fund(
    name: str,
    *,
    liquidity_days: int | None = None,
    month_count: int = 24,
) -> NormalizedFund:
    """Build a NormalizedFund with synthetic monthly returns."""
    returns = {
        f"2022-{m:02d}": 0.01 * (m % 5 - 2)
        for m in range(1, 13)
    }
    if month_count >= 13:
        extra = {
            f"2023-{m:02d}": 0.01 * (m % 5 - 2)
            for m in range(1, min(month_count - 12 + 1, 13))
        }
        returns.update(extra)
    elif month_count < 12:
        # Trim to desired month count
        returns = dict(list(returns.items())[:month_count])

    sorted_keys = sorted(returns.keys())
    return NormalizedFund(
        fund_name=name,
        strategy="Test Strategy",
        liquidity_days=liquidity_days,
        monthly_returns=returns,
        date_range_start=sorted_keys[0] if sorted_keys else "2022-01",
        date_range_end=sorted_keys[-1] if sorted_keys else "2022-01",
        month_count=len(returns),
    )


def _make_universe(*funds: NormalizedFund) -> NormalizedUniverse:
    """Wrap funds into a NormalizedUniverse."""
    return NormalizedUniverse(
        funds=list(funds),
        source_file_hash="test-hash",
        normalization_timestamp="2024-01-01T00:00:00Z",
    )


class TestAllFundsEligibleNoConstraints:
    """With no mandate constraints, all funds should be eligible."""

    def test_no_constraints_all_eligible(self):
        fund_a = _make_fund("Fund A", liquidity_days=30)
        fund_b = _make_fund("Fund B", liquidity_days=90)
        universe = _make_universe(fund_a, fund_b)

        metrics = compute_all_metrics(universe.funds)
        mandate = MandateConfig()  # No constraints set

        eligibility = step_classify_eligibility(universe, metrics, mandate)

        assert len(eligibility) == 2
        for e in eligibility:
            assert e.eligible is True
            assert e.failing_constraints == []


class TestLiquidityConstraint:
    """Fund with liquidity_days > min_liquidity_days should be ineligible."""

    def test_fund_exceeding_liquidity_is_ineligible(self):
        # Fund with 30-day liquidity should fail a 60-day maximum constraint
        # (min_liquidity means the fund must provide liquidity within N days)
        short_liquidity = _make_fund("ShortLiq", liquidity_days=30)
        long_liquidity = _make_fund("LongLiq", liquidity_days=90)
        universe = _make_universe(short_liquidity, long_liquidity)

        metrics = compute_all_metrics(universe.funds)
        mandate = MandateConfig(min_liquidity_days=60)

        eligibility = step_classify_eligibility(universe, metrics, mandate)
        elig_map = {e.fund_name: e for e in eligibility}

        # ShortLiq has 30d <= 60d threshold, should pass
        assert elig_map["ShortLiq"].eligible is True

        # LongLiq has 90d > 60d threshold, should fail
        assert elig_map["LongLiq"].eligible is False
        assert len(elig_map["LongLiq"].failing_constraints) >= 1
        liquidity_failure = next(
            c for c in elig_map["LongLiq"].failing_constraints
            if c.constraint_name == "min_liquidity"
        )
        assert liquidity_failure.passed is False
        assert "90" in liquidity_failure.explanation


class TestDrawdownConstraint:
    """Fund with deeper drawdown than tolerance should be ineligible."""

    def test_fund_exceeding_drawdown_is_ineligible(self):
        # Build a fund with returns that will produce a meaningful drawdown
        fund_a = _make_fund("SafeFund")
        # Build a fund with large negative returns to produce deep drawdown
        bad_fund = NormalizedFund(
            fund_name="RiskyFund",
            strategy="Aggressive",
            liquidity_days=30,
            monthly_returns={
                "2022-01": 0.05,
                "2022-02": -0.15,
                "2022-03": -0.10,
                "2022-04": 0.02,
                "2022-05": 0.03,
                "2022-06": -0.08,
                "2022-07": 0.01,
                "2022-08": 0.02,
                "2022-09": -0.05,
                "2022-10": 0.04,
                "2022-11": 0.03,
                "2022-12": 0.02,
                "2023-01": 0.01,
                "2023-02": 0.02,
                "2023-03": 0.01,
                "2023-04": 0.03,
                "2023-05": 0.02,
                "2023-06": 0.01,
                "2023-07": 0.02,
                "2023-08": 0.01,
                "2023-09": 0.03,
                "2023-10": 0.02,
                "2023-11": 0.01,
                "2023-12": 0.02,
            },
            date_range_start="2022-01",
            date_range_end="2023-12",
            month_count=24,
        )
        universe = _make_universe(fund_a, bad_fund)

        metrics = compute_all_metrics(universe.funds)
        # Very tight drawdown tolerance: -10%
        mandate = MandateConfig(max_drawdown_tolerance=-0.10)

        eligibility = step_classify_eligibility(universe, metrics, mandate)
        elig_map = {e.fund_name: e for e in eligibility}

        # RiskyFund should have a drawdown deeper than -10%, making it ineligible
        assert elig_map["RiskyFund"].eligible is False
        dd_failure = next(
            c for c in elig_map["RiskyFund"].failing_constraints
            if c.constraint_name == "max_drawdown"
        )
        assert dd_failure.passed is False
        assert "exceeds" in dd_failure.explanation


class TestInsufficientHistory:
    """Fund with < 12 months of history should be ineligible."""

    def test_short_history_is_ineligible(self):
        short_fund = _make_fund("ShortHistory", month_count=6)
        long_fund = _make_fund("LongHistory", month_count=24)
        universe = _make_universe(short_fund, long_fund)

        metrics = compute_all_metrics(universe.funds)
        mandate = MandateConfig()

        eligibility = step_classify_eligibility(universe, metrics, mandate)
        elig_map = {e.fund_name: e for e in eligibility}

        assert elig_map["ShortHistory"].eligible is False
        assert len(elig_map["ShortHistory"].failing_constraints) == 1
        history_failure = elig_map["ShortHistory"].failing_constraints[0]
        assert history_failure.constraint_name == "history"
        assert history_failure.passed is False
        assert "6 months" in history_failure.explanation

        assert elig_map["LongHistory"].eligible is True


class TestEligibleFundsHaveEmptyFailingConstraints:
    """Eligible funds should have empty failing_constraints lists."""

    def test_eligible_empty_failures(self):
        fund = _make_fund("GoodFund", liquidity_days=30)
        universe = _make_universe(fund)

        metrics = compute_all_metrics(universe.funds)
        mandate = MandateConfig(min_liquidity_days=60)

        eligibility = step_classify_eligibility(universe, metrics, mandate)

        assert len(eligibility) == 1
        assert eligibility[0].eligible is True
        assert eligibility[0].failing_constraints == []


class TestIneligibleFundsHavePopulatedFailingConstraints:
    """Ineligible funds should have populated failing_constraints with explanations."""

    def test_ineligible_has_explanations(self):
        fund = _make_fund("BadFund", liquidity_days=120)
        universe = _make_universe(fund)

        metrics = compute_all_metrics(universe.funds)
        mandate = MandateConfig(min_liquidity_days=60)

        eligibility = step_classify_eligibility(universe, metrics, mandate)

        assert len(eligibility) == 1
        result = eligibility[0]
        assert result.eligible is False
        assert len(result.failing_constraints) >= 1

        for constraint in result.failing_constraints:
            assert constraint.explanation != ""
            assert constraint.passed is False

    def test_multiple_constraints_can_fail(self):
        """A fund can fail multiple constraints at once."""
        bad_fund = NormalizedFund(
            fund_name="MultiFailFund",
            strategy="Aggressive",
            liquidity_days=120,
            monthly_returns={
                "2022-01": 0.05,
                "2022-02": -0.20,
                "2022-03": -0.15,
                "2022-04": 0.02,
                "2022-05": 0.03,
                "2022-06": -0.08,
                "2022-07": 0.01,
                "2022-08": 0.02,
                "2022-09": -0.05,
                "2022-10": 0.04,
                "2022-11": 0.03,
                "2022-12": 0.02,
                "2023-01": 0.01,
                "2023-02": 0.02,
                "2023-03": 0.01,
                "2023-04": 0.03,
                "2023-05": 0.02,
                "2023-06": 0.01,
                "2023-07": 0.02,
                "2023-08": 0.01,
                "2023-09": 0.03,
                "2023-10": 0.02,
                "2023-11": 0.01,
                "2023-12": 0.02,
            },
            date_range_start="2022-01",
            date_range_end="2023-12",
            month_count=24,
        )
        universe = _make_universe(bad_fund)

        metrics = compute_all_metrics(universe.funds)
        # Both constraints should fail: liquidity 120 > 60, drawdown deeper than -10%
        mandate = MandateConfig(
            min_liquidity_days=60,
            max_drawdown_tolerance=-0.10,
        )

        eligibility = step_classify_eligibility(universe, metrics, mandate)

        assert len(eligibility) == 1
        result = eligibility[0]
        assert result.eligible is False
        assert len(result.failing_constraints) == 2

        constraint_names = {c.constraint_name for c in result.failing_constraints}
        assert "min_liquidity" in constraint_names
        assert "max_drawdown" in constraint_names
