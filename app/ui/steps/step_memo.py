"""Step 3: Memo, Claims & Export."""
import streamlit as st
from app.core.schemas import MetricId
from app.services import step_create_run, step_export_pdf
from app.ui.widgets.calc_sheet import render_calc_sheet
from app.ui.widgets.navigation import render_nav_buttons


def render() -> None:
    st.header("Step 4: IC Memo & Export")

    gr = st.session_state["group_runs"][0]
    mandate = st.session_state["mandate"]
    universe = st.session_state["universe"]

    if not gr.memo:
        st.warning("No memo available. Go back to generate one.")
        render_nav_buttons(back_step=2, key_prefix="memo")
        return

    # --- Memo text ---
    st.markdown(gr.memo.memo_text)

    # --- Claims & Evidence ---
    if gr.memo.claims:
        st.subheader("Claims & Evidence")
        raw_context = st.session_state.get("raw_context")
        fund_lookup = {f.fund_name: f for f in universe.funds}
        metrics_lookup = {m.fund_name: m for m in gr.fund_metrics}

        # Claim selector
        claim_labels = [
            f"[{c.claim_id}] {c.claim_text[:80]}{'...' if len(c.claim_text) > 80 else ''}"
            for c in gr.memo.claims
        ]
        selected_idx = st.radio(
            "Select a claim to inspect",
            range(len(gr.memo.claims)),
            format_func=lambda i: claim_labels[i],
            key="selected_claim_idx",
        )

        selected_claim = gr.memo.claims[selected_idx]
        st.markdown(f"**Claim:** {selected_claim.claim_text}")

        for fund_name in selected_claim.referenced_fund_names:
            fund = fund_lookup.get(fund_name)
            fm = metrics_lookup.get(fund_name)
            if not fund or not fm:
                continue

            for metric_id in selected_claim.referenced_metric_ids:
                with st.expander(
                    f"{fund_name} — {metric_id.value}", expanded=True
                ):
                    render_calc_sheet(
                        fund=fund,
                        metric_id=metric_id,
                        fund_metrics=fm,
                        raw_context=raw_context,
                        benchmark=gr.group.benchmark,
                    )

    # --- Data Appendix ---
    with st.expander("Data Appendix"):
        filename = st.session_state.get("uploaded_name", "Unknown")
        st.markdown(
            f"**Fund Universe:** {filename} — "
            f"{len(universe.funds)} funds"
        )

        constraints = []
        if mandate.min_liquidity_days is not None:
            constraints.append(f"Min liquidity: {mandate.min_liquidity_days} days")
        if mandate.max_drawdown_tolerance is not None:
            constraints.append(f"Max drawdown: {mandate.max_drawdown_tolerance:.0%}")
        if mandate.target_volatility is not None:
            constraints.append(f"Target volatility: {mandate.target_volatility:.0%}")
        if mandate.min_annualized_return is not None:
            constraints.append(f"Min return: {mandate.min_annualized_return:.0%}")
        if mandate.min_sharpe_ratio is not None:
            constraints.append(f"Min Sharpe: {mandate.min_sharpe_ratio:.2f}")
        constraints.append(f"Min history: {mandate.min_history_months} months")
        st.markdown("**Mandate Constraints:** " + " · ".join(constraints))

        filters = []
        if mandate.strategy_include:
            filters.append("Include: " + ", ".join(mandate.strategy_include))
        if mandate.strategy_exclude:
            filters.append("Exclude: " + ", ".join(mandate.strategy_exclude))
        if filters:
            st.markdown("**Strategy Filters:** " + " · ".join(filters))
        else:
            st.markdown("**Strategy Filters:** None")

        bm = gr.group.benchmark
        if bm:
            bm_periods = sorted(bm.monthly_returns.keys())
            st.markdown(
                f"**Benchmark:** {bm.symbol} — "
                f"{len(bm_periods)} months "
                f"({bm_periods[0]} to {bm_periods[-1]}), "
                f"source: Yahoo Finance"
            )
        elif gr.group.benchmark_symbol:
            st.markdown(f"**Benchmark:** {gr.group.benchmark_symbol} (fetch failed)")
        else:
            st.markdown("**Benchmark:** None")

        weight_label = {
            MetricId.ANNUALIZED_RETURN: "Ann. Return",
            MetricId.SHARPE_RATIO: "Sharpe",
            MetricId.MAX_DRAWDOWN: "Drawdown",
        }
        weight_parts = [
            f"{weight_label.get(mid, mid.value)} {w:.0%}"
            for mid, w in mandate.weights.items()
        ]
        st.markdown("**Ranking Model:** " + ", ".join(weight_parts))
        st.caption(
            "Min-max normalized, weighted composite score, "
            "constraint-pass priority."
        )

    # --- Export ---
    st.divider()
    st.subheader("Export")

    decision_run = st.session_state.get("decision_run")
    if not decision_run:
        decision_run = step_create_run(
            universe=universe,
            mandate=mandate,
            fund_eligibility=st.session_state.get("eligibility"),
            group_runs=st.session_state.get("group_runs"),
            benchmark=None,
            all_fund_metrics=st.session_state.get("fund_metrics"),
            run_candidates=None,
            ranked_shortlist=None,
            memo=None,
            fact_pack=None,
        )
        st.session_state["decision_run"] = decision_run

    pdf_content = step_export_pdf(decision_run)
    st.download_button(
        "Download Memo (PDF)",
        data=pdf_content,
        file_name=f"equi_memo_{decision_run.run_id[:8]}.pdf",
        mime="application/pdf",
    )

    render_nav_buttons(back_step=2, key_prefix="memo")
