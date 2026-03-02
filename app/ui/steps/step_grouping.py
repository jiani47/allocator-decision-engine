"""Step 3: Fund Grouping."""
import streamlit as st
from app.config import Settings
from app.core.exceptions import DecisionEngineError
from app.core.schemas import GroupingCriteria
from app.ui.state import go_to, reset_from


def render() -> None:
    st.header("Step 4: Fund Grouping")

    eligibility = st.session_state["eligibility"]
    eligible_names = [e.fund_name for e in eligibility if e.eligible]

    st.markdown(
        f"**{len(eligible_names)} eligible fund(s)** to classify into peer groups."
    )

    st.subheader("Grouping Criteria")

    # Standard criteria
    standard_options = [
        "Strategy",
        "Geography",
        "Fund Size / AUM",
        "Liquidity Profile",
        "Risk Profile",
    ]
    selected_criteria = st.multiselect(
        "Standard criteria (select one or more)",
        standard_options,
        default=[],
        help="Common grouping dimensions. The LLM uses these as classification axes.",
    )

    # Free text
    free_text = st.text_area(
        "Additional grouping instructions",
        placeholder="e.g., 'Separate value-oriented from growth-oriented funds'",
        help="Natural language instructions for the LLM classifier.",
    )

    # Max groups
    settings = Settings()
    max_groups = st.number_input(
        "Maximum number of groups",
        min_value=1,
        max_value=settings.max_fund_groups,
        value=2,
    )

    # Classify button
    if st.button("Classify Funds into Groups", type="primary"):
        try:
            from app.services import step_group_funds

            criteria = GroupingCriteria(
                standard_criteria=selected_criteria,
                free_text=free_text,
                max_groups=max_groups,
            )

            with st.spinner("Classifying funds with LLM..."):
                grouping_result = step_group_funds(
                    st.session_state["universe"],
                    eligibility,
                    criteria,
                    st.session_state["fund_metrics"],
                    settings,
                )

            st.session_state["grouping_criteria"] = criteria
            st.session_state["grouping_result"] = grouping_result
            st.session_state["groups"] = grouping_result.groups
            go_to(4)
            st.rerun()
        except DecisionEngineError as e:
            st.error(f"Grouping failed: {e}")

    # Show existing grouping result if re-visiting
    if "grouping_result" in st.session_state:
        result = st.session_state["grouping_result"]
        st.divider()
        st.subheader("Current Grouping")
        st.info(f"**Rationale:** {result.rationale}")
        if result.ambiguities:
            st.warning(
                "**Ambiguities:**\n"
                + "\n".join(f"- {a}" for a in result.ambiguities)
            )
        for group in result.groups:
            with st.expander(
                f"{group.group_name} ({len(group.fund_names)} funds)"
            ):
                st.write(f"**Rationale:** {group.grouping_rationale}")
                for fn in group.fund_names:
                    st.write(f"- {fn}")

    # Back button
    if st.button("Back"):
        reset_from(2)
        go_to(2)
        st.rerun()
