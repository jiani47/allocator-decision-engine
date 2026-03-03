"""Excel-like worksheet viewer with row highlighting."""
import html as html_lib
from app.core.schemas import RawFileContext

HIGHLIGHT_COLORS = [
    ("#DCE6F1", "#4472C4"),  # light blue / blue label
    ("#FFF2CC", "#BF8F00"),  # amber / dark amber label
    ("#E2EFDA", "#548235"),  # green / dark green label
    ("#FCE4EC", "#C62828"),  # pink / dark red label
    ("#E8EAF6", "#283593"),  # indigo / dark indigo label
]


def get_highlight_rows_for_claim(
    claim, decision_run,
) -> dict[str, list[int]]:
    """Return {fund_name: [row_indices]} for all funds referenced in a claim."""
    highlight: dict[str, list[int]] = {}
    universe = decision_run.universe
    fund_lookup = {f.fund_name: f for f in universe.funds}
    for fund_name in claim.referenced_fund_names:
        fund = fund_lookup.get(fund_name)
        if fund and fund.source_row_indices:
            highlight[fund_name] = fund.source_row_indices
    return highlight


def render_worksheet_html(
    raw_context: RawFileContext,
    highlight_rows: dict[str, list[int]],
) -> str:
    """Build an Excel-like HTML table from RawFileContext with highlighted rows."""
    # Build color mapping per fund
    fund_color_map: dict[str, tuple[str, str]] = {}
    for i, fund_name in enumerate(highlight_rows):
        fund_color_map[fund_name] = HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]

    # Invert to row_index -> (bg_color, fund_name)
    row_highlight: dict[int, tuple[str, str]] = {}
    for fund_name, indices in highlight_rows.items():
        bg, _ = fund_color_map[fund_name]
        for ri in indices:
            row_highlight[ri] = (bg, fund_name)

    # Collect all rows (data + aggregated + empty), sorted by row_index
    all_rows = list(raw_context.data_rows) + list(raw_context.aggregated_rows) + list(raw_context.empty_rows)
    all_rows.sort(key=lambda r: r.row_index)

    num_cols = len(raw_context.headers)

    # CSS
    css = """
<style>
.ws-container { max-height:600px; overflow-y:auto; border:1px solid #CCCCCC; }
.ws-table { border-collapse:collapse; font-family:monospace; font-size:13px; width:100%; }
.ws-table th {
    background:#4472C4; color:white; padding:6px 10px; text-align:left;
    border:1px solid #E0E0E0; position:sticky; top:0; z-index:1;
}
.ws-table td { padding:4px 10px; border:1px solid #E0E0E0; white-space:nowrap; }
.ws-rownum { background:#F0F0F0; color:#888; text-align:center; font-size:12px; min-width:40px; }
.ws-row-even { background:#FFFFFF; }
.ws-row-odd { background:#F9F9F9; }
</style>
"""

    # Header row
    header_cells = '<th class="ws-rownum">#</th>'
    for h in raw_context.headers:
        header_cells += f"<th>{html_lib.escape(str(h))}</th>"
    table_header = f"<tr>{header_cells}</tr>"

    # Data rows
    body_rows = []
    for idx, raw_row in enumerate(all_rows):
        ri = raw_row.row_index
        if ri in row_highlight:
            bg_color, fund_name = row_highlight[ri]
            style = f'style="background:{bg_color};"'
            tooltip = f' title="Fund: {html_lib.escape(fund_name)}"'
        else:
            stripe = "ws-row-even" if idx % 2 == 0 else "ws-row-odd"
            style = f'class="{stripe}"'
            tooltip = ""

        cells_html = f'<td class="ws-rownum">{ri}</td>'
        for ci in range(num_cols):
            val = raw_row.cells[ci] if ci < len(raw_row.cells) else None
            cell_text = html_lib.escape(str(val)) if val is not None else ""
            cells_html += f"<td>{cell_text}</td>"

        body_rows.append(f"<tr {style}{tooltip}>{cells_html}</tr>")

    table_html = (
        css
        + '<div class="ws-container">'
        + f'<table class="ws-table">{table_header}{"".join(body_rows)}</table>'
        + "</div>"
    )

    # Legend
    if fund_color_map:
        legend_items = []
        for fund_name, (bg, label_color) in fund_color_map.items():
            legend_items.append(
                f'<span style="display:inline-block;width:14px;height:14px;'
                f"background:{bg};border:1px solid {label_color};"
                f'vertical-align:middle;margin-right:4px;"></span>'
                f'<span style="color:{label_color};margin-right:12px;">'
                f"{html_lib.escape(fund_name)}</span>"
            )
        table_html += '<div style="margin-top:8px;font-size:13px;">' + "".join(legend_items) + "</div>"

    return table_html
