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
    RunCandidate,
    ScoreComponent,
    ScoredFund,
)
from app.core.scoring.normalize import normalize_metric_scores

logger = logging.getLogger("equi.scoring")


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
) -> tuple[float, list[ScoreComponent]]:
    """Weighted sum of normalized metric scores with detailed breakdown.

    Returns (composite_score, breakdown).
    """
    breakdown: list[ScoreComponent] = []
    total = 0.0

    for metric_id, weight in mandate.weights.items():
        norm_val = normalized_scores.get(metric_id, 0.0)
        contribution = weight * norm_val
        total += contribution
        breakdown.append(
            ScoreComponent(
                metric_id=metric_id,
                raw_value=0.0,  # filled in by caller with actual raw value
                normalized_value=norm_val,
                weight=weight,
                weighted_contribution=contribution,
            )
        )

    return total, breakdown


def rank_universe(
    universe: NormalizedUniverse,
    all_metrics: list[FundMetrics],
    mandate: MandateConfig,
) -> tuple[list[ScoredFund], list[RunCandidate]]:
    """Main orchestrator: constraints, normalization, scoring, ranking.

    Returns (ranked_shortlist, run_candidates).
    """
    constraints = build_constraints(mandate)

    # Build fund lookup
    fund_by_name = {f.fund_name: f for f in universe.funds}
    metrics_by_name = {m.fund_name: m for m in all_metrics}

    # Track inclusion/exclusion for every fund
    run_candidates: list[RunCandidate] = []

    # Determine eligible funds
    eligible_names: list[str] = []
    for name, m in metrics_by_name.items():
        if m.insufficient_history:
            run_candidates.append(
                RunCandidate(
                    fund_name=name,
                    included=False,
                    exclusion_reason=f"Insufficient history ({m.month_count} months)",
                )
            )
        else:
            eligible_names.append(name)
            run_candidates.append(
                RunCandidate(fund_name=name, included=True)
            )

    eligible_metrics = [metrics_by_name[name] for name in eligible_names]

    # Normalize each weighted metric across eligible funds
    normalized_by_metric: dict[MetricId, dict[str, float]] = {}
    for metric_id in mandate.weights:
        normalized_by_metric[metric_id] = normalize_metric_scores(
            eligible_metrics, metric_id
        )

    scored_funds: list[ScoredFund] = []
    for name in eligible_names:
        fund = fund_by_name[name]
        metrics = metrics_by_name[name]

        constraint_results = evaluate_constraints(fund, metrics, constraints)
        all_passed = all(cr.passed for cr in constraint_results)

        # Build per-fund normalized scores dict for composite calculation
        fund_norm: dict[MetricId, float] = {
            mid: scores.get(name, 0.0)
            for mid, scores in normalized_by_metric.items()
        }

        composite, breakdown = compute_composite_score(fund_norm, mandate)

        # Fill in raw values on the breakdown
        raw_values = metrics.values_dict()
        for component in breakdown:
            component.raw_value = raw_values.get(component.metric_id, 0.0)

        scored_funds.append(
            ScoredFund(
                fund_name=name,
                metric_values=raw_values,
                score_breakdown=breakdown,
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
    return scored_funds, run_candidates
