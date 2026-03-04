"""Validation warning panel with ack/ignore controls."""
import streamlit as st
from app.core.schemas import ValidationWarning


def render_warning_panel(
    warnings: list[ValidationWarning],
    dismissed: set[int],
    eligible_fund_names: set[str] | None = None,
) -> None:
    """Render per-warning expanders with ack/ignore buttons and notes."""
    if not warnings:
        st.success("No validation warnings.")
        return

    active_count = sum(1 for i in range(len(warnings)) if i not in dismissed)
    st.caption(f"{active_count} active warning(s), {len(dismissed)} ignored")

    for idx, w in enumerate(warnings):
        # Skip warnings for ineligible funds if filtering
        if eligible_fund_names is not None and w.fund_name and w.fund_name not in eligible_fund_names:
            continue

        is_dismissed = idx in dismissed
        label_prefix = "~~" if is_dismissed else ""
        label_suffix = " (ignored)" if is_dismissed else ""
        label = (
            f"{label_prefix}[{w.category}] "
            f"{w.fund_name or 'General'}{label_suffix}{label_prefix}"
        )
        with st.expander(label, expanded=not is_dismissed):
            st.write(w.message)
            if w.row_indices:
                st.write(f"Affected rows: {w.row_indices}")

            wcol1, wcol2 = st.columns([1, 3])
            with wcol1:
                if is_dismissed:
                    if st.button("Restore", key=f"restore_warning_{idx}"):
                        st.session_state["dismissed_warnings"].discard(idx)
                        if f"warning_note_{idx}" in st.session_state:
                            del st.session_state[f"warning_note_{idx}"]
                        st.rerun()
                else:
                    if st.button("Ignore", key=f"ignore_warning_{idx}"):
                        st.session_state["dismissed_warnings"].add(idx)
                        st.rerun()
            with wcol2:
                note_key = f"warning_note_{idx}"
                if st.session_state.get(note_key):
                    st.text_input(
                        "Analyst note",
                        key=note_key,
                    )
                else:
                    if st.button("Resolve with Note", key=f"resolve_note_{idx}"):
                        st.session_state[note_key] = " "
                        st.rerun()
