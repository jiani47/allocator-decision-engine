"""Metric value formatting utilities."""
import math
from app.core.schemas import MetricId


def format_metric(metric_id: MetricId, value: float) -> str:
    """Format a metric value for display."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    if metric_id in (MetricId.ANNUALIZED_RETURN, MetricId.ANNUALIZED_VOLATILITY, MetricId.MAX_DRAWDOWN):
        return f"{value:.2%}"
    elif metric_id == MetricId.SHARPE_RATIO:
        return f"{value:.2f}"
    else:
        return f"{value:.3f}"
