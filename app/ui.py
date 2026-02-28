"""Equi — Allocator Decision Engine (Streamlit UI).

Thin, declarative UI. All business logic lives in app/services.py.
"""

import math

import pandas as pd
import streamlit as st

from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.core.schemas import ColumnMapping, MandateConfig, MetricId

st.set_page_config(
    page_title="Equi — Allocator Decision Engine",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
STEPS = [
    "Upload CSV",
    "Confirm Mapping",
    "Review Warnings",
    "Benchmark",
    "Metrics",
    "Mandate",
    "Ranked Shortlist",
    "Memo",
    "Audit",
    "Export",
]

if "step" not in st.session_state:
    st.session_state["step"] = 0


def _go_to(step: int) -> None:
    st.session_state["step"] = step


def _reset_from(step: int) -> None:
    """Clear downstream state when going back."""
    keys_by_step = {
        0: ["raw_df", "mapping", "file_hash", "universe", "benchmark", "fund_metrics",
            "mandate", "ranked", "memo", "fact_pack", "decision_run"],
        1: ["universe", "benchmark", "fund_metrics", "mandate", "ranked", "memo",
            "fact_pack", "decision_run"],
        2: ["benchmark", "fund_metrics", "mandate", "ranked", "memo", "fact_pack",
            "decision_run"],
        3: ["fund_metrics", "mandate", "ranked", "memo", "fact_pack", "decision_run"],
        4: ["mandate", "ranked", "memo", "fact_pack", "decision_run"],
        5: ["ranked", "memo", "fact_pack", "decision_run"],
        6: ["memo", "fact_pack", "decision_run"],
        7: ["decision_run"],
    }
    for key in keys_by_step.get(step, []):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Sidebar: progress indicator
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Pipeline Progress")
    for i, name in enumerate(STEPS):
        if i < st.session_state["step"]:
            st.markdown(f"~~{i+1}. {name}~~")
        elif i == st.session_state["step"]:
            st.markdown(f"**{i+1}. {name}** <--")
        else:
            st.markdown(f"{i+1}. {name}")

    st.divider()
    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state["step"] = 0
        st.rerun()


# ---------------------------------------------------------------------------
# Step 0: Upload CSV
# ---------------------------------------------------------------------------
if st.session_state["step"] == 0:
    st.title("Equi")
    st.subheader("Allocator Decision Engine")
    st.markdown(
        "Turn messy manager data into normalized, validated, "
        "and defendable investment decisions."
    )

    uploaded = st.file_uploader("Upload fund universe CSV", type=["csv"])

    if uploaded:
        try:
            from app.services import step_upload

            content = uploaded.getvalue()
            df, mapping, fhash = step_upload(content, uploaded.name)
            st.session_state["uploaded_content"] = content
            st.session_state["uploaded_name"] = uploaded.name
            st.session_state["raw_df"] = df
            st.session_state["mapping"] = mapping
            st.session_state["file_hash"] = fhash
            st.success(f"Parsed {len(df)} rows, {len(df.columns)} columns")
            _go_to(1)
            st.rerun()
        except DecisionEngineError as e:
            st.error(str(e))

# ---------------------------------------------------------------------------
# Step 1: Confirm Schema Mapping
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 1:
    st.header("Step 2: Confirm Schema Mapping")
    df = st.session_state["raw_df"]
    mapping = st.session_state["mapping"]
    columns = list(df.columns)

    st.markdown("We inferred the following column mapping. Adjust if needed.")

    col1, col2 = st.columns(2)
    with col1:
        fund_name_col = st.selectbox(
            "Fund Name column",
            columns,
            index=columns.index(mapping.fund_name) if mapping.fund_name in columns else 0,
        )
        date_col = st.selectbox(
            "Date column",
            columns,
            index=columns.index(mapping.date) if mapping.date in columns else 0,
        )
        return_col = st.selectbox(
            "Monthly Return column",
            columns,
            index=columns.index(mapping.monthly_return)
            if mapping.monthly_return in columns
            else 0,
        )

    with col2:
        optional_cols = ["(none)"] + columns
        strategy_col = st.selectbox(
            "Strategy column (optional)",
            optional_cols,
            index=optional_cols.index(mapping.strategy)
            if mapping.strategy in optional_cols
            else 0,
        )
        liquidity_col = st.selectbox(
            "Liquidity Days column (optional)",
            optional_cols,
            index=optional_cols.index(mapping.liquidity_days)
            if mapping.liquidity_days in optional_cols
            else 0,
        )

    st.dataframe(df.head(10), use_container_width=True)

    confirmed_mapping = ColumnMapping(
        fund_name=fund_name_col,
        date=date_col,
        monthly_return=return_col,
        strategy=strategy_col if strategy_col != "(none)" else None,
        liquidity_days=liquidity_col if liquidity_col != "(none)" else None,
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(0)
            _go_to(0)
            st.rerun()
    with bc2:
        if st.button("Confirm Mapping & Normalize", type="primary"):
            try:
                from app.services import step_normalize

                st.session_state["mapping"] = confirmed_mapping
                universe = step_normalize(
                    df, confirmed_mapping, st.session_state["file_hash"]
                )
                st.session_state["universe"] = universe
                _go_to(2)
                st.rerun()
            except DecisionEngineError as e:
                st.error(str(e))

# ---------------------------------------------------------------------------
# Step 2: Review Validation Warnings
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 2:
    st.header("Step 3: Review Validation Warnings")
    universe = st.session_state["universe"]

    st.metric("Funds Normalized", len(universe.funds))

    if universe.warnings:
        for w in universe.warnings:
            icon = "!" if w.severity == "error" else "i"
            label = f"[{w.category}] {w.fund_name or 'General'}"
            with st.expander(label):
                st.write(w.message)
                if w.row_indices:
                    st.write(f"Affected rows: {w.row_indices}")
    else:
        st.success("No validation warnings.")

    # Show normalized universe summary
    fund_data = []
    for f in universe.funds:
        fund_data.append({
            "Fund": f.fund_name,
            "Strategy": f.strategy or "-",
            "Months": f.month_count,
            "Start": f.date_range_start,
            "End": f.date_range_end,
            "Liquidity (days)": f.liquidity_days or "-",
        })
    st.dataframe(pd.DataFrame(fund_data), use_container_width=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(1)
            _go_to(1)
            st.rerun()
    with bc2:
        if st.button("Continue to Benchmark", type="primary"):
            _go_to(3)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 3: Benchmark Configuration
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 3:
    st.header("Step 4: Benchmark Configuration")

    symbol = st.text_input("Benchmark ticker symbol", value="SPY")
    skip_benchmark = st.checkbox("Skip benchmark (no correlation metric)")

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(2)
            _go_to(2)
            st.rerun()
    with bc2:
        if st.button("Fetch Benchmark & Compute Metrics", type="primary"):
            universe = st.session_state["universe"]
            benchmark = None

            if not skip_benchmark:
                try:
                    from app.services import step_fetch_benchmark

                    with st.spinner(f"Fetching {symbol} from Yahoo Finance..."):
                        benchmark = step_fetch_benchmark(symbol, universe)
                    st.session_state["benchmark"] = benchmark
                    st.success(
                        f"Fetched {len(benchmark.monthly_returns)} months of {symbol}"
                    )
                except DecisionEngineError as e:
                    st.warning(f"Benchmark fetch failed: {e}. Continuing without benchmark.")
                except Exception as e:
                    st.warning(f"Benchmark fetch failed: {e}. Continuing without benchmark.")

            st.session_state["benchmark_symbol"] = symbol if not skip_benchmark else "None"

            # Compute metrics
            from app.services import step_compute_metrics

            with st.spinner("Computing metrics..."):
                fund_metrics = step_compute_metrics(
                    universe, st.session_state.get("benchmark")
                )
            st.session_state["fund_metrics"] = fund_metrics
            _go_to(4)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 4: Review Metrics
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 4:
    st.header("Step 5: Metrics")
    fund_metrics = st.session_state["fund_metrics"]

    rows = []
    for fm in fund_metrics:
        row = {"Fund": fm.fund_name}
        for mid in MetricId:
            val = fm.metrics.get(mid, float("nan"))
            if mid in (MetricId.ANNUALIZED_RETURN, MetricId.ANNUALIZED_VOLATILITY, MetricId.MAX_DRAWDOWN):
                row[mid.value] = f"{val:.2%}" if not math.isnan(val) else "-"
            elif mid == MetricId.SHARPE_RATIO:
                row[mid.value] = f"{val:.2f}" if not math.isnan(val) else "-"
            else:
                row[mid.value] = f"{val:.3f}" if not math.isnan(val) else "-"
        row["Months"] = fm.month_count
        if fm.insufficient_history:
            row["Fund"] += " (insufficient history)"
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(3)
            _go_to(3)
            st.rerun()
    with bc2:
        if st.button("Configure Mandate", type="primary"):
            _go_to(5)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 5: Mandate Configuration
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 5:
    st.header("Step 6: Mandate & Weights")
    universe = st.session_state["universe"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Constraints")
        use_liquidity = st.checkbox("Min liquidity constraint")
        min_liq = st.number_input("Min liquidity (days)", 0, 365, 45) if use_liquidity else None

        use_dd = st.checkbox("Max drawdown constraint")
        max_dd_pct = st.slider("Max drawdown tolerance (%)", 1, 50, 20) if use_dd else None

        use_vol = st.checkbox("Target volatility constraint")
        target_vol_pct = st.slider("Target volatility (%)", 1, 50, 15) if use_vol else None

        strategies = list({f.strategy for f in universe.funds if f.strategy})
        strategy_exclude = st.multiselect("Exclude strategies", strategies)

    with col2:
        st.subheader("Scoring Weights")
        w_ret = st.slider("Return weight", 0.0, 1.0, 0.4, 0.05)
        w_sharpe = st.slider("Sharpe weight", 0.0, 1.0, 0.4, 0.05)
        w_dd = st.slider("Drawdown penalty weight", 0.0, 1.0, 0.2, 0.05)

        total = w_ret + w_sharpe + w_dd
        if abs(total - 1.0) > 0.01:
            st.warning(f"Weights sum to {total:.2f}, not 1.0. Results may be unexpected.")

    mandate = MandateConfig(
        min_liquidity_days=min_liq,
        max_drawdown_tolerance=-max_dd_pct / 100.0 if max_dd_pct else None,
        target_volatility=target_vol_pct / 100.0 if target_vol_pct else None,
        strategy_exclude=strategy_exclude,
        weight_return=w_ret,
        weight_sharpe=w_sharpe,
        weight_drawdown_penalty=w_dd,
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(4)
            _go_to(4)
            st.rerun()
    with bc2:
        if st.button("Run Decision Engine", type="primary"):
            from app.services import step_rank

            with st.spinner("Ranking funds..."):
                ranked = step_rank(
                    universe, st.session_state["fund_metrics"], mandate
                )
            st.session_state["mandate"] = mandate
            st.session_state["ranked"] = ranked
            _go_to(6)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 6: Ranked Shortlist
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 6:
    st.header("Step 7: Ranked Shortlist")
    ranked = st.session_state["ranked"]

    rows = []
    for sf in ranked:
        m = sf.metrics
        rows.append({
            "Rank": sf.rank,
            "Fund": sf.fund_name,
            "Score": f"{sf.composite_score:.3f}",
            "Return": f"{m.get(MetricId.ANNUALIZED_RETURN, 0):.2%}",
            "Vol": f"{m.get(MetricId.ANNUALIZED_VOLATILITY, 0):.2%}",
            "Sharpe": f"{m.get(MetricId.SHARPE_RATIO, 0):.2f}",
            "Max DD": f"{m.get(MetricId.MAX_DRAWDOWN, 0):.2%}",
            "Constraints": "Pass" if sf.all_constraints_passed else "FAIL",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Show constraint details
    for sf in ranked:
        if sf.constraint_results:
            with st.expander(f"{sf.fund_name} — Constraint Details"):
                for cr in sf.constraint_results:
                    icon = "+" if cr.passed else "x"
                    st.write(f"[{icon}] {cr.explanation}")

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _reset_from(5)
            _go_to(5)
            st.rerun()
    with bc2:
        if st.button("Generate IC Memo", type="primary"):
            _go_to(7)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 7: Generate Memo
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 7:
    st.header("Step 8: IC Memo Generation")

    settings = Settings()

    if not settings.anthropic_api_key:
        st.warning(
            "No Anthropic API key configured. Set EQUI_ANTHROPIC_API_KEY "
            "in environment or Streamlit secrets to enable memo generation."
        )
        st.info("You can skip this step and go directly to export.")

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("Back"):
                _reset_from(6)
                _go_to(6)
                st.rerun()
        with bc2:
            if st.button("Skip to Export", type="primary"):
                _go_to(9)
                st.rerun()
    else:
        if st.button("Generate Memo", type="primary"):
            try:
                from app.services import step_generate_memo

                with st.spinner("Generating IC memo via Claude..."):
                    memo, fact_pack = step_generate_memo(
                        st.session_state["ranked"],
                        st.session_state["universe"],
                        st.session_state["mandate"],
                        st.session_state.get("benchmark_symbol", "SPY"),
                        settings,
                    )
                st.session_state["memo"] = memo
                st.session_state["fact_pack"] = fact_pack
                _go_to(8)
                st.rerun()
            except DecisionEngineError as e:
                st.error(f"Memo generation failed: {e}")

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("Back"):
                _reset_from(6)
                _go_to(6)
                st.rerun()
        with bc2:
            if st.button("Skip to Export"):
                _go_to(9)
                st.rerun()

# ---------------------------------------------------------------------------
# Step 8: Audit Claims
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 8:
    st.header("Step 9: Audit Claims")

    memo = st.session_state["memo"]
    st.markdown(memo.memo_text)

    st.divider()
    st.subheader("Claims & Evidence")

    # Build decision run for evidence lookup
    from app.services import step_build_evidence, step_create_run

    decision_run = step_create_run(
        universe=st.session_state["universe"],
        benchmark=st.session_state.get("benchmark"),
        mandate=st.session_state["mandate"],
        all_fund_metrics=st.session_state["fund_metrics"],
        ranked_shortlist=st.session_state["ranked"],
        memo=memo,
        fact_pack=st.session_state.get("fact_pack"),
    )
    st.session_state["decision_run"] = decision_run

    for claim in memo.claims:
        with st.expander(f"[{claim.claim_id}] {claim.claim_text}"):
            evidence_list = step_build_evidence(claim, decision_run)
            if not evidence_list:
                st.write("No evidence found for this claim.")
            for ev in evidence_list:
                st.markdown(f"**{ev.metric_id.value}** for **{ev.fund_name}**")
                st.write(f"- Value: `{ev.computed_value:.6f}`")
                st.write(f"- Formula: {ev.formula_description}")
                st.write(f"- Date range: {ev.date_range_start} to {ev.date_range_end} ({ev.month_count} months)")
                st.write("- Sample returns:")
                st.json(ev.sample_raw_returns)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back"):
            _go_to(7)
            st.rerun()
    with bc2:
        if st.button("Continue to Export", type="primary"):
            _go_to(9)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 9: Export
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 9:
    st.header("Step 10: Export & Archive")

    from app.services import step_create_run, step_export_json, step_export_markdown

    # Build decision run if not already created
    if "decision_run" not in st.session_state:
        decision_run = step_create_run(
            universe=st.session_state["universe"],
            benchmark=st.session_state.get("benchmark"),
            mandate=st.session_state["mandate"],
            all_fund_metrics=st.session_state["fund_metrics"],
            ranked_shortlist=st.session_state["ranked"],
            memo=st.session_state.get("memo"),
            fact_pack=st.session_state.get("fact_pack"),
        )
        st.session_state["decision_run"] = decision_run

    decision_run = st.session_state["decision_run"]

    st.markdown(f"**Run ID:** `{decision_run.run_id}`")
    st.markdown(f"**Timestamp:** {decision_run.timestamp}")
    st.markdown(f"**Input Hash:** `{decision_run.input_hash[:16]}...`")

    col1, col2 = st.columns(2)
    with col1:
        md_content = step_export_markdown(decision_run)
        st.download_button(
            "Download Memo (Markdown)",
            data=md_content,
            file_name=f"equi_memo_{decision_run.run_id[:8]}.md",
            mime="text/markdown",
        )
    with col2:
        json_content = step_export_json(decision_run)
        st.download_button(
            "Download Full Run (JSON)",
            data=json_content,
            file_name=f"equi_run_{decision_run.run_id[:8]}.json",
            mime="application/json",
        )

    st.divider()
    with st.expander("Preview Markdown Export"):
        st.markdown(md_content)

    if st.button("Back"):
        _go_to(8 if st.session_state.get("memo") else 6)
        st.rerun()
