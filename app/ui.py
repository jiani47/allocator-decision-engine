"""Equi — Allocator Decision Engine (Streamlit UI).

Thin entry point: page config, session state init, sidebar, step router.
All business logic lives in app/services.py.
All UI rendering lives in app/ui/steps/ and app/ui/widgets/.
"""

import streamlit as st

from app.ui.state import init_state
from app.ui.sidebar import render_sidebar
from app.ui.steps import (
    step_mandate,
    step_upload,
    step_ranking,
    step_memo,
)

st.set_page_config(
    page_title="Equi — Allocator Decision Engine",
    layout="wide",
)

init_state()
render_sidebar()

STEP_RENDERERS = [
    step_mandate.render,
    step_upload.render,
    step_ranking.render,
    step_memo.render,
]

STEP_RENDERERS[st.session_state["step"]]()
