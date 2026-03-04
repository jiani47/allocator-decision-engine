"""Minimum Sharpe ratio constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, MetricId, NormalizedFund


class MinSharpeConstraint(BaseConstraint):
    def __init__(self, min_sharpe_ratio: float) -> None:
        self._min_sharpe = min_sharpe_ratio  # e.g., 0.5

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        actual_sharpe = metrics.get_value(MetricId.SHARPE_RATIO) or 0.0
        passed = actual_sharpe >= self._min_sharpe
        return ConstraintResult(
            constraint_name="min_sharpe_ratio",
            passed=passed,
            explanation=(
                f"{fund.fund_name}: Sharpe ratio {actual_sharpe:.2f} "
                f"{'meets' if passed else 'below'} {self._min_sharpe:.2f} minimum"
            ),
            threshold=self._min_sharpe,
            actual_value=actual_sharpe,
        )
