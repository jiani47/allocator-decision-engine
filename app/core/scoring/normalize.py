"""Metric score normalization (min-max to [0, 1])."""

from __future__ import annotations

import math

from app.core.schemas import FundMetrics, MetricId

# Metrics where higher raw value = worse. These get inverted during normalization.
_INVERT_METRICS = {MetricId.MAX_DRAWDOWN}


def normalize_metric_scores(
    all_metrics: list[FundMetrics],
    metric_id: MetricId,
) -> dict[str, float]:
    """Min-max normalize a single metric across all funds to [0, 1].

    Higher normalized score is always better.
    For drawdown (negative), inversion ensures less-negative = higher score.
    """
    values = {
        fm.fund_name: fm.get_value(metric_id) for fm in all_metrics
    }

    # Filter out None and NaN
    valid = {
        name: v
        for name, v in values.items()
        if v is not None and not math.isnan(v)
    }
    if not valid:
        return {name: 0.0 for name in values}

    vals = list(valid.values())
    min_val = min(vals)
    max_val = max(vals)

    if max_val == min_val:
        return {name: 1.0 if name in valid else 0.0 for name in values}

    result: dict[str, float] = {}
    for name in values:
        if name not in valid:
            result[name] = 0.0
            continue
        raw = valid[name]
        normalized = (raw - min_val) / (max_val - min_val)
        if metric_id in _INVERT_METRICS:
            normalized = 1.0 - normalized
        result[name] = normalized

    return result
