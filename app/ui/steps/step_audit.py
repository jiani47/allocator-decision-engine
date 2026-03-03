"""Step 4: Audit Claims."""
import streamlit as st
from app.core.evidence.audit import build_claim_evidence_for_group
from app.ui.widgets.navigation import render_nav_buttons
from app.ui.widgets.worksheet_viewer import render_worksheet_html


def render() -> None:
    st.header("Step 5: Audit Claims")

    gr = st.session_state["group_runs"][0]
    universe = st.session_state["universe"]

    if not gr.memo:
        st.info("No memo generated yet. Go back to generate a memo first.")
        render_nav_buttons(back_step=3, key_prefix="audit_empty")
        return

    memo = gr.memo
    st.markdown(memo.memo_text)
    st.divider()
    st.subheader("Claims & Evidence")

    if not memo.claims:
        st.info("No claims were extracted from this memo.")
        render_nav_buttons(back_step=3, forward_step=5, key_prefix="audit")
        return

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
        key="audit_claim",
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
        evidence_list = build_claim_evidence_for_group(claim, gr, universe)
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
            highlight_rows: dict[str, list[int]] = {}
            fund_lookup = {f.fund_name: f for f in universe.funds}
            for fund_name in claim.referenced_fund_names:
                fund = fund_lookup.get(fund_name)
                if fund and fund.source_row_indices:
                    highlight_rows[fund_name] = fund.source_row_indices

            worksheet_html = render_worksheet_html(
                raw_context, highlight_rows
            )
            st.markdown(worksheet_html, unsafe_allow_html=True)

    render_nav_buttons(back_step=3, forward_step=5, key_prefix="audit")
