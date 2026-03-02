"""Step 5: Metrics & Ranking."""
import streamlit as st
import pandas as pd
from app.core.exceptions import DecisionEngineError
from app.core.schemas import FundGroup, MetricId
from app.ui.state import go_to, reset_from
from app.ui.widgets.metric_format import format_metric


def render() -> None:
    st.header("Step 6: Metrics & Ranking")

    groups: list[FundGroup] = st.session_state["groups"]
    mandate = st.session_state["mandate"]
    universe = st.session_state["universe"]

    # Check if we need to compute (first visit)
    if "group_runs" not in st.session_state:
        try:
            from app.services import step_rank_group

            group_runs = []
            with st.spinner("Computing metrics and ranking per group..."):
                for group in groups:
                    group_run = step_rank_group(
                        universe,
                        group,
                        mandate,
                        min_history_months=mandate.min_history_months,
                    )
                    group_runs.append(group_run)

            st.session_state["group_runs"] = group_runs
        except DecisionEngineError as e:
            st.error(f"Ranking failed: {e}")
            if st.button("Back"):
                reset_from(4)
                go_to(4)
                st.rerun()
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            if st.button("Back"):
                reset_from(4)
                go_to(4)
                st.rerun()
            return

    group_runs = st.session_state["group_runs"]

    # Metric explanation expander
    with st.expander("How are these metrics calculated?"):
        st.markdown(
            "**Annualized Return:** Geometric mean of monthly growth factors, annualized."
        )
        st.markdown(
            "**Annualized Volatility:** Sample std dev of monthly returns x sqrt(12)."
        )
        st.markdown(
            "**Sharpe Ratio:** Ann. Return / Ann. Volatility (risk-free rate = 0)."
        )
        st.markdown(
            "**Max Drawdown:** Worst peak-to-trough decline in cumulative wealth."
        )
        st.markdown(
            "**Benchmark Correlation:** Pearson correlation over overlapping periods."
        )

    # Per-group tabs
    tab_labels = [
        f"{gr.group.group_name} ({len(gr.ranked_shortlist)})" for gr in group_runs
    ]
    tabs = st.tabs(tab_labels)

    for tab, gr in zip(tabs, group_runs):
        with tab:
            # Excluded candidates
            excluded = [rc for rc in gr.run_candidates if not rc.included]
            if excluded:
                with st.expander(f"{len(excluded)} fund(s) excluded from ranking"):
                    for rc in excluded:
                        st.write(f"- **{rc.fund_name}**: {rc.exclusion_reason}")

            # Ranked shortlist table
            rows = []
            for sf in gr.ranked_shortlist:
                m = sf.metric_values
                row = {
                    "Rank": sf.rank,
                    "Fund": sf.fund_name,
                    "Score": f"{sf.composite_score:.3f}",
                }
                for mid in MetricId:
                    val = m.get(mid)
                    row[mid.value] = (
                        format_metric(mid, val) if val is not None else "-"
                    )
                row["Constraints"] = (
                    "Pass" if sf.all_constraints_passed else "FAIL"
                )
                rows.append(row)

            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

            # Score breakdown per fund
            for sf in gr.ranked_shortlist:
                with st.expander(f"{sf.fund_name} — Details"):
                    if sf.score_breakdown:
                        st.markdown("**Score Breakdown:**")
                        for sc in sf.score_breakdown:
                            st.write(
                                f"- {sc.metric_id.value}: "
                                f"raw={sc.raw_value:.4f}, "
                                f"normalized={sc.normalized_value:.3f}, "
                                f"weight={sc.weight}, "
                                f"contribution={sc.weighted_contribution:.4f}"
                            )
                    if sf.constraint_results:
                        st.markdown("**Constraints:**")
                        for cr in sf.constraint_results:
                            icon = "+" if cr.passed else "x"
                            st.write(f"[{icon}] {cr.explanation}")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            reset_from(4)
            go_to(4)
            st.rerun()
    with col2:
        if st.button("Generate Memos", type="primary"):
            go_to(6)
            st.rerun()
