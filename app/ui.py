"""Equi — Allocator Decision Engine (Streamlit UI).

Thin, declarative UI. All business logic lives in app/services.py.
"""

import math

import pandas as pd
import streamlit as st

from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.core.schemas import MandateConfig, MetricId

st.set_page_config(
    page_title="Equi — Allocator Decision Engine",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
STEPS = [
    "Upload File",
    "Review Interpretation",
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
        0: ["universe", "benchmark", "fund_metrics",
            "mandate", "ranked", "run_candidates", "memo", "fact_pack", "decision_run",
            "raw_context", "llm_result", "llm_validation_errors",
            "dismissed_warnings", "warning_resolutions"],
        1: ["universe", "benchmark", "fund_metrics", "mandate", "ranked",
            "run_candidates", "memo", "fact_pack", "decision_run",
            "dismissed_warnings", "warning_resolutions"],
        2: ["benchmark", "fund_metrics", "mandate", "ranked", "run_candidates",
            "memo", "fact_pack", "decision_run", "warning_resolutions"],
        3: ["fund_metrics", "mandate", "ranked", "run_candidates", "memo",
            "fact_pack", "decision_run"],
        4: ["mandate", "ranked", "run_candidates", "memo", "fact_pack", "decision_run"],
        5: ["ranked", "run_candidates", "memo", "fact_pack", "decision_run"],
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
# Helper: render LLM interpretation review step
# ---------------------------------------------------------------------------
def _render_llm_review_step() -> None:
    """Render the LLM extraction review UI."""
    llm_result = st.session_state["llm_result"]
    raw_context = st.session_state["raw_context"]
    validation_errors = st.session_state.get("llm_validation_errors", [])

    # Interpretation notes
    if llm_result.interpretation_notes:
        st.info(f"**Interpretation:** {llm_result.interpretation_notes}")

    # Ambiguities
    if llm_result.ambiguities:
        st.warning(
            "**Ambiguities detected:**\n"
            + "\n".join(f"- {a}" for a in llm_result.ambiguities)
        )

    # Validation errors
    if validation_errors:
        st.error(
            "**Validation issues:**\n"
            + "\n".join(f"- {e}" for e in validation_errors)
        )

    # Build row index lookup for source row display
    row_lookup: dict[int, list[str | None]] = {}
    for raw_row in raw_context.data_rows:
        row_lookup[raw_row.row_index] = raw_row.cells
    for raw_row in raw_context.aggregated_rows:
        row_lookup[raw_row.row_index] = raw_row.cells
    for raw_row in raw_context.empty_rows:
        row_lookup[raw_row.row_index] = raw_row.cells

    # Per-fund review
    st.subheader(f"Extracted {len(llm_result.funds)} fund(s)")
    for fund in llm_result.funds:
        returns_sorted = sorted(fund.monthly_returns.items())
        date_range = f"{returns_sorted[0][0]} to {returns_sorted[-1][0]}" if returns_sorted else "N/A"

        with st.expander(
            f"{fund.fund_name} — {len(fund.monthly_returns)} months "
            f"({date_range})"
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

            # Sample returns as readable bullet points
            sample = returns_sorted[:3]
            st.markdown("**Sample returns:**")
            for period, ret in sample:
                st.markdown(f"- {period}: {ret:.2%}")
            if len(returns_sorted) > 3:
                st.caption(f"... and {len(returns_sorted) - 3} more months")

            # Source rows as clickable expander with actual data
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

    # Skipped rows section
    has_aggregated = len(raw_context.aggregated_rows) > 0
    has_empty = len(raw_context.empty_rows) > 0
    if has_aggregated or has_empty:
        st.subheader("Skipped Rows")
        st.caption("These rows were detected but not used for fund extraction.")

        if has_aggregated:
            with st.expander(f"Aggregated rows ({len(raw_context.aggregated_rows)} rows)"):
                agg_data = []
                for raw_row in raw_context.aggregated_rows:
                    row_dict: dict[str, object] = {"Row #": raw_row.row_index, "Reason": "Aggregated"}
                    for hi, header in enumerate(raw_context.headers):
                        row_dict[header] = raw_row.cells[hi] if hi < len(raw_row.cells) else None
                    agg_data.append(row_dict)
                st.dataframe(pd.DataFrame(agg_data), use_container_width=True)

        if has_empty:
            with st.expander(f"Empty rows ({len(raw_context.empty_rows)} rows)"):
                empty_indices = [r.row_index for r in raw_context.empty_rows]
                st.write(f"Empty row indices: {empty_indices}")

    # Correction and re-extract
    correction = st.text_area(
        "Corrections or instructions for re-extraction (optional)",
        placeholder="e.g., 'The returns are already in decimal format, not percentages'",
        key="llm_correction",
    )

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("Back"):
            _reset_from(0)
            _go_to(0)
            st.rerun()
    with bc2:
        if st.button("Re-extract with LLM"):
            try:
                from app.services import step_llm_extract

                settings = Settings()
                with st.spinner("Re-extracting with LLM..."):
                    result, errors = step_llm_extract(raw_context, settings)
                st.session_state["llm_result"] = result
                st.session_state["llm_validation_errors"] = errors
                st.rerun()
            except DecisionEngineError as e:
                st.error(f"LLM extraction failed: {e}")
    with bc3:
        if st.button("Confirm & Normalize", type="primary"):
            try:
                from app.services import step_normalize_from_llm

                universe = step_normalize_from_llm(llm_result, raw_context)
                st.session_state["universe"] = universe
                _go_to(2)
                st.rerun()
            except DecisionEngineError as e:
                st.error(str(e))


# ---------------------------------------------------------------------------
# Audit helpers
# ---------------------------------------------------------------------------


def _get_highlight_rows_for_claim(
    claim, decision_run,
) -> dict[str, list[int]]:
    """Return {fund_name: [row_indices]} for all funds referenced in a claim."""
    highlight: dict[str, list[int]] = {}
    universe = decision_run.universe
    fund_lookup = {f.fund_name: f for f in universe.funds}
    for fund_name in claim.referenced_fund_names:
        fund = fund_lookup.get(fund_name)
        if fund and fund.source_row_indices:
            highlight[fund_name] = fund.source_row_indices
    return highlight


_HIGHLIGHT_COLORS = [
    ("#DCE6F1", "#4472C4"),  # light blue / blue label
    ("#FFF2CC", "#BF8F00"),  # amber / dark amber label
    ("#E2EFDA", "#548235"),  # green / dark green label
    ("#FCE4EC", "#C62828"),  # pink / dark red label
    ("#E8EAF6", "#283593"),  # indigo / dark indigo label
]


def _render_worksheet_html(
    raw_context,
    highlight_rows: dict[str, list[int]],
) -> str:
    """Build an Excel-like HTML table from RawFileContext with highlighted rows."""
    import html as html_lib

    # Build color mapping per fund
    fund_color_map: dict[str, tuple[str, str]] = {}
    for i, fund_name in enumerate(highlight_rows):
        fund_color_map[fund_name] = _HIGHLIGHT_COLORS[i % len(_HIGHLIGHT_COLORS)]

    # Invert to row_index -> (bg_color, fund_name)
    row_highlight: dict[int, tuple[str, str]] = {}
    for fund_name, indices in highlight_rows.items():
        bg, _ = fund_color_map[fund_name]
        for ri in indices:
            row_highlight[ri] = (bg, fund_name)

    # Collect all rows (data + aggregated + empty), sorted by row_index
    all_rows = list(raw_context.data_rows) + list(raw_context.aggregated_rows) + list(raw_context.empty_rows)
    all_rows.sort(key=lambda r: r.row_index)

    num_cols = len(raw_context.headers)

    # CSS
    css = """
<style>
.ws-container { max-height:600px; overflow-y:auto; border:1px solid #CCCCCC; }
.ws-table { border-collapse:collapse; font-family:monospace; font-size:13px; width:100%; }
.ws-table th {
    background:#4472C4; color:white; padding:6px 10px; text-align:left;
    border:1px solid #E0E0E0; position:sticky; top:0; z-index:1;
}
.ws-table td { padding:4px 10px; border:1px solid #E0E0E0; white-space:nowrap; }
.ws-rownum { background:#F0F0F0; color:#888; text-align:center; font-size:12px; min-width:40px; }
.ws-row-even { background:#FFFFFF; }
.ws-row-odd { background:#F9F9F9; }
</style>
"""

    # Header row
    header_cells = '<th class="ws-rownum">#</th>'
    for h in raw_context.headers:
        header_cells += f"<th>{html_lib.escape(str(h))}</th>"
    table_header = f"<tr>{header_cells}</tr>"

    # Data rows
    body_rows = []
    for idx, raw_row in enumerate(all_rows):
        ri = raw_row.row_index
        if ri in row_highlight:
            bg_color, fund_name = row_highlight[ri]
            style = f'style="background:{bg_color};"'
            tooltip = f' title="Fund: {html_lib.escape(fund_name)}"'
        else:
            stripe = "ws-row-even" if idx % 2 == 0 else "ws-row-odd"
            style = f'class="{stripe}"'
            tooltip = ""

        cells_html = f'<td class="ws-rownum">{ri}</td>'
        for ci in range(num_cols):
            val = raw_row.cells[ci] if ci < len(raw_row.cells) else None
            cell_text = html_lib.escape(str(val)) if val is not None else ""
            cells_html += f"<td>{cell_text}</td>"

        body_rows.append(f"<tr {style}{tooltip}>{cells_html}</tr>")

    table_html = (
        css
        + '<div class="ws-container">'
        + f'<table class="ws-table">{table_header}{"".join(body_rows)}</table>'
        + "</div>"
    )

    # Legend
    if fund_color_map:
        legend_items = []
        for fund_name, (bg, label_color) in fund_color_map.items():
            legend_items.append(
                f'<span style="display:inline-block;width:14px;height:14px;'
                f"background:{bg};border:1px solid {label_color};"
                f'vertical-align:middle;margin-right:4px;"></span>'
                f'<span style="color:{label_color};margin-right:12px;">'
                f"{html_lib.escape(fund_name)}</span>"
            )
        table_html += '<div style="margin-top:8px;font-size:13px;">' + "".join(legend_items) + "</div>"

    return table_html


# ---------------------------------------------------------------------------
# Step 0: Upload File
# ---------------------------------------------------------------------------
if st.session_state["step"] == 0:
    st.title("Equi")
    st.subheader("Allocator Decision Engine")
    st.markdown(
        "Turn messy manager data into normalized, validated, "
        "and defendable investment decisions."
    )

    with st.expander("Supported file format", expanded=True):
        st.markdown(
            "**CSV or Excel file** with **monthly** return time series per fund.\n\n"
            "Required data (column names are flexible):\n"
            "- **Fund name** — manager or fund identifier\n"
            "- **Date** — monthly frequency (e.g. 2022-01-01, 01/2022)\n"
            "- **Monthly return** — decimal (0.012) or percentage (1.2%)\n\n"
            "Optional: strategy, liquidity days, management fee, performance fee.\n\n"
            "*Not supported: summary-only files, daily/weekly data, "
            "multi-currency, or multiple asset classes in one file.*"
        )

    uploaded = st.file_uploader(
        "Upload fund universe", type=["csv", "xlsx", "xls"]
    )

    if uploaded:
        content = uploaded.getvalue()
        filename = uploaded.name

        try:
            from app.services import step_parse_raw

            settings = Settings()
            raw_context = step_parse_raw(
                content, filename, max_rows=settings.ingestion_max_rows
            )
            st.session_state["uploaded_content"] = content
            st.session_state["uploaded_name"] = filename
            st.session_state["raw_context"] = raw_context

            st.success(
                f"Parsed {raw_context.total_rows} rows, "
                f"{len(raw_context.headers)} columns, "
                f"{len(raw_context.data_rows)} data rows"
            )

            if st.button("Extract with LLM", type="primary"):
                try:
                    from app.services import step_llm_extract

                    with st.spinner("Extracting fund data with LLM..."):
                        result, errors = step_llm_extract(raw_context, settings)
                    st.session_state["llm_result"] = result
                    st.session_state["llm_validation_errors"] = errors
                    _go_to(1)
                    st.rerun()
                except DecisionEngineError as e:
                    st.error(f"LLM extraction failed: {e}")

        except Exception as e:
            st.error(f"Failed to parse file: {e}")

# ---------------------------------------------------------------------------
# Step 1: Review Interpretation
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 1:
    st.header("Step 2: Review LLM Interpretation")
    _render_llm_review_step()

# ---------------------------------------------------------------------------
# Step 2: Review Validation Warnings
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 2:
    st.header("Step 3: Review Validation Warnings")
    universe = st.session_state["universe"]

    # Initialize dismissed warnings set
    if "dismissed_warnings" not in st.session_state:
        st.session_state["dismissed_warnings"] = set()

    st.metric("Funds Normalized", len(universe.funds))

    if universe.warnings:
        dismissed = st.session_state["dismissed_warnings"]
        active_count = sum(1 for i in range(len(universe.warnings)) if i not in dismissed)
        dismissed_count = len(dismissed)
        st.caption(f"{active_count} active warning(s), {dismissed_count} ignored")

        for idx, w in enumerate(universe.warnings):
            is_dismissed = idx in dismissed
            label_prefix = "~~" if is_dismissed else ""
            label_suffix = " (ignored)" if is_dismissed else ""
            label = f"{label_prefix}[{w.category}] {w.fund_name or 'General'}{label_suffix}{label_prefix}"
            with st.expander(label, expanded=not is_dismissed):
                st.write(w.message)
                if w.row_indices:
                    st.write(f"Affected rows: {w.row_indices}")

                wcol1, wcol2 = st.columns([1, 3])
                with wcol1:
                    if is_dismissed:
                        if st.button("Restore", key=f"restore_warning_{idx}"):
                            st.session_state["dismissed_warnings"].discard(idx)
                            st.rerun()
                    else:
                        if st.button("Ignore", key=f"ignore_warning_{idx}"):
                            st.session_state["dismissed_warnings"].add(idx)
                            st.rerun()
                with wcol2:
                    st.text_input(
                        "Analyst note (optional)",
                        key=f"warning_note_{idx}",
                        placeholder="e.g., Confirmed with manager, keeping as-is",
                    )
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
            # Collect warning resolutions
            from app.core.schemas import WarningResolution

            resolutions = []
            dismissed = st.session_state.get("dismissed_warnings", set())
            for idx, w in enumerate(universe.warnings):
                note = st.session_state.get(f"warning_note_{idx}", "")
                if idx in dismissed or note:
                    resolutions.append(WarningResolution(
                        category=w.category,
                        fund_name=w.fund_name,
                        original_message=w.message,
                        action="ignored" if idx in dismissed else "acknowledged",
                        analyst_note=note,
                    ))
            st.session_state["warning_resolutions"] = resolutions
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

    # Metric explanations
    with st.expander("How are these metrics calculated?"):
        st.markdown("**Annualized Return**")
        st.latex(r"\text{Ann. Return} = \left(\prod_{i=1}^{n}(1 + r_i)\right)^{12/n} - 1")
        st.caption("Geometric mean of monthly growth factors, annualized to a 12-month basis.")

        st.markdown("**Annualized Volatility**")
        st.latex(r"\text{Ann. Vol} = \sigma(r_i) \times \sqrt{12}")
        st.caption("Sample standard deviation of monthly returns, scaled to annual by multiplying by sqrt(12).")

        st.markdown("**Sharpe Ratio**")
        st.latex(r"\text{Sharpe} = \frac{\text{Ann. Return} - r_f}{\text{Ann. Vol}}")
        st.caption("Risk-adjusted return. Risk-free rate (r_f) is set to 0 in V1.")

        st.markdown("**Max Drawdown**")
        st.latex(r"\text{Max DD} = \min_t \left(\frac{\text{CumulWealth}_t}{\max_{s \leq t} \text{CumulWealth}_s} - 1\right)")
        st.caption("Worst peak-to-trough decline in cumulative wealth. Reported as a negative percentage.")

        st.markdown("**Benchmark Correlation**")
        st.latex(r"\rho(\text{fund}, \text{benchmark})")
        st.caption("Pearson correlation of monthly returns over overlapping periods (requires at least 3 months).")

    rows = []
    for fm in fund_metrics:
        row = {"Fund": fm.fund_name}
        for mid in MetricId:
            val = fm.get_value(mid)
            if val is None:
                row[mid.value] = "-"
            elif mid in (MetricId.ANNUALIZED_RETURN, MetricId.ANNUALIZED_VOLATILITY, MetricId.MAX_DRAWDOWN):
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

    mandate_name = st.text_input("Mandate name", value="Untitled Mandate")

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
        w_ret = st.slider("Annualized Return weight", 0.0, 1.0, 0.4, 0.05)
        w_sharpe = st.slider("Sharpe Ratio weight", 0.0, 1.0, 0.4, 0.05)
        w_dd = st.slider("Max Drawdown penalty weight", 0.0, 1.0, 0.2, 0.05)

        total = w_ret + w_sharpe + w_dd
        if abs(total - 1.0) > 0.01:
            st.warning(f"Weights sum to {total:.2f}, not 1.0. Results may be unexpected.")

    weights = {}
    if w_ret > 0:
        weights[MetricId.ANNUALIZED_RETURN] = w_ret
    if w_sharpe > 0:
        weights[MetricId.SHARPE_RATIO] = w_sharpe
    if w_dd > 0:
        weights[MetricId.MAX_DRAWDOWN] = w_dd

    st.divider()
    st.subheader("Memo Shortlist")
    total_funds = len(universe.funds)
    use_top_k = st.checkbox("Limit funds included in memo", value=False)
    if use_top_k:
        top_k = st.number_input(
            "Include top N funds in memo",
            min_value=1,
            max_value=total_funds,
            value=min(3, total_funds),
        )
    else:
        top_k = None
    st.caption(
        f"{'All' if top_k is None else top_k} of {total_funds} fund(s) will be analyzed in the IC memo."
    )

    mandate = MandateConfig(
        name=mandate_name,
        min_liquidity_days=min_liq,
        max_drawdown_tolerance=-max_dd_pct / 100.0 if max_dd_pct else None,
        target_volatility=target_vol_pct / 100.0 if target_vol_pct else None,
        strategy_exclude=strategy_exclude,
        weights=weights,
        shortlist_top_k=top_k,
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
                ranked, run_candidates = step_rank(
                    universe, st.session_state["fund_metrics"], mandate
                )
            st.session_state["mandate"] = mandate
            st.session_state["ranked"] = ranked
            st.session_state["run_candidates"] = run_candidates
            _go_to(6)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 6: Ranked Shortlist
# ---------------------------------------------------------------------------
elif st.session_state["step"] == 6:
    st.header("Step 7: Ranked Shortlist")
    ranked = st.session_state["ranked"]
    run_candidates = st.session_state.get("run_candidates", [])
    mandate = st.session_state["mandate"]
    top_k = mandate.shortlist_top_k

    # Info banner about memo inclusion
    if top_k is not None:
        st.info(f"Top {top_k} fund(s) will be included in the IC memo.")
    else:
        st.info(f"All {len(ranked)} fund(s) will be included in the IC memo.")

    # Show excluded candidates
    excluded = [rc for rc in run_candidates if not rc.included]
    if excluded:
        with st.expander(f"{len(excluded)} fund(s) excluded from ranking"):
            for rc in excluded:
                st.write(f"- **{rc.fund_name}**: {rc.exclusion_reason}")

    rows = []
    for sf in ranked:
        m = sf.metric_values
        in_memo = "Yes" if (top_k is None or sf.rank <= top_k) else "No"
        rows.append({
            "Rank": sf.rank,
            "Fund": sf.fund_name,
            "Score": f"{sf.composite_score:.3f}",
            "Return": f"{m.get(MetricId.ANNUALIZED_RETURN, 0):.2%}",
            "Vol": f"{m.get(MetricId.ANNUALIZED_VOLATILITY, 0):.2%}",
            "Sharpe": f"{m.get(MetricId.SHARPE_RATIO, 0):.2f}",
            "Max DD": f"{m.get(MetricId.MAX_DRAWDOWN, 0):.2%}",
            "Constraints": "Pass" if sf.all_constraints_passed else "FAIL",
            "In Memo": in_memo,
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Show constraint details and score breakdown
    for sf in ranked:
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

    st.markdown(
        "Generate an IC memo using Claude to draft narrative "
        "from the deterministic fact pack produced in the previous steps."
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Back", key="memo_back"):
            _reset_from(6)
            _go_to(6)
            st.rerun()
    with bc2:
        if st.button("Skip to Export", key="memo_skip"):
            _go_to(9)
            st.rerun()

    if st.button("Generate Memo", type="primary"):
        try:
            from app.services import step_generate_memo

            settings = Settings()
            with st.spinner("Generating IC memo via Claude..."):
                memo, fact_pack = step_generate_memo(
                    st.session_state["ranked"],
                    st.session_state["universe"],
                    st.session_state["mandate"],
                    st.session_state.get("benchmark_symbol", "SPY"),
                    settings,
                    warning_resolutions=st.session_state.get("warning_resolutions"),
                )
            st.session_state["memo"] = memo
            st.session_state["fact_pack"] = fact_pack
            _go_to(8)
            st.rerun()
        except DecisionEngineError as e:
            st.error(f"Memo generation failed: {e}")

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
        run_candidates=st.session_state.get("run_candidates", []),
        ranked_shortlist=st.session_state["ranked"],
        memo=memo,
        fact_pack=st.session_state.get("fact_pack"),
    )
    st.session_state["decision_run"] = decision_run

    if not memo.claims:
        st.info("No claims were extracted from this memo.")
    else:
        # Claim selector
        claim_labels = [
            f"[{c.claim_id}] {c.claim_text[:80]}{'...' if len(c.claim_text) > 80 else ''}"
            for c in memo.claims
        ]
        selected_idx = st.selectbox(
            "Select a claim to audit",
            range(len(memo.claims)),
            format_func=lambda i: claim_labels[i],
            key="audit_claim_select",
        )
        claim = memo.claims[selected_idx]

        # Two-column layout: evidence (left) + worksheet (right)
        raw_context = decision_run.universe.raw_context
        has_worksheet = raw_context is not None and len(raw_context.data_rows) > 0

        col_left, col_right = st.columns([3, 2] if has_worksheet else [1, 0.01])

        with col_left:
            st.markdown(f"**Claim:** {claim.claim_text}")
            st.caption(
                f"Metrics: {', '.join(m.value for m in claim.referenced_metric_ids)} | "
                f"Funds: {', '.join(claim.referenced_fund_names)}"
            )
            evidence_list = step_build_evidence(claim, decision_run)
            if not evidence_list:
                st.write("No evidence found for this claim.")
            for ev in evidence_list:
                with st.expander(f"{ev.metric_id.value} — {ev.fund_name}", expanded=True):
                    st.write(f"**Value:** `{ev.computed_value:.6f}`")
                    st.write(f"**Formula:** {ev.formula_description}")
                    st.write(
                        f"**Dependencies:** "
                        f"{', '.join(d.value for d in ev.dependencies) or 'none'}"
                    )
                    st.write(
                        f"**Date range:** {ev.date_range_start} to "
                        f"{ev.date_range_end} ({ev.month_count} months)"
                    )
                    st.write("**Sample returns:**")
                    st.json(ev.sample_raw_returns)

        with col_right:
            if has_worksheet:
                st.markdown("**Source Worksheet**")
                highlight_rows = _get_highlight_rows_for_claim(claim, decision_run)
                worksheet_html = _render_worksheet_html(raw_context, highlight_rows)
                st.markdown(worksheet_html, unsafe_allow_html=True)

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
            run_candidates=st.session_state.get("run_candidates", []),
            ranked_shortlist=st.session_state["ranked"],
            memo=st.session_state.get("memo"),
            fact_pack=st.session_state.get("fact_pack"),
        )
        st.session_state["decision_run"] = decision_run

    decision_run = st.session_state["decision_run"]

    st.markdown(f"**Run ID:** `{decision_run.run_id}`")
    st.markdown(f"**Timestamp:** {decision_run.timestamp}")
    st.markdown(f"**Metric Version:** {decision_run.metric_version}")
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
