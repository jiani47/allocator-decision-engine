"""Alert block widgets for notes, ambiguities, and errors."""
import streamlit as st


def render_alerts(
    notes: str | list[str] | None = None,
    ambiguities: list[str] | None = None,
    errors: list[str] | None = None,
) -> None:
    """Render info/warning/error alert blocks."""
    if notes:
        if isinstance(notes, list):
            items = notes
        else:
            # Split string into bullet points by newline or sentence boundary
            items = [s.strip() for s in notes.replace(". ", ".\n").split("\n") if s.strip()]
        st.info(
            "**Interpretation:**\n"
            + "\n".join(f"- {item}" for item in items)
        )
    if ambiguities:
        st.warning(
            "**Ambiguities detected:**\n"
            + "\n".join(f"- {a}" for a in ambiguities)
        )
    if errors:
        st.error(
            "**Validation issues:**\n"
            + "\n".join(f"- {e}" for e in errors)
        )
