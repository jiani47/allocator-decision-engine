"""Tests for raw file parsing and row classification."""

from pathlib import Path

from app.core.schemas import RowClassification
from app.domains.alt_invest.raw_parser import (
    _classify_row,
    _detect_header_row,
    _parse_csv_raw,
    parse_raw_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseCSVRaw:
    def test_parses_clean_csv(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        rows = _parse_csv_raw(content)
        # Header + 72 data rows
        assert len(rows) == 73
        # First row is the header
        assert rows[0] == ["fund_name", "date", "monthly_return", "strategy", "liquidity_days"]

    def test_parses_messy_csv(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()
        rows = _parse_csv_raw(content)
        assert len(rows) > 0
        # Header row should have the messy column names
        assert "Fund Name" in rows[0]

    def test_empty_cells_become_none(self):
        content = b"a,b,c\n1,,3\n"
        rows = _parse_csv_raw(content)
        assert rows[1] == ["1", None, "3"]


class TestDetectHeaderRow:
    def test_header_is_first_row_for_clean_csv(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        rows = _parse_csv_raw(content)
        idx = _detect_header_row(rows)
        assert idx == 0

    def test_header_is_first_row_for_messy_csv(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()
        rows = _parse_csv_raw(content)
        idx = _detect_header_row(rows)
        assert idx == 0

    def test_header_with_numeric_prefix_rows(self):
        rows = [
            ["1", "2", "3"],  # numeric row
            ["Fund", "Date", "Return"],  # header row
            ["Atlas", "2022-01-01", "0.012"],  # data row
        ]
        idx = _detect_header_row(rows)
        assert idx == 1


class TestClassifyRow:
    def test_empty_row(self):
        result = _classify_row([None, None, None], ["a", "b", "c"], 5, 0)
        assert result == RowClassification.EMPTY

    def test_whitespace_only_row(self):
        result = _classify_row(["  ", " ", ""], ["a", "b", "c"], 5, 0)
        assert result == RowClassification.EMPTY

    def test_data_row(self):
        result = _classify_row(
            ["Atlas Fund", "2022-01-01", "0.012"],
            ["fund_name", "date", "monthly_return"],
            5, 0,
        )
        assert result == RowClassification.DATA

    def test_aggregated_row_total(self):
        result = _classify_row(
            ["Total", None, "0.15"],
            ["fund_name", "date", "monthly_return"],
            5, 0,
        )
        assert result == RowClassification.AGGREGATED

    def test_aggregated_row_average(self):
        result = _classify_row(
            ["Average Return", None, "0.01"],
            ["fund_name", "date", "monthly_return"],
            5, 0,
        )
        assert result == RowClassification.AGGREGATED

    def test_aggregated_row_ytd(self):
        result = _classify_row(
            ["Fund A", "YTD", "0.12"],
            ["fund_name", "date", "monthly_return"],
            5, 0,
        )
        assert result == RowClassification.AGGREGATED

    def test_row_before_header_is_header(self):
        result = _classify_row(
            ["Some title", None, None],
            ["fund_name", "date", "monthly_return"],
            0, 2,
        )
        assert result == RowClassification.HEADER


class TestParseRawFile:
    def test_clean_csv(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        ctx = parse_raw_file(content, "01_clean_universe.csv")

        assert ctx.filename == "01_clean_universe.csv"
        assert ctx.total_rows == 73
        assert ctx.header_row_index == 0
        assert len(ctx.headers) == 5
        assert "fund_name" in ctx.headers
        assert len(ctx.data_rows) == 72
        assert len(ctx.aggregated_rows) == 0
        assert ctx.file_hash  # Non-empty hash

    def test_messy_csv(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()
        ctx = parse_raw_file(content, "02_messy_universe.csv")

        assert ctx.filename == "02_messy_universe.csv"
        assert len(ctx.data_rows) > 0
        assert "Fund Name" in ctx.headers

    def test_max_rows_truncation(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        ctx = parse_raw_file(content, "test.csv", max_rows=10)
        # Should have at most 9 data rows (10 total - 1 header)
        assert len(ctx.data_rows) <= 9
        assert ctx.total_rows == 73  # Original row count preserved

    def test_all_data_rows_have_correct_classification(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        ctx = parse_raw_file(content, "test.csv")
        for row in ctx.data_rows:
            assert row.classification == RowClassification.DATA

    def test_aggregated_rows_detected(self):
        csv_content = b"fund_name,date,return\nFund A,2022-01,0.01\nTotal,,0.01\n"
        ctx = parse_raw_file(csv_content, "test.csv")
        assert len(ctx.aggregated_rows) == 1
        assert ctx.aggregated_rows[0].classification == RowClassification.AGGREGATED
