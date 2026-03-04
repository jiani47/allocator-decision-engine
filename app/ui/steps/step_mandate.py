"""Step 0: Mandate Configuration."""
import streamlit as st
from app.core.schemas import MandateConfig
from app.ui.widgets.navigation import render_nav_buttons


def render() -> None:
    st.title("Equi")
    st.subheader("Allocator Decision Engine")
    st.markdown(
        "Turn messy manager data into normalized, validated, "
        "and defendable investment decisions."
    )

    st.header("Step 1: Define Your Mandate")
    st.markdown("Set your hard constraints before uploading data.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Constraints")
        use_dd = st.checkbox("Max drawdown constraint")
        max_dd_pct = st.slider("Max drawdown tolerance (%)", 1, 50, 20) if use_dd else None

        use_vol = st.checkbox("Target volatility constraint")
        target_vol_pct = st.slider("Target volatility (%)", 1, 50, 15) if use_vol else None

        use_liquidity = st.checkbox("Min liquidity constraint")
        min_liq = st.number_input("Min liquidity (days)", 0, 365, 45) if use_liquidity else None

    with col2:
        st.subheader("Performance Constraints")
        use_min_return = st.checkbox("Min annualized return")
        min_return_pct = (
            st.slider("Min annualized return (%)", 0, 50, 5)
            if use_min_return
            else None
        )

        use_min_sharpe = st.checkbox("Min Sharpe ratio")
        min_sharpe = (
            st.number_input("Min Sharpe ratio", 0.0, 5.0, 0.5, 0.1)
            if use_min_sharpe
            else None
        )

        min_history = st.number_input("Min history (months)", 1, 120, 12)

    st.divider()
    with st.expander("Strategy Filters", expanded=False):
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
            min_annualized_return=min_return_pct / 100.0 if min_return_pct else None,
            min_sharpe_ratio=min_sharpe,
            min_history_months=min_history,
            strategy_include=include_list,
            strategy_exclude=exclude_list,
        )
        st.session_state["mandate"] = mandate

    render_nav_buttons(forward_step=1, on_forward=_save_mandate, key_prefix="mandate")
