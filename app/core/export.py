"""Export decision run to Markdown, JSON, and PDF."""

from __future__ import annotations

import io
import json
import re

from fpdf import FPDF

from app.core.schemas import DecisionRun, FundEligibility, GroupRun, MetricId

# Helvetica supports only Latin-1; replace Unicode with ASCII equivalents for PDF export
_ASCII_REPLACEMENTS = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2022": "-",  # bullet
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
}


def _ascii_safe(text: str) -> str:
    """Replace Unicode chars unsupported by Helvetica with ASCII equivalents."""
    for u, a in _ASCII_REPLACEMENTS.items():
        text = text.replace(u, a)
    return "".join(c if ord(c) < 128 else "?" for c in text)


def export_memo_markdown(decision_run: DecisionRun) -> str:
    """Export the memo + metadata as a Markdown document."""
    lines = [
        f"# IC Memo — Decision Run {decision_run.run_id[:8]}",
        "",
        f"**Run ID:** `{decision_run.run_id}`",
        f"**Timestamp:** {decision_run.timestamp}",
        f"**Input Hash:** `{decision_run.input_hash[:16]}...`",
        f"**Metric Version:** {decision_run.metric_version}",
        f"**Benchmark:** {decision_run.benchmark.symbol if decision_run.benchmark else 'None'}",
        "",
        "---",
        "",
        "## Universe Summary",
        "",
        f"- **Funds evaluated:** {len(decision_run.universe.funds)}",
        f"- **Candidates included:** {sum(1 for rc in decision_run.run_candidates if rc.included)}",
        f"- **Candidates excluded:** {sum(1 for rc in decision_run.run_candidates if not rc.included)}",
        f"- **Validation warnings:** {len(decision_run.universe.warnings)}",
        "",
        "## Mandate Configuration",
        "",
    ]

    mandate = decision_run.mandate
    lines.append(f"- Name: {mandate.name}")
    if mandate.min_liquidity_days is not None:
        lines.append(f"- Min liquidity: {mandate.min_liquidity_days} days")
    if mandate.max_drawdown_tolerance is not None:
        lines.append(f"- Max drawdown tolerance: {mandate.max_drawdown_tolerance:.1%}")
    if mandate.target_volatility is not None:
        lines.append(f"- Target volatility: {mandate.target_volatility:.1%}")
    weights_str = ", ".join(
        f"{mid.value}={w}" for mid, w in mandate.weights.items()
    )
    lines.append(f"- Weights: {weights_str}")

    # Excluded candidates
    excluded = [rc for rc in decision_run.run_candidates if not rc.included]
    if excluded:
        lines.extend(["", "## Excluded Candidates", ""])
        for rc in excluded:
            lines.append(f"- {rc.fund_name}: {rc.exclusion_reason}")

    lines.extend(["", "## Ranked Shortlist", ""])
    lines.append(
        "| Rank | Fund | Return | Vol | Sharpe | Max DD | Score | Constraints |"
    )
    lines.append("|------|------|--------|-----|--------|--------|-------|-------------|")

    for sf in decision_run.ranked_shortlist:
        m = sf.metric_values
        ret = m.get(MetricId.ANNUALIZED_RETURN, 0)
        vol = m.get(MetricId.ANNUALIZED_VOLATILITY, 0)
        sharpe = m.get(MetricId.SHARPE_RATIO, 0)
        dd = m.get(MetricId.MAX_DRAWDOWN, 0)
        status = "Pass" if sf.all_constraints_passed else "FAIL"
        lines.append(
            f"| {sf.rank} | {sf.fund_name} | {ret:.2%} | {vol:.2%} | "
            f"{sharpe:.2f} | {dd:.2%} | {sf.composite_score:.3f} | {status} |"
        )

    if decision_run.group_runs:
        # Per-group sections
        for group_run in decision_run.group_runs:
            group = group_run.group
            lines.extend(["", "---", "", f"## Group: {group.group_name}", ""])
            if group.benchmark_symbol:
                lines.append(f"**Benchmark:** {group.benchmark_symbol}")
            if group.grouping_rationale:
                lines.append(f"**Rationale:** {group.grouping_rationale}")
            lines.append("")

            # Ranked shortlist for this group
            lines.append(f"### Ranked Shortlist — {group.group_name}")
            lines.append("")
            lines.append(
                "| Rank | Fund | Return | Vol | Sharpe | Max DD | Score | Constraints |"
            )
            lines.append("|------|------|--------|-----|--------|--------|-------|-------------|")
            for sf in group_run.ranked_shortlist:
                m = sf.metric_values
                ret = m.get(MetricId.ANNUALIZED_RETURN, 0)
                vol = m.get(MetricId.ANNUALIZED_VOLATILITY, 0)
                sharpe = m.get(MetricId.SHARPE_RATIO, 0)
                dd = m.get(MetricId.MAX_DRAWDOWN, 0)
                status = "Pass" if sf.all_constraints_passed else "FAIL"
                lines.append(
                    f"| {sf.rank} | {sf.fund_name} | {ret:.2%} | {vol:.2%} | "
                    f"{sharpe:.2f} | {dd:.2%} | {sf.composite_score:.3f} | {status} |"
                )

            if group_run.memo:
                lines.extend(["", f"### Memo — {group.group_name}", "", group_run.memo.memo_text])

                if group_run.memo.claims:
                    lines.extend(["", f"### Claims — {group.group_name}", ""])
                    for claim in group_run.memo.claims:
                        metrics_str = ", ".join(m.value for m in claim.referenced_metric_ids)
                        funds_str = ", ".join(claim.referenced_fund_names)
                        lines.append(f"- **[{claim.claim_id}]** {claim.claim_text}")
                        lines.append(f"  - Metrics: {metrics_str}")
                        lines.append(f"  - Funds: {funds_str}")
    else:
        # Single-group format (backward compatible)
        if decision_run.memo:
            lines.extend(["", "---", "", "## Memo", "", decision_run.memo.memo_text])

            if decision_run.memo.claims:
                lines.extend(["", "## Claims", ""])
                for claim in decision_run.memo.claims:
                    metrics_str = ", ".join(m.value for m in claim.referenced_metric_ids)
                    funds_str = ", ".join(claim.referenced_fund_names)
                    lines.append(f"- **[{claim.claim_id}]** {claim.claim_text}")
                    lines.append(f"  - Metrics: {metrics_str}")
                    lines.append(f"  - Funds: {funds_str}")

    lines.extend(["", "---", "", f"*Generated by Equi Decision Engine*"])
    return "\n".join(lines)


def export_memo_pdf(decision_run: DecisionRun) -> bytes:
    """Export the memo + metadata as a PDF document."""
    md = export_memo_markdown(decision_run)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _ascii_safe(f"IC Memo - Decision Run {decision_run.run_id[:8]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    for line in md.split("\n"):
        # Reset cursor to left margin before each line
        pdf.set_x(pdf.l_margin)

        # Skip the top-level title (already rendered)
        if line.startswith("# "):
            continue

        # Section headers
        if line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, _ascii_safe(line.lstrip("# ")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            continue

        if line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, _ascii_safe(line.lstrip("# ")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            continue

        # Table rows
        if line.startswith("|"):
            # Skip separator rows
            if re.match(r"^\|[\s\-|]+\|$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            usable_w = pdf.w - pdf.l_margin - pdf.r_margin
            col_w = usable_w / max(len(cells), 1)
            # Use smaller font for wide tables, skip if still too narrow
            if col_w < 8:
                pdf.set_font("Helvetica", "", 6)
                col_w = usable_w / max(len(cells), 1)
            if col_w < 4:
                # Too many columns to render — skip this table row
                continue
            for cell_text in cells:
                pdf.cell(col_w, 5, _ascii_safe(cell_text[:int(col_w / 2)]), border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            continue

        # Horizontal rule
        if line.startswith("---"):
            pdf.ln(3)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(3)
            continue

        # Bold lines (**text**)
        stripped = line.strip()
        if stripped.startswith("**") and "**" in stripped[2:]:
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(0, 5, _ascii_safe(stripped.replace("**", "")))
            pdf.set_font("Helvetica", "", 9)
            continue

        # Bullet points (use hyphen - Helvetica doesn't support Unicode bullet)
        if stripped.startswith("- "):
            text = _ascii_safe(stripped[2:].replace("**", ""))
            pdf.cell(5, 5, "-")
            pdf.multi_cell(0, 5, text)
            continue

        # Italic / footer
        if stripped.startswith("*") and stripped.endswith("*"):
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, _ascii_safe(stripped.strip("*")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            continue

        # Empty lines
        if not stripped:
            pdf.ln(2)
            continue

        # Regular text
        pdf.multi_cell(0, 5, _ascii_safe(stripped.replace("**", "").replace("`", "")))

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def export_decision_run_json(decision_run: DecisionRun) -> str:
    """Export the full DecisionRun as formatted JSON for archival."""
    return decision_run.model_dump_json(indent=2)
