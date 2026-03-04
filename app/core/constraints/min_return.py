"""Minimum annualized return constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, MetricId, NormalizedFund


class MinReturnConstraint(BaseConstraint):
    def __init__(self, min_annualized_return: float) -> None:
        self._min_return = min_annualized_return  # e.g., 0.05 for 5%

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        actual_return = metrics.get_value(MetricId.ANNUALIZED_RETURN) or 0.0
        passed = actual_return >= self._min_return
        return ConstraintResult(
            constraint_name="min_annualized_return",
            passed=passed,
            explanation=(
                f"{fund.fund_name}: annualized return {actual_return:.2%} "
                f"{'meets' if passed else 'below'} {self._min_return:.2%} minimum"
            ),
            threshold=self._min_return,
            actual_value=actual_return,
        )
