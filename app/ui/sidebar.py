"""Pipeline progress sidebar."""
import streamlit as st
from app.ui.state import STEPS


def render_sidebar() -> None:
    """Render pipeline progress sidebar."""
    with st.sidebar:
        st.markdown("### Pipeline Progress")
        current = st.session_state["step"]
        for i, name in enumerate(STEPS):
            if i < current:
                st.markdown(f"~~{i+1}. {name}~~")
            elif i == current:
                st.markdown(f"**{i+1}. {name}** <--")
            else:
                st.markdown(f"{i+1}. {name}")

        st.divider()
        if st.button("Start Over"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state["step"] = 0
            st.rerun()
