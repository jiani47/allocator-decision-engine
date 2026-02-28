"""Tests for CSV ingestion and normalization."""

from pathlib import Path

import pytest

from app.core.exceptions import InvalidUniverseError, SchemaInferenceError
from app.core.hashing import file_hash
from app.domains.alt_invest.adapter import fund_to_return_series
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    infer_column_mapping,
    read_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_and_normalize(filename: str):
    """Helper: read CSV, infer mapping, build universe."""
    content = (FIXTURES / filename).read_bytes()
    df = read_csv(content, filename)
    mapping = infer_column_mapping(df)
    return build_normalized_universe(df, mapping, file_hash(content))


class TestCleanCSV:
    def test_loads_three_funds(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        assert len(universe.funds) == 3

    def test_fund_names(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        names = sorted(f.fund_name for f in universe.funds)
        assert names == ["Atlas L/S Equity", "Birch Global Macro", "Cedar Credit"]

    def test_each_fund_has_24_months(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        for fund in universe.funds:
            assert fund.month_count == 24

    def test_no_error_warnings(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        errors = [w for w in universe.warnings if w.severity == "error"]
        assert len(errors) == 0

    def test_strategy_preserved(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        strategies = {f.fund_name: f.strategy for f in universe.funds}
        assert strategies["Atlas L/S Equity"] == "Long/Short Equity"
        assert strategies["Cedar Credit"] == "Credit"

    def test_liquidity_days_preserved(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        liq = {f.fund_name: f.liquidity_days for f in universe.funds}
        assert liq["Atlas L/S Equity"] == 45
        assert liq["Cedar Credit"] == 30

    def test_returns_are_decimals(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        atlas = next(f for f in universe.funds if f.fund_name == "Atlas L/S Equity")
        # First month return should be 0.012
        first_return = list(atlas.monthly_returns.values())[0]
        assert abs(first_return - 0.012) < 1e-6

    def test_adapter_produces_series(self):
        universe = _load_and_normalize("01_clean_universe.csv")
        atlas = next(f for f in universe.funds if f.fund_name == "Atlas L/S Equity")
        series = fund_to_return_series(atlas)
        assert len(series) == 24
        assert series.index.freqstr == "M"


class TestMessyCSV:
    def test_loads_three_funds(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        assert len(universe.funds) == 3

    def test_fund_names_normalized(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        names = sorted(f.fund_name for f in universe.funds)
        assert "Atlas L/S Equity" in names

    def test_percent_strings_converted(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        atlas = next(f for f in universe.funds if f.fund_name == "Atlas L/S Equity")
        first_return = list(atlas.monthly_returns.values())[0]
        assert abs(first_return - 0.012) < 1e-6

    def test_duplicates_detected(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        dup_warnings = [w for w in universe.warnings if w.category == "duplicate"]
        assert len(dup_warnings) >= 1

    def test_outlier_flagged(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        outlier_warnings = [w for w in universe.warnings if w.category == "outlier"]
        assert len(outlier_warnings) >= 1
        # The 45% return should be flagged
        assert any("45.0%" in w.message for w in outlier_warnings)

    def test_missing_months_detected(self):
        universe = _load_and_normalize("02_messy_universe.csv")
        missing_warnings = [w for w in universe.warnings if w.category == "missing_month"]
        # Cedar Credit is missing 2022-04
        cedar_missing = [w for w in missing_warnings if w.fund_name == "Cedar Credit"]
        assert len(cedar_missing) >= 1


class TestColumnMappingInference:
    def test_clean_csv_mapping(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        assert mapping.fund_name == "fund_name"
        assert mapping.date == "date"
        assert mapping.monthly_return == "monthly_return"

    def test_messy_csv_mapping(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()
        df = read_csv(content, "02_messy_universe.csv")
        mapping = infer_column_mapping(df)
        assert mapping.fund_name == "Fund Name"
        assert mapping.date == "Date"
        assert mapping.monthly_return == "Return (%)"

    def test_missing_required_column_raises(self):
        content = b"col_a,col_b,col_c\n1,2,3\n"
        df = read_csv(content, "bad.csv")
        with pytest.raises(SchemaInferenceError):
            infer_column_mapping(df)


class TestEdgeCases:
    def test_empty_csv_raises(self):
        with pytest.raises(InvalidUniverseError):
            read_csv(b"fund_name,date,monthly_return\n", "empty.csv")

    def test_single_date_raises(self):
        content = b"fund_name,date,monthly_return\nFund A,2022-01-01,0.01\n"
        df = read_csv(content, "single.csv")
        mapping = infer_column_mapping(df)
        with pytest.raises(InvalidUniverseError, match="summary"):
            build_normalized_universe(df, mapping, "abc123")
