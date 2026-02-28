"""Tests for LLM ingestion service: prompt construction, extraction, validation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import LLMIngestionError
from app.core.schemas import LLMExtractedFund, LLMIngestionResult, RawFileContext, RawRow, RowClassification
from app.domains.alt_invest.raw_parser import parse_raw_file
from app.llm.ingestion_service import (
    build_ingestion_prompt,
    extract_funds_via_llm,
    validate_llm_extraction,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _make_raw_context() -> RawFileContext:
    """Helper: build a RawFileContext from the clean fixture."""
    content = (FIXTURES / "01_clean_universe.csv").read_bytes()
    return parse_raw_file(content, "01_clean_universe.csv")


def _make_llm_result() -> LLMIngestionResult:
    """Helper: build a valid LLMIngestionResult."""
    return LLMIngestionResult(
        funds=[
            LLMExtractedFund(
                fund_name="Atlas L/S Equity",
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
                fund_name="Birch Global Macro",
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
        interpretation_notes="Extracted 2 funds from clean CSV",
        ambiguities=[],
    )


class TestBuildIngestionPrompt:
    def test_includes_filename(self):
        ctx = _make_raw_context()
        prompt = build_ingestion_prompt(ctx)
        assert "01_clean_universe.csv" in prompt

    def test_includes_headers(self):
        ctx = _make_raw_context()
        prompt = build_ingestion_prompt(ctx)
        assert "fund_name" in prompt
        assert "monthly_return" in prompt

    def test_includes_data_rows(self):
        ctx = _make_raw_context()
        prompt = build_ingestion_prompt(ctx)
        assert "Atlas L/S Equity" in prompt
        assert "Row " in prompt

    def test_includes_row_count(self):
        ctx = _make_raw_context()
        prompt = build_ingestion_prompt(ctx)
        assert "72 rows" in prompt

    def test_includes_aggregated_rows_section(self):
        csv = b"fund_name,date,return\nFund A,2022-01,0.01\nTotal,,0.01\n"
        ctx = parse_raw_file(csv, "test.csv")
        prompt = build_ingestion_prompt(ctx)
        assert "Aggregated" in prompt
        assert "SKIP" in prompt


class TestExtractFundsViaLLM:
    def test_valid_json_response(self):
        result_data = _make_llm_result().model_dump()
        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps(result_data)

        ctx = _make_raw_context()
        result = extract_funds_via_llm(mock_client, ctx)

        assert len(result.funds) == 2
        assert result.funds[0].fund_name == "Atlas L/S Equity"

    def test_strips_code_fences(self):
        result_data = _make_llm_result().model_dump()
        raw_json = "```json\n" + json.dumps(result_data) + "\n```"
        mock_client = MagicMock()
        mock_client.generate.return_value = raw_json

        ctx = _make_raw_context()
        result = extract_funds_via_llm(mock_client, ctx)
        assert len(result.funds) == 2

    def test_invalid_json_raises(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = "this is not json"

        ctx = _make_raw_context()
        with pytest.raises(LLMIngestionError, match="invalid JSON"):
            extract_funds_via_llm(mock_client, ctx)

    def test_invalid_schema_raises(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({"not": "valid schema"})

        ctx = _make_raw_context()
        with pytest.raises(LLMIngestionError, match="schema validation"):
            extract_funds_via_llm(mock_client, ctx)


class TestValidateLLMExtraction:
    def test_valid_result_no_errors(self):
        result = _make_llm_result()
        errors = validate_llm_extraction(result)
        assert errors == []

    def test_zero_funds_error(self):
        result = LLMIngestionResult(funds=[], interpretation_notes="", ambiguities=[])
        errors = validate_llm_extraction(result)
        assert any("zero funds" in e for e in errors)

    def test_duplicate_fund_names(self):
        result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01": 0.01, "2022-02": 0.02},
                    source_row_indices=[1, 2],
                ),
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01": 0.03, "2022-02": 0.04},
                    source_row_indices=[3, 4],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )
        errors = validate_llm_extraction(result)
        assert any("Duplicate fund name" in e for e in errors)

    def test_percentage_returns_flagged(self):
        result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01": 1.2, "2022-02": -0.8},  # Looks like percentages
                    source_row_indices=[1, 2],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )
        errors = validate_llm_extraction(result)
        assert any("percentage" in e.lower() or "|value| > 1.0" in e for e in errors)

    def test_invalid_date_format(self):
        result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01-01": 0.01, "2022-02": 0.02},  # Bad date
                    source_row_indices=[1, 2],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )
        errors = validate_llm_extraction(result)
        assert any("date format" in e.lower() for e in errors)

    def test_too_few_months(self):
        result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Fund A",
                    monthly_returns={"2022-01": 0.01},  # Only 1 month
                    source_row_indices=[1],
                ),
            ],
            interpretation_notes="",
            ambiguities=[],
        )
        errors = validate_llm_extraction(result)
        assert any("fewer than 2 months" in e for e in errors)
