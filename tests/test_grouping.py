"""Tests for LLM-powered fund grouping service."""

import json
from unittest.mock import MagicMock

import pytest

from app.core.schemas import (
    FundMetrics,
    GroupingCriteria,
    LLMGroupingResult,
    MetricId,
    MetricResult,
    NormalizedFund,
    RawFileContext,
    RawRow,
    RowClassification,
)
from app.llm.grouping_service import (
    build_grouping_prompt,
    classify_funds_into_groups,
    validate_grouping,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_funds() -> list[NormalizedFund]:
    """Create a small set of test funds."""
    return [
        NormalizedFund(
            fund_name="Alpha L/S Equity",
            strategy="Long/Short Equity",
            liquidity_days=45,
            management_fee=0.02,
            performance_fee=0.20,
            monthly_returns={"2022-01": 0.01, "2022-02": -0.005},
            date_range_start="2022-01",
            date_range_end="2022-02",
            month_count=2,
        ),
        NormalizedFund(
            fund_name="Beta Global Macro",
            strategy="Global Macro",
            liquidity_days=90,
            management_fee=0.015,
            performance_fee=0.15,
            monthly_returns={"2022-01": 0.02, "2022-02": 0.01},
            date_range_start="2022-01",
            date_range_end="2022-02",
            month_count=2,
        ),
        NormalizedFund(
            fund_name="Gamma Credit",
            strategy="Credit",
            liquidity_days=30,
            management_fee=0.01,
            performance_fee=0.10,
            monthly_returns={"2022-01": 0.005, "2022-02": 0.003},
            date_range_start="2022-01",
            date_range_end="2022-02",
            month_count=2,
        ),
        NormalizedFund(
            fund_name="Delta Equity",
            strategy="Long/Short Equity",
            liquidity_days=60,
            management_fee=0.02,
            performance_fee=0.20,
            monthly_returns={"2022-01": 0.015, "2022-02": -0.01},
            date_range_start="2022-01",
            date_range_end="2022-02",
            month_count=2,
        ),
    ]


def _make_metrics(funds: list[NormalizedFund]) -> list[FundMetrics]:
    """Create mock metrics for each fund."""
    metrics = []
    for fund in funds:
        metrics.append(
            FundMetrics(
                fund_name=fund.fund_name,
                metric_results=[
                    MetricResult(
                        metric_id=MetricId.ANNUALIZED_RETURN,
                        value=0.08,
                        period_start="2022-01",
                        period_end="2022-02",
                        formula_text="ann_return",
                    ),
                    MetricResult(
                        metric_id=MetricId.ANNUALIZED_VOLATILITY,
                        value=0.12,
                        period_start="2022-01",
                        period_end="2022-02",
                        formula_text="ann_vol",
                    ),
                    MetricResult(
                        metric_id=MetricId.SHARPE_RATIO,
                        value=0.67,
                        period_start="2022-01",
                        period_end="2022-02",
                        formula_text="sharpe",
                    ),
                    MetricResult(
                        metric_id=MetricId.MAX_DRAWDOWN,
                        value=-0.10,
                        period_start="2022-01",
                        period_end="2022-02",
                        formula_text="max_dd",
                    ),
                ],
                date_range_start="2022-01",
                date_range_end="2022-02",
                month_count=2,
            )
        )
    return metrics


def _make_criteria(max_groups: int = 2) -> GroupingCriteria:
    return GroupingCriteria(
        standard_criteria=["strategy", "liquidity"],
        free_text="Group equity strategies together",
        max_groups=max_groups,
    )


def _fund_names(funds: list[NormalizedFund]) -> set[str]:
    return {f.fund_name for f in funds}


def _valid_grouping_json(funds: list[NormalizedFund]) -> str:
    """Return a valid LLM response with 2 groups."""
    return json.dumps(
        {
            "groups": [
                {
                    "group_name": "Equity Strategies",
                    "group_id": "group_1",
                    "fund_names": ["Alpha L/S Equity", "Delta Equity"],
                    "grouping_rationale": "Both are long/short equity strategies.",
                },
                {
                    "group_name": "Macro and Credit",
                    "group_id": "group_2",
                    "fund_names": ["Beta Global Macro", "Gamma Credit"],
                    "grouping_rationale": "Non-equity strategies with different risk profiles.",
                },
            ],
            "rationale": "Grouped by primary strategy type.",
            "ambiguities": [],
        }
    )


# ---------------------------------------------------------------------------
# Tests: build_grouping_prompt
# ---------------------------------------------------------------------------


class TestBuildGroupingPrompt:
    def test_prompt_contains_fund_names(self):
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()
        prompt = build_grouping_prompt(funds, None, criteria, metrics)
        for fund in funds:
            assert fund.fund_name in prompt

    def test_prompt_contains_criteria(self):
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()
        prompt = build_grouping_prompt(funds, None, criteria, metrics)
        assert "strategy" in prompt
        assert "liquidity" in prompt
        assert "Group equity strategies together" in prompt

    def test_prompt_contains_max_groups(self):
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria(max_groups=3)
        prompt = build_grouping_prompt(funds, None, criteria, metrics)
        assert "3" in prompt

    def test_prompt_contains_metrics(self):
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()
        prompt = build_grouping_prompt(funds, None, criteria, metrics)
        assert "Annualized return" in prompt
        assert "Sharpe ratio" in prompt
        assert "Max drawdown" in prompt


# ---------------------------------------------------------------------------
# Tests: classify_funds_into_groups
# ---------------------------------------------------------------------------


class TestClassifyFundsIntoGroups:
    def test_valid_grouping_parsed(self):
        """Mock LLM returns valid JSON; parsing and validation succeed."""
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()

        mock_client = MagicMock()
        mock_client.generate.return_value = _valid_grouping_json(funds)

        result = classify_funds_into_groups(
            mock_client, funds, None, criteria, metrics
        )

        assert isinstance(result, LLMGroupingResult)
        assert len(result.groups) == 2
        assert result.groups[0].group_name == "Equity Strategies"
        assert "Alpha L/S Equity" in result.groups[0].fund_names
        assert "Delta Equity" in result.groups[0].fund_names
        assert "Beta Global Macro" in result.groups[1].fund_names

    def test_code_fence_stripped(self):
        """LLM sometimes wraps JSON in code fences."""
        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()

        mock_client = MagicMock()
        mock_client.generate.return_value = (
            "```json\n" + _valid_grouping_json(funds) + "\n```"
        )

        result = classify_funds_into_groups(
            mock_client, funds, None, criteria, metrics
        )
        assert len(result.groups) == 2

    def test_invalid_json_raises(self):
        """LLM returns invalid JSON; should raise FundGroupingError."""
        from app.core.exceptions import FundGroupingError

        funds = _make_funds()
        metrics = _make_metrics(funds)
        criteria = _make_criteria()

        mock_client = MagicMock()
        mock_client.generate.return_value = "This is not valid JSON at all"

        with pytest.raises(FundGroupingError, match="invalid JSON"):
            classify_funds_into_groups(
                mock_client, funds, None, criteria, metrics
            )


# ---------------------------------------------------------------------------
# Tests: validate_grouping
# ---------------------------------------------------------------------------


class TestValidateGrouping:
    def test_valid_grouping_passes(self):
        """All funds present in exactly one group, within max_groups."""
        funds = _make_funds()
        result = LLMGroupingResult.model_validate(json.loads(_valid_grouping_json(funds)))
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert errors == []

    def test_missing_fund_detected(self):
        """A fund is missing from the grouping result."""
        funds = _make_funds()
        # Only include 3 of 4 funds
        result = LLMGroupingResult.model_validate(
            {
                "groups": [
                    {
                        "group_name": "Group A",
                        "group_id": "group_1",
                        "fund_names": ["Alpha L/S Equity", "Delta Equity"],
                        "grouping_rationale": "Equity",
                    },
                    {
                        "group_name": "Group B",
                        "group_id": "group_2",
                        "fund_names": ["Beta Global Macro"],
                        "grouping_rationale": "Macro",
                    },
                ],
                "rationale": "Strategy-based",
                "ambiguities": [],
            }
        )
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert len(errors) == 1
        assert "Gamma Credit" in errors[0]

    def test_duplicate_fund_detected(self):
        """A fund appears in multiple groups."""
        funds = _make_funds()
        result = LLMGroupingResult.model_validate(
            {
                "groups": [
                    {
                        "group_name": "Group A",
                        "group_id": "group_1",
                        "fund_names": ["Alpha L/S Equity", "Delta Equity", "Beta Global Macro"],
                        "grouping_rationale": "Equity",
                    },
                    {
                        "group_name": "Group B",
                        "group_id": "group_2",
                        "fund_names": ["Beta Global Macro", "Gamma Credit"],
                        "grouping_rationale": "Macro",
                    },
                ],
                "rationale": "Strategy-based",
                "ambiguities": [],
            }
        )
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert len(errors) == 1
        assert "Beta Global Macro" in errors[0]

    def test_too_many_groups_detected(self):
        """More groups than max_groups."""
        funds = _make_funds()
        result = LLMGroupingResult.model_validate(
            {
                "groups": [
                    {
                        "group_name": "Group A",
                        "group_id": "group_1",
                        "fund_names": ["Alpha L/S Equity"],
                        "grouping_rationale": "Equity 1",
                    },
                    {
                        "group_name": "Group B",
                        "group_id": "group_2",
                        "fund_names": ["Delta Equity"],
                        "grouping_rationale": "Equity 2",
                    },
                    {
                        "group_name": "Group C",
                        "group_id": "group_3",
                        "fund_names": ["Beta Global Macro", "Gamma Credit"],
                        "grouping_rationale": "Others",
                    },
                ],
                "rationale": "Fine-grained",
                "ambiguities": [],
            }
        )
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert len(errors) == 1
        assert "3 groups" in errors[0]
        assert "max_groups=2" in errors[0]

    def test_empty_groups_detected(self):
        """All groups exist but are empty."""
        result = LLMGroupingResult.model_validate(
            {
                "groups": [
                    {
                        "group_name": "Empty Group",
                        "group_id": "group_1",
                        "fund_names": [],
                        "grouping_rationale": "Nothing here",
                    },
                ],
                "rationale": "No assignments made",
                "ambiguities": [],
            }
        )
        funds = _make_funds()
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert any("empty" in e.lower() for e in errors)

    def test_zero_groups_detected(self):
        """LLM returns zero groups."""
        result = LLMGroupingResult.model_validate(
            {
                "groups": [],
                "rationale": "Could not determine groups",
                "ambiguities": [],
            }
        )
        funds = _make_funds()
        errors = validate_grouping(result, _fund_names(funds), max_groups=2)
        assert any("zero groups" in e.lower() for e in errors)
