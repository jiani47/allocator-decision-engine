"""Step 2: Metrics & Ranking."""
import pandas as pd
import streamlit as st
from app.core.exceptions import DecisionEngineError
from app.core.schemas import FundGroup, MetricId
from app.services import step_fetch_benchmark
from app.ui.widgets.metric_format import format_metric
from app.ui.widgets.navigation import render_nav_buttons


def render() -> None:
    st.header("Step 3: Metrics & Ranking")

    mandate = st.session_state["mandate"]
    universe = st.session_state["universe"]
    eligibility = st.session_state["eligibility"]

    # --- Benchmark configuration ---
    st.subheader("Benchmark")
    st.caption("Data source: Yahoo Finance (monthly adjusted close, converted to returns).")
    col_bm, col_skip = st.columns([3, 1])
    with col_bm:
        benchmark_symbol = st.text_input(
            "Benchmark ticker", value="SPY", key="benchmark_ticker"
        )
    with col_skip:
        skip_benchmark = st.checkbox(
            "Skip benchmark", key="skip_benchmark",
            help="Correlation will be N/A",
        )

    effective_symbol = None if skip_benchmark else benchmark_symbol
    stored_benchmark = st.session_state.get("_benchmark")

    # Clear stored benchmark if ticker changed
    prev_ticker = st.session_state.get("_benchmark_ticker")
    if prev_ticker is not None and prev_ticker != effective_symbol:
        st.session_state.pop("_benchmark", None)
        stored_benchmark = None
    st.session_state["_benchmark_ticker"] = effective_symbol

    if not skip_benchmark and benchmark_symbol:
        if st.button("Fetch Benchmark", key="fetch_benchmark"):
            try:
                bm = step_fetch_benchmark(benchmark_symbol, universe)
                st.session_state["_benchmark"] = bm
                stored_benchmark = bm
            except (DecisionEngineError, Exception) as e:
                st.error(f"Failed to fetch benchmark '{benchmark_symbol}': {e}")
                st.session_state.pop("_benchmark", None)
                stored_benchmark = None

        if stored_benchmark is not None:
            periods = sorted(stored_benchmark.monthly_returns.keys())
            fund_periods: set[str] = set()
            for f in universe.funds:
                fund_periods.update(f.monthly_returns.keys())
            overlap = len(
                set(stored_benchmark.monthly_returns.keys()) & fund_periods
            )
            st.success(
                f"Fetched {len(periods)} months of {stored_benchmark.symbol} "
                f"({periods[0]} to {periods[-1]}), "
                f"{overlap} overlapping with fund universe"
            )

            # Benchmark preview
            bm_data = [
                {"Period": p, "Monthly Return": stored_benchmark.monthly_returns[p]}
                for p in periods
            ]
            bm_df = pd.DataFrame(bm_data)
            preview_n = 6
            st.caption(f"Most recent {min(preview_n, len(periods))} months:")
            st.dataframe(
                bm_df.tail(preview_n).style.format({"Monthly Return": "{:.4%}"}),
                use_container_width=True,
                hide_index=True,
            )
            with st.expander(f"View all {len(periods)} months"):
                st.dataframe(
                    bm_df.style.format({"Monthly Return": "{:.4%}"}),
                    use_container_width=True,
                    hide_index=True,
                )

    st.divider()

    # --- Ranking computation ---
    if "group_runs" not in st.session_state:
        eligible_names = [e.fund_name for e in eligibility if e.eligible]
        default_group = FundGroup(
            group_name="All Funds",
            group_id="default",
            fund_names=eligible_names,
            benchmark_symbol=effective_symbol,
            benchmark=stored_benchmark,
            grouping_rationale="",
        )

        try:
            from app.services import step_rank_group

            with st.spinner("Computing metrics and ranking..."):
                group_run = step_rank_group(
                    universe,
                    default_group,
                    mandate,
                    min_history_months=mandate.min_history_months,
                )
            st.session_state["group_runs"] = [group_run]
        except DecisionEngineError as e:
            st.error(f"Ranking failed: {e}")
            render_nav_buttons(back_step=1, key_prefix="ranking_err")
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            render_nav_buttons(back_step=1, key_prefix="ranking_err2")
            return

    gr = st.session_state["group_runs"][0]

    # Metric explanation
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

    # Benchmark info
    if gr.group.benchmark:
        bm = gr.group.benchmark
        bm_periods = sorted(bm.monthly_returns.keys())
        st.caption(
            f"Benchmark: **{bm.symbol}** — {len(bm_periods)} months "
            f"({bm_periods[0]} to {bm_periods[-1]})"
        )
    elif gr.group.benchmark_symbol:
        st.caption(f"Benchmark: {gr.group.benchmark_symbol} (fetch failed)")
    else:
        st.caption("Benchmark: None (correlation will be N/A)")

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
            row[mid.value] = format_metric(mid, val) if val is not None else "-"
        row["Constraints"] = "Pass" if sf.all_constraints_passed else "FAIL"
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

    render_nav_buttons(back_step=1, forward_step=3, key_prefix="ranking")
