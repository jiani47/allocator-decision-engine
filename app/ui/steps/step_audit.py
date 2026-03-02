"""Step 7: Audit Claims."""
import streamlit as st
from app.core.evidence.audit import build_claim_evidence_for_group
from app.ui.state import go_to
from app.ui.widgets.worksheet_viewer import render_worksheet_html


def render() -> None:
    st.header("Step 8: Audit Claims")

    group_runs = st.session_state["group_runs"]
    universe = st.session_state["universe"]

    # Only show groups that have memos
    groups_with_memos = [gr for gr in group_runs if gr.memo]

    if not groups_with_memos:
        st.info("No memos generated yet. Go back to generate memos first.")
        if st.button("Back to Memo"):
            go_to(6)
            st.rerun()
        return

    tab_labels = [gr.group.group_name for gr in groups_with_memos]
    tabs = st.tabs(tab_labels)

    for tab, gr in zip(tabs, groups_with_memos):
        with tab:
            memo = gr.memo
            st.markdown(memo.memo_text)
            st.divider()
            st.subheader("Claims & Evidence")

            if not memo.claims:
                st.info("No claims were extracted from this memo.")
                continue

            # Claim selector
            claim_labels = [
                f"[{c.claim_id}] {c.claim_text[:80]}"
                f"{'...' if len(c.claim_text) > 80 else ''}"
                for c in memo.claims
            ]
            selected_idx = st.selectbox(
                "Select a claim to audit",
                range(len(memo.claims)),
                format_func=lambda i, labels=claim_labels: labels[i],
                key=f"audit_claim_{gr.group.group_id}",
            )
            claim = memo.claims[selected_idx]

            # Two-column layout: evidence + worksheet
            raw_context = universe.raw_context
            has_worksheet = (
                raw_context is not None and len(raw_context.data_rows) > 0
            )

            col_left, col_right = st.columns(
                [3, 2] if has_worksheet else [1, 0.01]
            )

            with col_left:
                st.markdown(f"**Claim:** {claim.claim_text}")
                st.caption(
                    f"Metrics: {', '.join(m.value for m in claim.referenced_metric_ids)} | "
                    f"Funds: {', '.join(claim.referenced_fund_names)}"
                )
                evidence_list = build_claim_evidence_for_group(
                    claim, gr, universe
                )
                if not evidence_list:
                    st.write("No evidence found for this claim.")
                for ev in evidence_list:
                    with st.expander(
                        f"{ev.metric_id.value} — {ev.fund_name}",
                        expanded=True,
                    ):
                        st.write(f"**Value:** `{ev.computed_value:.6f}`")
                        st.write(f"**Formula:** {ev.formula_description}")
                        st.write(
                            f"**Dependencies:** "
                            f"{', '.join(d.value for d in ev.dependencies) or 'none'}"
                        )
                        st.write(
                            f"**Date range:** {ev.date_range_start} to "
                            f"{ev.date_range_end} ({ev.month_count} months)"
                        )
                        st.write("**Sample returns:**")
                        st.json(ev.sample_raw_returns)

            with col_right:
                if has_worksheet:
                    st.markdown("**Source Worksheet**")
                    # Build highlight from group's funds
                    highlight_rows: dict[str, list[int]] = {}
                    fund_lookup = {
                        f.fund_name: f for f in universe.funds
                    }
                    for fund_name in claim.referenced_fund_names:
                        fund = fund_lookup.get(fund_name)
                        if fund and fund.source_row_indices:
                            highlight_rows[fund_name] = (
                                fund.source_row_indices
                            )

                    worksheet_html = render_worksheet_html(
                        raw_context, highlight_rows
                    )
                    st.markdown(worksheet_html, unsafe_allow_html=True)

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Memo"):
            go_to(6)
            st.rerun()
    with col2:
        if st.button("Continue to Export", type="primary"):
            go_to(8)
            st.rerun()
