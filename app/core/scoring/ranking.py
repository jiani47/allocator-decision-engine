"""Weighted scoring and ranking orchestrator."""

from __future__ import annotations

import logging

from app.core.constraints.base import BaseConstraint
from app.core.constraints.drawdown import MaxDrawdownConstraint
from app.core.constraints.liquidity import MinLiquidityConstraint
from app.core.constraints.strategy import StrategyConstraint
from app.core.constraints.volatility import TargetVolatilityConstraint
from app.core.schemas import (
    ConstraintResult,
    FundMetrics,
    MandateConfig,
    MetricId,
    NormalizedFund,
    NormalizedUniverse,
    ScoredFund,
)
from app.core.scoring.normalize import normalize_metric_scores

logger = logging.getLogger("equi.scoring")

# Mapping from MetricId to MandateConfig weight field
_WEIGHT_MAP: dict[MetricId, str] = {
    MetricId.ANNUALIZED_RETURN: "weight_return",
    MetricId.SHARPE_RATIO: "weight_sharpe",
    MetricId.MAX_DRAWDOWN: "weight_drawdown_penalty",
}


def build_constraints(mandate: MandateConfig) -> list[BaseConstraint]:
    """Construct constraint instances from mandate configuration."""
    constraints: list[BaseConstraint] = []

    if mandate.min_liquidity_days is not None:
        constraints.append(MinLiquidityConstraint(mandate.min_liquidity_days))

    if mandate.max_drawdown_tolerance is not None:
        constraints.append(MaxDrawdownConstraint(mandate.max_drawdown_tolerance))

    if mandate.target_volatility is not None:
        constraints.append(TargetVolatilityConstraint(mandate.target_volatility))

    if mandate.strategy_include or mandate.strategy_exclude:
        constraints.append(
            StrategyConstraint(mandate.strategy_include, mandate.strategy_exclude)
        )

    return constraints


def evaluate_constraints(
    fund: NormalizedFund,
    metrics: FundMetrics,
    constraints: list[BaseConstraint],
) -> list[ConstraintResult]:
    """Run all constraints against a fund."""
    return [c.evaluate(fund, metrics) for c in constraints]


def compute_composite_score(
    normalized_scores: dict[MetricId, float],
    mandate: MandateConfig,
) -> float:
    """Weighted sum of normalized metric scores."""
    score = 0.0
    for metric_id, weight_field in _WEIGHT_MAP.items():
        weight = getattr(mandate, weight_field)
        score += weight * normalized_scores.get(metric_id, 0.0)
    return score


def rank_universe(
    universe: NormalizedUniverse,
    all_metrics: list[FundMetrics],
    mandate: MandateConfig,
) -> list[ScoredFund]:
    """Main orchestrator: constraints, normalization, scoring, ranking."""
    constraints = build_constraints(mandate)

    # Build fund lookup
    fund_by_name = {f.fund_name: f for f in universe.funds}
    metrics_by_name = {m.fund_name: m for m in all_metrics}

    # Filter out insufficient history
    eligible_names = [
        name for name, m in metrics_by_name.items() if not m.insufficient_history
    ]

    eligible_metrics = [metrics_by_name[name] for name in eligible_names]

    # Normalize each scored metric across eligible funds
    norm_return = normalize_metric_scores(eligible_metrics, MetricId.ANNUALIZED_RETURN)
    norm_sharpe = normalize_metric_scores(eligible_metrics, MetricId.SHARPE_RATIO)
    norm_dd = normalize_metric_scores(eligible_metrics, MetricId.MAX_DRAWDOWN)

    scored_funds: list[ScoredFund] = []
    for name in eligible_names:
        fund = fund_by_name[name]
        metrics = metrics_by_name[name]

        constraint_results = evaluate_constraints(fund, metrics, constraints)
        all_passed = all(cr.passed for cr in constraint_results)

        normalized = {
            MetricId.ANNUALIZED_RETURN: norm_return.get(name, 0.0),
            MetricId.SHARPE_RATIO: norm_sharpe.get(name, 0.0),
            MetricId.MAX_DRAWDOWN: norm_dd.get(name, 0.0),
        }

        composite = compute_composite_score(normalized, mandate)

        scored_funds.append(
            ScoredFund(
                fund_name=name,
                metrics=metrics.metrics,
                normalized_scores=normalized,
                composite_score=composite,
                rank=0,  # set below
                constraint_results=constraint_results,
                all_constraints_passed=all_passed,
            )
        )

    # Sort: constraint-passing funds first, then by composite score descending
    scored_funds.sort(
        key=lambda sf: (sf.all_constraints_passed, sf.composite_score),
        reverse=True,
    )

    # Assign ranks
    for i, sf in enumerate(scored_funds):
        sf.rank = i + 1

    logger.info(
        "Ranked %d funds (%d passed all constraints)",
        len(scored_funds),
        sum(1 for sf in scored_funds if sf.all_constraints_passed),
    )
    return scored_funds
