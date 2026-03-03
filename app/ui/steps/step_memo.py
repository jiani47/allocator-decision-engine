"""Step 3: Memo Generation."""
import streamlit as st
from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.ui.widgets.navigation import render_nav_buttons


def render() -> None:
    st.header("Step 4: IC Memo Generation")
    st.markdown(
        "Generate an IC memo using Claude. "
        "The memo is drafted from the deterministic fact pack."
    )

    gr = st.session_state["group_runs"][0]
    mandate = st.session_state["mandate"]

    # Shortlist size control
    top_k = st.number_input(
        "Funds in memo (top N by rank)",
        min_value=1,
        max_value=50,
        value=mandate.shortlist_top_k,
        help="Only the top N ranked funds will be included in the memo.",
        key="memo_top_k",
    )
    if top_k != mandate.shortlist_top_k:
        mandate = mandate.model_copy(update={"shortlist_top_k": top_k})
        st.session_state["mandate"] = mandate

    if gr.memo:
        st.markdown(gr.memo.memo_text)
        if st.button("Regenerate", key="regen_memo"):
            gr.memo = None
            gr.fact_pack = None
            st.rerun()
    else:
        st.info("No memo generated yet.")
        if st.button("Generate Memo", type="primary", key="gen_memo"):
            try:
                from app.services import step_generate_group_memo

                settings = Settings()
                with st.spinner("Generating memo..."):
                    updated_gr = step_generate_group_memo(
                        gr,
                        st.session_state["universe"],
                        st.session_state["mandate"],
                        settings,
                        warning_resolutions=st.session_state.get(
                            "warning_resolutions"
                        ),
                    )
                st.session_state["group_runs"] = [updated_gr]
                st.rerun()
            except DecisionEngineError as e:
                st.error(f"Memo generation failed: {e}")

    has_memo = gr.memo is not None
    render_nav_buttons(
        back_step=2,
        forward_step=4 if has_memo else None,
        skip_label="Skip to Export",
        skip_step=5,
        key_prefix="memo",
    )
