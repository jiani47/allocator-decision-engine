"""Base constraint interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.schemas import ConstraintResult, FundMetrics, NormalizedFund


class BaseConstraint(ABC):
    @abstractmethod
    def evaluate(self, fund: NormalizedFund, metrics: FundMetrics) -> ConstraintResult:
        """Evaluate constraint for a single fund. Returns pass/fail + explanation."""
