"""Step 8: Export & Archive."""
import streamlit as st
from app.services import step_create_run, step_export_json, step_export_markdown
from app.ui.state import go_to


def render() -> None:
    st.header("Step 9: Export & Archive")

    # Build decision run
    if "decision_run" not in st.session_state:
        decision_run = step_create_run(
            universe=st.session_state["universe"],
            mandate=st.session_state["mandate"],
            fund_eligibility=st.session_state.get("eligibility"),
            grouping_criteria=st.session_state.get("grouping_criteria"),
            group_runs=st.session_state.get("group_runs"),
            benchmark=None,
            all_fund_metrics=st.session_state.get("fund_metrics"),
            run_candidates=None,
            ranked_shortlist=None,
            memo=None,
            fact_pack=None,
        )
        st.session_state["decision_run"] = decision_run

    decision_run = st.session_state["decision_run"]

    st.markdown(f"**Run ID:** `{decision_run.run_id}`")
    st.markdown(f"**Timestamp:** {decision_run.timestamp}")
    st.markdown(f"**Metric Version:** {decision_run.metric_version}")
    st.markdown(f"**Input Hash:** `{decision_run.input_hash[:16]}...`")

    # Group summary
    if decision_run.group_runs:
        st.subheader("Groups")
        for gr in decision_run.group_runs:
            st.write(
                f"- **{gr.group.group_name}**: {len(gr.ranked_shortlist)} ranked funds, "
                f"benchmark: {gr.group.benchmark_symbol or 'none'}, "
                f"memo: {'yes' if gr.memo else 'no'}"
            )

    # Export buttons
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
        has_memo = any(
            gr.memo for gr in st.session_state.get("group_runs", [])
        )
        go_to(7 if has_memo else 5)
        st.rerun()
