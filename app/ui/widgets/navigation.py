"""Reusable navigation button widget."""
from typing import Callable

import streamlit as st
from app.ui.state import go_to, reset_from


def render_nav_buttons(
    back_step: int | None = None,
    forward_step: int | None = None,
    forward_disabled: bool = False,
    forward_warning: str | None = None,
    on_forward: Callable[[], None] | None = None,
    skip_label: str | None = None,
    skip_step: int | None = None,
    key_prefix: str = "nav",
) -> None:
    """Render consistent Go back / Continue button row.

    Args:
        back_step: Step index to navigate back to (with reset). None hides the button.
        forward_step: Step index to navigate forward to. None hides the button.
        forward_disabled: Disable the Continue button.
        forward_warning: Warning message shown when forward is disabled.
        on_forward: Callback executed before forward navigation (e.g. save state).
        skip_label: Label for an optional middle skip button.
        skip_step: Step index for the skip button.
        key_prefix: Unique key prefix to avoid Streamlit duplicate key errors.
    """
    has_back = back_step is not None
    has_skip = skip_label and skip_step is not None
    has_forward = forward_step is not None

    if not (has_back or has_skip or has_forward):
        return

    # Fixed 3-column layout: back on left, skip in center, forward on right.
    col_left, col_mid, col_right = st.columns(3)

    if has_back:
        with col_left:
            if st.button("Go back", key=f"{key_prefix}_back"):
                reset_from(back_step)
                go_to(back_step)
                st.rerun()

    if has_skip:
        with col_mid:
            if st.button(skip_label, key=f"{key_prefix}_skip"):
                go_to(skip_step)
                st.rerun()

    if has_forward:
        with col_right:
            if forward_warning and forward_disabled:
                st.warning(forward_warning)
            if st.button(
                "Continue",
                type="primary",
                disabled=forward_disabled,
                key=f"{key_prefix}_forward",
            ):
                if on_forward:
                    on_forward()
                go_to(forward_step)
                st.rerun()
