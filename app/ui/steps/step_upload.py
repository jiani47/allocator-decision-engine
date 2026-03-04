"""Step 1: Upload & Review."""
import streamlit as st
from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.core.schemas import WarningResolution
from app.ui.state import reset_from
from app.ui.widgets.alert_block import render_alerts
from app.ui.widgets.navigation import render_nav_buttons
from app.ui.widgets.fund_details import render_eligible_table
from app.ui.widgets.warning_panel import render_warning_panel


def _process_file(content: bytes, filename: str) -> None:
    """Run the full ingestion pipeline and store results in session state."""
    from app.services import (
        step_classify_eligibility,
        step_compute_metrics,
        step_llm_extract,
        step_normalize_from_llm,
        step_parse_raw,
    )

    settings = Settings()
    mandate = st.session_state["mandate"]

    with st.status("Processing file...", expanded=True) as status:
        status.update(label="Parsing raw file...")
        raw_context = step_parse_raw(content, filename, max_rows=settings.ingestion_max_rows)

        status.update(label="Extracting fund data with LLM...")
        llm_result, validation_errors = step_llm_extract(raw_context, settings)

        status.update(label="Normalizing fund universe...")
        universe = step_normalize_from_llm(llm_result, raw_context)

        status.update(label="Computing metrics...")
        fund_metrics = step_compute_metrics(
            universe, None, mandate.min_history_months
        )

        status.update(label="Classifying eligibility...")
        eligibility = step_classify_eligibility(universe, fund_metrics, mandate)

        status.update(label="Processing complete", state="complete", expanded=False)

    st.session_state["uploaded_content"] = content
    st.session_state["uploaded_name"] = filename
    st.session_state["raw_context"] = raw_context
    st.session_state["llm_result"] = llm_result
    st.session_state["llm_validation_errors"] = validation_errors
    st.session_state["universe"] = universe
    st.session_state["fund_metrics"] = fund_metrics
    st.session_state["eligibility"] = eligibility


def _render_review() -> None:
    """Render review & resolve content from session state."""
    llm_result = st.session_state["llm_result"]
    raw_context = st.session_state["raw_context"]
    universe = st.session_state["universe"]
    eligibility = st.session_state["eligibility"]
    validation_errors = st.session_state.get("llm_validation_errors", [])

    # Initialize dismissed warnings
    if "dismissed_warnings" not in st.session_state:
        st.session_state["dismissed_warnings"] = set()

    # Alerts
    render_alerts(
        errors=validation_errors if validation_errors else None,
    )

    # Split into eligible and ineligible
    eligible_names = {e.fund_name for e in eligibility if e.eligible}
    ineligible = [e for e in eligibility if not e.eligible]

    # --- Eligible Funds Section ---
    st.subheader(f"Eligible Funds ({len(eligible_names)})")

    # Build row lookup for fund cards
    row_lookup: dict[int, list[str | None]] = {}
    for raw_row in raw_context.data_rows:
        row_lookup[raw_row.row_index] = raw_row.cells
    for raw_row in raw_context.aggregated_rows:
        row_lookup[raw_row.row_index] = raw_row.cells

    eligible_funds = [f for f in llm_result.funds if f.fund_name in eligible_names]
    render_eligible_table(eligible_funds, raw_context, row_lookup)

    # Warnings for eligible funds only
    if universe.warnings:
        st.markdown("#### Warnings (Eligible Funds)")
        render_warning_panel(
            universe.warnings,
            st.session_state["dismissed_warnings"],
            eligible_fund_names=eligible_names,
        )

    # --- Ineligible Funds Section ---
    if ineligible:
        st.subheader(f"Ineligible Funds ({len(ineligible)})")
        st.caption(
            "These funds failed mandate constraints and will not be "
            "included in grouping or memo generation."
        )
        for e in ineligible:
            reasons = [c.explanation for c in e.failing_constraints]
            with st.expander(f"{e.fund_name} — INELIGIBLE"):
                for reason in reasons:
                    st.write(f"- {reason}")

    # Navigation
    def _save_warning_resolutions() -> None:
        resolutions = []
        dismissed = st.session_state.get("dismissed_warnings", set())
        for idx, w in enumerate(universe.warnings):
            note = st.session_state.get(f"warning_note_{idx}", "")
            if idx in dismissed or note:
                resolutions.append(
                    WarningResolution(
                        category=w.category,
                        fund_name=w.fund_name,
                        original_message=w.message,
                        action="ignored" if idx in dismissed else "acknowledged",
                        analyst_note=note,
                    )
                )
        st.session_state["warning_resolutions"] = resolutions

    render_nav_buttons(
        back_step=0,
        forward_step=2,
        on_forward=_save_warning_resolutions,
        key_prefix="upload",
    )


def render() -> None:
    st.header("Step 2: Upload & Review")

    with st.expander("Supported file format", expanded=False):
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

    uploaded = st.file_uploader("Upload fund universe", type=["csv", "xlsx", "xls"])

    if uploaded:
        content = uploaded.getvalue()
        filename = uploaded.name

        # Check if we need to process (new file or first time)
        needs_processing = (
            "universe" not in st.session_state
            or st.session_state.get("uploaded_name") != filename
        )

        if needs_processing:
            try:
                _process_file(content, filename)
                st.rerun()
            except DecisionEngineError as e:
                st.error(f"Processing failed: {e}")
                return
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                return

        # Show review content
        _render_review()
    else:
        # File cleared — also clear processing results
        if "universe" in st.session_state:
            reset_from(0)
            st.rerun()

        render_nav_buttons(back_step=0, key_prefix="upload_empty")
