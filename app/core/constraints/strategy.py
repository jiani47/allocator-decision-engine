"""Strategy include/exclude constraint."""

from __future__ import annotations

from app.core.constraints.base import BaseConstraint
from app.core.schemas import ConstraintResult, FundMetrics, NormalizedFund


class StrategyConstraint(BaseConstraint):
    def __init__(
        self,
        include: list[str],
        exclude: list[str],
    ) -> None:
        self._include = [s.lower() for s in include]
        self._exclude = [s.lower() for s in exclude]

    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        strategy = (fund.strategy or "").lower()

        if self._exclude and strategy in self._exclude:
            return ConstraintResult(
                constraint_name="strategy_filter",
                passed=False,
                explanation=f"{fund.fund_name}: strategy '{fund.strategy}' is in exclude list",
            )

        if self._include and strategy not in self._include:
            return ConstraintResult(
                constraint_name="strategy_filter",
                passed=False,
                explanation=f"{fund.fund_name}: strategy '{fund.strategy}' is not in include list",
            )

        return ConstraintResult(
            constraint_name="strategy_filter",
            passed=True,
            explanation=f"{fund.fund_name}: strategy '{fund.strategy}' passes filter",
        )
