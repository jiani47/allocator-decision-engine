"""Target volatility constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, MetricId, NormalizedFund


class TargetVolatilityConstraint(BaseConstraint):
    def __init__(self, target_volatility: float) -> None:
        self._target = target_volatility

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        actual_vol = metrics.metrics.get(MetricId.ANNUALIZED_VOLATILITY, 0.0)
        passed = actual_vol <= self._target
        return ConstraintResult(
            constraint_name="target_volatility",
            passed=passed,
            explanation=(
                f"{fund.fund_name}: volatility {actual_vol:.2%} "
                f"{'<=' if passed else '>'} {self._target:.2%} target"
            ),
            threshold=self._target,
            actual_value=actual_vol,
        )
