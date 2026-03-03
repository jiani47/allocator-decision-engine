"""Configurable fund summary table widget."""
import pandas as pd
import streamlit as st
from app.core.schemas import FundMetrics, MetricId, NormalizedFund, ScoredFund
from app.ui.widgets.metric_format import format_metric


def render_fund_table(
    funds: list[NormalizedFund],
    metrics: dict[str, FundMetrics] | None = None,
    scores: dict[str, ScoredFund] | None = None,
    eligibility: dict[str, bool] | None = None,
    show_strategy: bool = True,
    show_dates: bool = True,
) -> None:
    """Render a configurable fund summary dataframe."""
    rows = []
    for f in funds:
        row: dict = {"Fund": f.fund_name}
        if eligibility is not None:
            row["Eligible"] = "Yes" if eligibility.get(f.fund_name, True) else "No"
        if show_strategy:
            row["Strategy"] = f.strategy or "-"
        row["Months"] = f.month_count
        if show_dates:
            row["Start"] = f.date_range_start
            row["End"] = f.date_range_end
        row["Liquidity"] = f.liquidity_days or "-"

        if metrics and f.fund_name in metrics:
            fm = metrics[f.fund_name]
            for mid in MetricId:
                val = fm.get_value(mid)
                row[mid.value] = format_metric(mid, val) if val is not None else "-"

        if scores and f.fund_name in scores:
            sf = scores[f.fund_name]
            row["Score"] = f"{sf.composite_score:.3f}"
            row["Rank"] = sf.rank
            row["Constraints"] = "Pass" if sf.all_constraints_passed else "FAIL"

        rows.append(row)

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
