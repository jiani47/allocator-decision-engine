"""Step 6: Memo Generation."""
import streamlit as st
from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.ui.state import go_to, reset_from


def render() -> None:
    st.header("Step 7: IC Memo Generation")
    st.markdown(
        "Generate one IC memo per group using Claude. "
        "Each memo is drafted from the deterministic fact pack for that group."
    )

    group_runs = st.session_state["group_runs"]

    tab_labels = [f"{gr.group.group_name}" for gr in group_runs]
    tabs = st.tabs(tab_labels)

    for tab, gr in zip(tabs, group_runs):
        with tab:
            if gr.memo:
                st.markdown(gr.memo.memo_text)
                if st.button(
                    "Regenerate", key=f"regen_memo_{gr.group.group_id}"
                ):
                    gr.memo = None
                    gr.fact_pack = None
                    st.rerun()
            else:
                st.info(f"No memo generated yet for {gr.group.group_name}.")
                if st.button(
                    f"Generate Memo for {gr.group.group_name}",
                    type="primary",
                    key=f"gen_memo_{gr.group.group_id}",
                ):
                    try:
                        from app.services import step_generate_group_memo

                        settings = Settings()
                        with st.spinner(
                            f"Generating memo for {gr.group.group_name}..."
                        ):
                            updated_gr = step_generate_group_memo(
                                gr,
                                st.session_state["universe"],
                                st.session_state["mandate"],
                                settings,
                                warning_resolutions=st.session_state.get(
                                    "warning_resolutions"
                                ),
                            )
                        # Update in place
                        idx = group_runs.index(gr)
                        group_runs[idx] = updated_gr
                        st.session_state["group_runs"] = group_runs
                        st.rerun()
                    except DecisionEngineError as e:
                        st.error(f"Memo generation failed: {e}")

    # Navigation
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Back", key="memo_back"):
            reset_from(5)
            go_to(5)
            st.rerun()
    with col2:
        if st.button("Skip to Export", key="memo_skip"):
            go_to(8)
            st.rerun()
    with col3:
        # Only advance if at least one memo exists
        has_memo = any(gr.memo for gr in group_runs)
        if has_memo:
            if st.button("Audit Claims", type="primary", key="to_audit"):
                go_to(7)
                st.rerun()
