"""Minimum liquidity constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, NormalizedFund


class MinLiquidityConstraint(BaseConstraint):
    def __init__(self, min_liquidity_days: int) -> None:
        self._min_days = min_liquidity_days

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        if fund.liquidity_days is None:
            return ConstraintResult(
                constraint_name="min_liquidity",
                passed=True,
                explanation=f"{fund.fund_name}: no liquidity data available, passing by default",
                threshold=float(self._min_days),
                actual_value=None,
            )

        passed = fund.liquidity_days <= self._min_days
        return ConstraintResult(
            constraint_name="min_liquidity",
            passed=passed,
            explanation=(
                f"{fund.fund_name}: liquidity {fund.liquidity_days}d "
                f"{'<=' if passed else '>'} {self._min_days}d threshold"
            ),
            threshold=float(self._min_days),
            actual_value=float(fund.liquidity_days),
        )
