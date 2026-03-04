"""Session state management for Equi pipeline."""
import streamlit as st

STEPS = [
    "Mandate",
    "Upload & Review",
    "Metrics & Ranking",
    "Memo & Export",
]


def init_state() -> None:
    """Initialize session state if needed."""
    if "step" not in st.session_state:
        st.session_state["step"] = 0


def go_to(step: int) -> None:
    """Navigate to a specific step."""
    st.session_state["step"] = step


def reset_from(step: int) -> None:
    """Clear downstream state when going back."""
    keys_by_step = {
        0: ["universe", "benchmark", "fund_metrics",
            "mandate", "ranked", "run_candidates", "memo", "fact_pack", "decision_run",
            "raw_context", "llm_result", "llm_validation_errors",
            "uploaded_content", "uploaded_name",
            "dismissed_warnings", "warning_resolutions",
            "eligibility", "groups", "group_runs",
            "_benchmark", "_benchmark_ticker"],
        1: ["benchmark", "fund_metrics", "ranked", "run_candidates",
            "memo", "fact_pack", "decision_run", "warning_resolutions",
            "groups", "group_runs", "_benchmark", "_benchmark_ticker"],
        2: ["memo", "fact_pack", "decision_run", "group_runs"],
    }
    for key in keys_by_step.get(step, []):
        st.session_state.pop(key, None)
