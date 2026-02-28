"""Maximum drawdown constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, MetricId, NormalizedFund


class MaxDrawdownConstraint(BaseConstraint):
    def __init__(self, max_drawdown_tolerance: float) -> None:
        self._tolerance = max_drawdown_tolerance  # e.g., -0.20

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        actual_dd = metrics.metrics.get(MetricId.MAX_DRAWDOWN, 0.0)
        # Less negative = better. Pass if actual >= tolerance (both negative).
        passed = actual_dd >= self._tolerance
        return ConstraintResult(
            constraint_name="max_drawdown",
            passed=passed,
            explanation=(
                f"{fund.fund_name}: max drawdown {actual_dd:.2%} "
                f"{'within' if passed else 'exceeds'} {self._tolerance:.2%} tolerance"
            ),
            threshold=self._tolerance,
            actual_value=actual_dd,
        )
