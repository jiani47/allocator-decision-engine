"""Claim-to-evidence mapping for audit view."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.schemas import (
    Claim,
    DecisionRun,
    GroupRun,
    MetricId,
    NormalizedUniverse,
)


class MetricEvidence(BaseModel):
    """Evidence backing a single metric reference in a claim."""

    metric_id: MetricId
    fund_name: str
    computed_value: float
    formula_description: str
    dependencies: list[MetricId]
    date_range_start: str
    date_range_end: str
    month_count: int
    sample_raw_returns: dict[str, float]  # first/last few periods


def build_claim_evidence(
    claim: Claim,
    decision_run: DecisionRun,
) -> list[MetricEvidence]:
    """For each metric and fund referenced in a claim, build evidence."""
    # Build lookups
    metrics_by_name = {m.fund_name: m for m in decision_run.all_fund_metrics}
    fund_by_name = {f.fund_name: f for f in decision_run.universe.funds}

    evidence: list[MetricEvidence] = []
    for fund_name in claim.referenced_fund_names:
        fm = metrics_by_name.get(fund_name)
        fund = fund_by_name.get(fund_name)
        if fm is None or fund is None:
            continue

        for metric_id in claim.referenced_metric_ids:
            result = fm.get_result(metric_id)
            if result is None:
                continue

            # Sample raw returns: first 3 and last 3 periods
            sorted_periods = sorted(fund.monthly_returns.keys())
            sample_periods = sorted_periods[:3] + sorted_periods[-3:]
            sample_returns = {p: fund.monthly_returns[p] for p in dict.fromkeys(sample_periods)}

            evidence.append(
                MetricEvidence(
                    metric_id=metric_id,
                    fund_name=fund_name,
                    computed_value=result.value,
                    formula_description=result.formula_text,
                    dependencies=result.dependencies,
                    date_range_start=result.period_start,
                    date_range_end=result.period_end,
                    month_count=fm.month_count,
                    sample_raw_returns=sample_returns,
                )
            )

    return evidence


def build_claim_evidence_for_group(
    claim: Claim,
    group_run: GroupRun,
    universe: NormalizedUniverse,
) -> list[MetricEvidence]:
    """Build evidence chain for a claim within a specific group run."""
    # Build lookups from group-scoped data
    metrics_by_name = {m.fund_name: m for m in group_run.fund_metrics}
    fund_by_name = {f.fund_name: f for f in universe.funds}

    evidence: list[MetricEvidence] = []
    for fund_name in claim.referenced_fund_names:
        fm = metrics_by_name.get(fund_name)
        fund = fund_by_name.get(fund_name)
        if fm is None or fund is None:
            continue

        for metric_id in claim.referenced_metric_ids:
            result = fm.get_result(metric_id)
            if result is None:
                continue

            # Sample raw returns: first 3 and last 3 periods
            sorted_periods = sorted(fund.monthly_returns.keys())
            sample_periods = sorted_periods[:3] + sorted_periods[-3:]
            sample_returns = {p: fund.monthly_returns[p] for p in dict.fromkeys(sample_periods)}

            evidence.append(
                MetricEvidence(
                    metric_id=metric_id,
                    fund_name=fund_name,
                    computed_value=result.value,
                    formula_description=result.formula_text,
                    dependencies=result.dependencies,
                    date_range_start=result.period_start,
                    date_range_end=result.period_end,
                    month_count=fm.month_count,
                    sample_raw_returns=sample_returns,
                )
            )

    return evidence
