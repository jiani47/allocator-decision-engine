"""Step 0: Mandate Configuration."""
import streamlit as st
from app.config import Settings
from app.core.schemas import MandateConfig, MetricId
from app.ui.widgets.navigation import render_nav_buttons


def render() -> None:
    st.title("Equi")
    st.subheader("Allocator Decision Engine")
    st.markdown(
        "Turn messy manager data into normalized, validated, "
        "and defendable investment decisions."
    )

    st.header("Step 1: Define Your Mandate")
    st.markdown("Set your hard constraints and scoring preferences before uploading data.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Constraints")
        use_liquidity = st.checkbox("Min liquidity constraint")
        min_liq = st.number_input("Min liquidity (days)", 0, 365, 45) if use_liquidity else None

        use_dd = st.checkbox("Max drawdown constraint")
        max_dd_pct = st.slider("Max drawdown tolerance (%)", 1, 50, 20) if use_dd else None

        use_vol = st.checkbox("Target volatility constraint")
        target_vol_pct = st.slider("Target volatility (%)", 1, 50, 15) if use_vol else None

        min_history = st.number_input("Min history (months)", 1, 120, 12)

    with col2:
        st.subheader("Scoring Weights")
        w_ret = st.slider("Annualized Return weight", 0.0, 1.0, 0.4, 0.05)
        w_sharpe = st.slider("Sharpe Ratio weight", 0.0, 1.0, 0.4, 0.05)
        w_dd = st.slider("Max Drawdown penalty weight", 0.0, 1.0, 0.2, 0.05)

        total = w_ret + w_sharpe + w_dd
        if abs(total - 1.0) > 0.01:
            st.warning(f"Weights sum to {total:.2f}, not 1.0.")

    weights = {}
    if w_ret > 0:
        weights[MetricId.ANNUALIZED_RETURN] = w_ret
    if w_sharpe > 0:
        weights[MetricId.SHARPE_RATIO] = w_sharpe
    if w_dd > 0:
        weights[MetricId.MAX_DRAWDOWN] = w_dd

    st.divider()
    st.subheader("Strategy Filters")
    st.caption("Optional — filter funds by strategy label before ranking.")
    strategy_include = st.text_input(
        "Include only these strategies (comma-separated)",
        placeholder="e.g., Long/Short Equity, Global Macro",
    )
    strategy_exclude = st.text_input(
        "Exclude these strategies (comma-separated)",
        placeholder="e.g., Credit",
    )

    def _save_mandate() -> None:
        include_list = (
            [s.strip() for s in strategy_include.split(",") if s.strip()]
            if strategy_include
            else []
        )
        exclude_list = (
            [s.strip() for s in strategy_exclude.split(",") if s.strip()]
            if strategy_exclude
            else []
        )
        mandate = MandateConfig(
            min_liquidity_days=min_liq,
            max_drawdown_tolerance=-max_dd_pct / 100.0 if max_dd_pct else None,
            target_volatility=target_vol_pct / 100.0 if target_vol_pct else None,
            min_history_months=min_history,
            weights=weights,
            strategy_include=include_list,
            strategy_exclude=exclude_list,
        )
        st.session_state["mandate"] = mandate

    render_nav_buttons(forward_step=1, on_forward=_save_mandate, key_prefix="mandate")
