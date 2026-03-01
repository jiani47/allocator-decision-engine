"""Tests for build_normalized_universe_from_llm with anomaly detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import InvalidUniverseError
from app.core.schemas import (
    LLMExtractedFund,
    LLMIngestionResult,
    RawFileContext,
    RawRow,
    RowClassification,
)
from app.domains.alt_invest.ingest import build_normalized_universe_from_llm
from app.domains.alt_invest.raw_parser import parse_raw_file

FIXTURES = Path(__file__).parent / "fixtures"


def _make_raw_context() -> RawFileContext:
    """Helper: build a RawFileContext from the clean fixture."""
    content = (FIXTURES / "01_clean_universe.csv").read_bytes()
    return parse_raw_file(content, "01_clean_universe.csv")


def _make_basic_llm_result() -> LLMIngestionResult:
    """Helper: 2 funds, 3 months each, clean data."""
    return LLMIngestionResult(
        funds=[
            LLMExtractedFund(
                fund_name="Alpha Fund",
                strategy="Long/Short Equity",
                liquidity_days=45,
                monthly_returns={
                    "2022-01": 0.012,
                    "2022-02": -0.008,
                    "2022-03": 0.015,
                },
                source_row_indices=[1, 2, 3],
            ),
            LLMExtractedFund(
                fund_name="Beta Fund",
                strategy="Global Macro",
                liquidity_days=90,
                monthly_returns={
                    "2022-01": 0.008,
                    "2022-02": 0.012,
                    "2022-03": -0.005,
                },
                source_row_indices=[4, 5, 6],
            ),
        ],
        interpretation_notes="Extracted 2 funds",
        ambiguities=[],
    )


class TestBuildNormalizedUniverseFromLLM:
    def test_basic_normalization(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)

        assert len(universe.funds) == 2
        assert universe.ingestion_method == "llm"
        assert universe.column_mapping is None
        assert universe.raw_context is not None
        assert universe.llm_interpretation_notes == "Extracted 2 funds"

    def test_fund_names_preserved(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        names = sorted(f.fund_name for f in universe.funds)
        assert names == ["Alpha Fund", "Beta Fund"]

    def test_monthly_returns_preserved(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        alpha = next(f for f in universe.funds if f.fund_name == "Alpha Fund")
        assert alpha.monthly_returns["2022-01"] == pytest.approx(0.012)
        assert alpha.month_count == 3

    def test_strategy_preserved(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        alpha = next(f for f in universe.funds if f.fund_name == "Alpha Fund")
        assert alpha.strategy == "Long/Short Equity"

    def test_liquidity_days_preserved(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        beta = next(f for f in universe.funds if f.fund_name == "Beta Fund")
        assert beta.liquidity_days == 90

    def test_date_range_computed(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        alpha = next(f for f in universe.funds if f.fund_name == "Alpha Fund")
        assert alpha.date_range_start == "2022-01"
        assert alpha.date_range_end == "2022-03"

    def test_file_hash_from_raw_context(self):
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        assert universe.source_file_hash == raw_ctx.file_hash

    def test_outlier_detection_runs(self):
        raw_ctx = _make_raw_context()
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Volatile Fund",
                    monthly_returns={
                        "2022-01": 0.45,  # Outlier: 45%
                        "2022-02": -0.008,
                        "2022-03": 0.015,
                    },
                    source_row_indices=[1, 2, 3],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        outlier_warnings = [w for w in universe.warnings if w.category == "outlier"]
        assert len(outlier_warnings) >= 1

    def test_missing_month_detection_runs(self):
        raw_ctx = _make_raw_context()
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Gappy Fund",
                    monthly_returns={
                        "2022-01": 0.01,
                        # 2022-02 missing
                        "2022-03": 0.015,
                    },
                    source_row_indices=[1, 2],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        missing_warnings = [w for w in universe.warnings if w.category == "missing_month"]
        assert len(missing_warnings) >= 1

    def test_empty_extraction_raises(self):
        raw_ctx = _make_raw_context()
        llm_result = LLMIngestionResult(
            funds=[], interpretation_notes="", ambiguities=[]
        )

        with pytest.raises(InvalidUniverseError, match="no data rows"):
            build_normalized_universe_from_llm(llm_result, raw_ctx)

    def test_single_date_raises(self):
        raw_ctx = _make_raw_context()
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="One Month Fund",
                    monthly_returns={"2022-01": 0.01},
                    source_row_indices=[1],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )

        with pytest.raises(InvalidUniverseError, match="only 1 unique date"):
            build_normalized_universe_from_llm(llm_result, raw_ctx)

    def test_source_row_indices_propagated(self):
        """source_row_indices from LLMExtractedFund should appear on NormalizedFund."""
        raw_ctx = _make_raw_context()
        llm_result = _make_basic_llm_result()

        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        alpha = next(f for f in universe.funds if f.fund_name == "Alpha Fund")
        beta = next(f for f in universe.funds if f.fund_name == "Beta Fund")
        assert alpha.source_row_indices == [1, 2, 3]
        assert beta.source_row_indices == [4, 5, 6]

    def test_source_row_indices_empty_when_missing(self):
        """Funds with no source_row_indices get empty list."""
        raw_ctx = _make_raw_context()
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="No Rows Fund",
                    monthly_returns={"2022-01": 0.01, "2022-02": 0.02, "2022-03": 0.03},
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )
        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        fund = universe.funds[0]
        assert fund.source_row_indices == []

    def test_duplicate_detection_runs(self):
        raw_ctx = _make_raw_context()
        # Create result where duplicate would appear when flattening
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01": 0.01, "2022-02": 0.02},
                    source_row_indices=[1, 2],
                ),
                LLMExtractedFund(
                    fund_name="Fund B",
                    monthly_returns={"2022-01": 0.03, "2022-02": 0.04},
                    source_row_indices=[3, 4],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )

        # This should work fine (no duplicates)
        universe = build_normalized_universe_from_llm(llm_result, raw_ctx)
        assert len(universe.funds) == 2
