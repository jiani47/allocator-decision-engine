"""Fund detail card widget."""
import pandas as pd
import streamlit as st
from app.core.schemas import LLMExtractedFund, RawFileContext


def render_fund_card(
    fund: LLMExtractedFund,
    raw_context: RawFileContext,
    row_lookup: dict[int, list[str | None]],
) -> None:
    """Render a fund detail expander with metadata, sample returns, source rows."""
    returns_sorted = sorted(fund.monthly_returns.items())
    date_range = f"{returns_sorted[0][0]} to {returns_sorted[-1][0]}" if returns_sorted else "N/A"

    with st.expander(
        f"{fund.fund_name} — {len(fund.monthly_returns)} months ({date_range})"
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Strategy:** {fund.strategy or 'N/A'}")
            st.write(f"**Liquidity (days):** {fund.liquidity_days or 'N/A'}")
            st.write(f"**Management fee:** {fund.management_fee or 'N/A'}")
            st.write(f"**Performance fee:** {fund.performance_fee or 'N/A'}")
        with col2:
            st.write(f"**Months:** {len(fund.monthly_returns)}")
            st.write(f"**Date range:** {date_range}")

        sample = returns_sorted[:3]
        st.markdown("**Sample returns:**")
        for period, ret in sample:
            st.markdown(f"- {period}: {ret:.2%}")
        if len(returns_sorted) > 3:
            st.caption(f"... and {len(returns_sorted) - 3} more months")

        if fund.source_row_indices:
            with st.expander(f"Source rows ({len(fund.source_row_indices)} rows)"):
                source_data = []
                for ri in fund.source_row_indices:
                    cells = row_lookup.get(ri, [])
                    row_dict = {"Row #": ri}
                    for hi, header in enumerate(raw_context.headers):
                        row_dict[header] = cells[hi] if hi < len(cells) else None
                    source_data.append(row_dict)
                if source_data:
                    st.dataframe(pd.DataFrame(source_data), use_container_width=True)


def _render_source_rows(
    fund: LLMExtractedFund,
    raw_context: RawFileContext,
    row_lookup: dict[int, list[str | None]],
) -> None:
    """Render source rows dataframe inside an expander."""
    if not fund.source_row_indices:
        return
    source_data = []
    for ri in fund.source_row_indices:
        cells = row_lookup.get(ri, [])
        row_dict = {"Row #": ri}
        for hi, header in enumerate(raw_context.headers):
            row_dict[header] = cells[hi] if hi < len(cells) else None
        source_data.append(row_dict)
    if source_data:
        st.dataframe(
            pd.DataFrame(source_data),
            use_container_width=True,
            hide_index=True,
        )


def render_eligible_table(
    funds: list[LLMExtractedFund],
    raw_context: RawFileContext,
    row_lookup: dict[int, list[str | None]],
) -> None:
    """Render eligible funds as a summary table with per-fund source row viewers."""
    rows = []
    for fund in funds:
        returns_sorted = sorted(fund.monthly_returns.keys())
        period = (
            f"{returns_sorted[0]} \u2013 {returns_sorted[-1]}"
            if returns_sorted
            else "N/A"
        )
        rows.append(
            {
                "Name": fund.fund_name,
                "Strategy": fund.strategy or "\u2014",
                "Months": len(fund.monthly_returns),
                "Period": period,
                "Liquidity": f"{fund.liquidity_days}d" if fund.liquidity_days is not None else "\u2014",
                "Mgmt Fee": f"{fund.management_fee:.1%}" if fund.management_fee is not None else "\u2014",
                "Perf Fee": f"{fund.performance_fee:.1%}" if fund.performance_fee is not None else "\u2014",
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Per-fund source row viewers
    for fund in funds:
        if fund.source_row_indices:
            with st.expander(f"Source rows \u2014 {fund.fund_name}"):
                _render_source_rows(fund, raw_context, row_lookup)
