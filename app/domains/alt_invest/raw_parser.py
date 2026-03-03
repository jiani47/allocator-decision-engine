"""Raw file parsing and row classification for LLM-based ingestion."""

from __future__ import annotations

import csv
import io
import logging
import re

from app.core.hashing import file_hash as compute_file_hash
from app.core.schemas import RawFileContext, RawRow, RowClassification

logger = logging.getLogger("equi.raw_parser")

_AGGREGATED_KEYWORDS = {"total", "average", "avg", "sum", "ytd", "cumulative", "grand total"}


def parse_raw_file(
    file_content: bytes,
    filename: str,
    max_rows: int = 2000,
) -> RawFileContext:
    """Parse a CSV or Excel file into raw rows with classification.

    Returns a RawFileContext preserving headers, data rows, and
    aggregated rows for downstream LLM extraction.
    """
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        raw_rows = _parse_excel_raw(file_content)
    else:
        raw_rows = _parse_csv_raw(file_content)

    if not raw_rows:
        raise ValueError(f"File '{filename}' produced no rows")

    # Truncate to max_rows
    total_rows = len(raw_rows)
    raw_rows = raw_rows[:max_rows]

    header_idx = _detect_header_row(raw_rows)
    headers = [str(c) if c is not None else "" for c in raw_rows[header_idx]]

    data_rows: list[RawRow] = []
    aggregated_rows: list[RawRow] = []
    empty_rows: list[RawRow] = []

    for i, cells in enumerate(raw_rows):
        if i == header_idx:
            continue
        classification = _classify_row(cells, headers, i, header_idx)
        row = RawRow(row_index=i, cells=cells, classification=classification)
        if classification == RowClassification.DATA:
            data_rows.append(row)
        elif classification == RowClassification.AGGREGATED:
            aggregated_rows.append(row)
        elif classification == RowClassification.EMPTY:
            empty_rows.append(row)

    fhash = compute_file_hash(file_content)

    logger.info(
        "Parsed %s: %d total rows, header at row %d, %d data rows, %d aggregated, %d empty",
        filename,
        total_rows,
        header_idx,
        len(data_rows),
        len(aggregated_rows),
        len(empty_rows),
    )

    return RawFileContext(
        filename=filename,
        file_hash=fhash,
        headers=headers,
        header_row_index=header_idx,
        data_rows=data_rows,
        aggregated_rows=aggregated_rows,
        empty_rows=empty_rows,
        total_rows=total_rows,
    )


def _parse_csv_raw(file_content: bytes) -> list[list[str | None]]:
    """Parse CSV bytes into a list of row cell lists."""
    text = file_content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows: list[list[str | None]] = []
    for row in reader:
        rows.append([c if c.strip() != "" else None for c in row])
    return rows


def _parse_excel_raw(file_content: bytes) -> list[list[str | None]]:
    """Parse Excel bytes into a list of row cell lists using openpyxl."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
    ws = wb.active
    rows: list[list[str | None]] = []
    for row in ws.iter_rows(values_only=True):
        cells = [str(c) if c is not None else None for c in row]
        rows.append(cells)
    wb.close()
    return rows


def _detect_header_row(rows: list[list[str | None]], max_scan: int = 10) -> int:
    """Detect the header row by scoring rows by ratio of non-numeric text cells.

    Scans the first max_scan rows and returns the index of the row with the
    highest ratio of text (non-numeric, non-empty) cells. In case of ties,
    returns the first such row.
    """
    best_idx = 0
    best_score = -1.0

    for i, cells in enumerate(rows[:max_scan]):
        if not cells:
            continue
        non_empty = [c for c in cells if c is not None and c.strip()]
        if not non_empty:
            continue
        text_count = sum(1 for c in non_empty if not _is_numeric(c))
        score = text_count / len(non_empty)
        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx


def _is_numeric(value: str) -> bool:
    """Check if a string looks numeric (including percentages and dates with numbers)."""
    stripped = value.strip().rstrip("%")
    try:
        float(stripped)
        return True
    except ValueError:
        pass
    # Match date-like patterns: 2022-01-01, 01/01/2022, etc.
    if re.match(r"^\d{1,4}[/\-]\d{1,2}([/\-]\d{1,4})?$", stripped):
        return True
    return False


def _classify_row(
    cells: list[str | None],
    headers: list[str],
    row_index: int,
    header_row_index: int,
) -> RowClassification:
    """Classify a single row based on its content."""
    # Rows before header are treated as header
    if row_index < header_row_index:
        return RowClassification.HEADER

    # Check for empty row
    non_empty = [c for c in cells if c is not None and str(c).strip()]
    if not non_empty:
        return RowClassification.EMPTY

    # Check for aggregated keywords
    cell_text = " ".join(str(c).lower() for c in cells if c is not None)
    for keyword in _AGGREGATED_KEYWORDS:
        if keyword in cell_text:
            return RowClassification.AGGREGATED

    return RowClassification.DATA
