"""Step 4: Group Review & Benchmark."""
import streamlit as st
from app.core.schemas import FundGroup
from app.ui.state import go_to, reset_from


def render() -> None:
    st.header("Step 5: Group Review & Benchmark")

    groups: list[FundGroup] = st.session_state["groups"]
    grouping_result = st.session_state["grouping_result"]

    st.info(f"**Overall rationale:** {grouping_result.rationale}")

    # Per-group configuration
    all_fund_names = []
    for g in groups:
        all_fund_names.extend(g.fund_names)

    updated_groups = []
    for gi, group in enumerate(groups):
        st.subheader(f"Group {gi + 1}: {group.group_name}")

        # Editable group name
        new_name = st.text_input(
            "Group name",
            value=group.group_name,
            key=f"group_name_{gi}",
        )

        # Fund list
        st.write(f"**Funds ({len(group.fund_names)}):**")
        for fn in group.fund_names:
            st.write(f"- {fn}")

        # Move fund to another group
        if len(groups) > 1:
            other_group_names = [
                g.group_name for j, g in enumerate(groups) if j != gi
            ]
            fund_to_move = st.selectbox(
                "Move a fund to another group",
                ["(none)"] + group.fund_names,
                key=f"move_fund_{gi}",
            )
            if fund_to_move != "(none)":
                target_group = st.selectbox(
                    f"Move '{fund_to_move}' to",
                    other_group_names,
                    key=f"move_target_{gi}",
                )
                if st.button(f"Move '{fund_to_move}'", key=f"move_btn_{gi}"):
                    # Execute the move
                    for g in groups:
                        if fund_to_move in g.fund_names:
                            g.fund_names.remove(fund_to_move)
                        if g.group_name == target_group:
                            g.fund_names.append(fund_to_move)
                    st.session_state["groups"] = groups
                    st.rerun()

        # Benchmark
        benchmark_symbol = st.text_input(
            "Benchmark ticker",
            value=group.benchmark_symbol or "SPY",
            key=f"benchmark_{gi}",
        )
        skip_benchmark = st.checkbox(
            "Skip benchmark for this group",
            key=f"skip_benchmark_{gi}",
        )

        updated_groups.append(
            FundGroup(
                group_name=new_name,
                group_id=group.group_id,
                fund_names=group.fund_names,
                benchmark_symbol=None if skip_benchmark else benchmark_symbol,
                grouping_rationale=group.grouping_rationale,
            )
        )

        st.divider()

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            reset_from(3)
            go_to(3)
            st.rerun()
    with col2:
        if st.button("Compute Metrics & Rank", type="primary"):
            st.session_state["groups"] = updated_groups
            go_to(5)
            st.rerun()
