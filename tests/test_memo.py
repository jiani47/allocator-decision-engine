"""Tests for memo generation, fact pack, and claim validation."""

import json
from unittest.mock import MagicMock

import pytest

from app.core.evidence.fact_pack import build_fact_pack, build_memo_prompt
from app.core.exceptions import MemoGenerationError
from app.core.schemas import (
    Claim,
    ConstraintResult,
    FactPack,
    MandateConfig,
    MemoOutput,
    MetricId,
    NormalizedFund,
    NormalizedUniverse,
    ColumnMapping,
    ScoreComponent,
    ScoredFund,
    WarningResolution,
)
from app.llm.memo_service import generate_memo, validate_claims


def _make_shortlist() -> list[ScoredFund]:
    return [
        ScoredFund(
            fund_name="Atlas L/S Equity",
            metric_values={
                MetricId.ANNUALIZED_RETURN: 0.08,
                MetricId.ANNUALIZED_VOLATILITY: 0.12,
                MetricId.SHARPE_RATIO: 0.67,
                MetricId.MAX_DRAWDOWN: -0.10,
                MetricId.BENCHMARK_CORRELATION: 0.75,
            },
            score_breakdown=[
                ScoreComponent(
                    metric_id=MetricId.ANNUALIZED_RETURN,
                    raw_value=0.08,
                    normalized_value=0.8,
                    weight=0.4,
                    weighted_contribution=0.32,
                ),
                ScoreComponent(
                    metric_id=MetricId.SHARPE_RATIO,
                    raw_value=0.67,
                    normalized_value=0.7,
                    weight=0.4,
                    weighted_contribution=0.28,
                ),
                ScoreComponent(
                    metric_id=MetricId.MAX_DRAWDOWN,
                    raw_value=-0.10,
                    normalized_value=0.9,
                    weight=0.2,
                    weighted_contribution=0.18,
                ),
            ],
            composite_score=0.78,
            rank=1,
            constraint_results=[
                ConstraintResult(
                    constraint_name="max_drawdown",
                    passed=True,
                    explanation="Within tolerance",
                )
            ],
            all_constraints_passed=True,
        ),
    ]


def _make_universe() -> NormalizedUniverse:
    return NormalizedUniverse(
        funds=[
            NormalizedFund(
                fund_name="Atlas L/S Equity",
                strategy="Long/Short Equity",
                liquidity_days=45,
                management_fee=None,
                performance_fee=None,
                monthly_returns={"2022-01": 0.01, "2022-02": -0.005},
                date_range_start="2022-01",
                date_range_end="2022-02",
                month_count=2,
            )
        ],
        warnings=[],
        source_file_hash="abc123",
        column_mapping=ColumnMapping(
            fund_name="fund_name", date="date", monthly_return="monthly_return"
        ),
        normalization_timestamp="2024-01-01T00:00:00",
    )


def _make_fact_pack() -> FactPack:
    return build_fact_pack(
        run_id="test-run-1",
        shortlist=_make_shortlist(),
        universe=_make_universe(),
        mandate=MandateConfig(),
        benchmark_symbol="SPY",
    )


class TestFactPack:
    def test_construction(self):
        fp = _make_fact_pack()
        assert fp.run_id == "test-run-1"
        assert len(fp.shortlist) == 1
        assert fp.benchmark_symbol == "SPY"
        assert fp.universe_summary["total_funds"] == 1

    def test_instructions_present(self):
        fp = _make_fact_pack()
        assert fp.instructions["no_new_numbers"] is True
        assert fp.instructions["all_claims_require_evidence"] is True


class TestMemoPrompt:
    def test_prompt_contains_data(self):
        fp = _make_fact_pack()
        prompt = build_memo_prompt(fp)
        assert "Atlas L/S Equity" in prompt
        assert "annualized_return" in prompt
        assert "SPY" in prompt

    def test_prompt_contains_instructions(self):
        fp = _make_fact_pack()
        prompt = build_memo_prompt(fp)
        assert "Do NOT invent any numbers" in prompt
        assert "valid JSON" in prompt

    def test_prompt_contains_score_breakdown(self):
        fp = _make_fact_pack()
        prompt = build_memo_prompt(fp)
        assert "score_breakdown" in prompt
        assert "contribution" in prompt


class TestMemoGeneration:
    def test_valid_json_response(self):
        """Mock Anthropic response with valid JSON, verify parsing."""
        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps(
            {
                "memo_text": "# IC Memo\n\nAtlas L/S Equity shows strong returns.",
                "claims": [
                    {
                        "claim_id": "claim_1",
                        "claim_text": "Atlas L/S Equity achieved 8.00% annualized return.",
                        "referenced_metric_ids": ["annualized_return"],
                        "referenced_fund_names": ["Atlas L/S Equity"],
                    }
                ],
            }
        )

        fp = _make_fact_pack()
        memo = generate_memo(mock_client, fp)
        assert isinstance(memo, MemoOutput)
        assert len(memo.claims) == 1
        assert "Atlas" in memo.memo_text

    def test_invalid_json_raises(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = "This is not JSON"

        with pytest.raises(MemoGenerationError, match="invalid JSON"):
            generate_memo(mock_client, _make_fact_pack())

    def test_code_fence_stripped(self):
        """LLM sometimes wraps JSON in code fences."""
        mock_client = MagicMock()
        mock_client.generate.return_value = (
            '```json\n{"memo_text": "Test memo", "claims": []}\n```'
        )

        memo = generate_memo(mock_client, _make_fact_pack())
        assert memo.memo_text == "Test memo"


class TestClaimValidation:
    def test_valid_claims(self):
        memo = MemoOutput(
            memo_text="Test",
            claims=[
                Claim(
                    claim_id="c1",
                    claim_text="Atlas has strong returns",
                    referenced_metric_ids=[MetricId.ANNUALIZED_RETURN],
                    referenced_fund_names=["Atlas L/S Equity"],
                )
            ],
        )
        errors = validate_claims(memo, _make_fact_pack())
        assert len(errors) == 0

    def test_unknown_fund(self):
        memo = MemoOutput(
            memo_text="Test",
            claims=[
                Claim(
                    claim_id="c1",
                    claim_text="Unknown fund has returns",
                    referenced_metric_ids=[MetricId.ANNUALIZED_RETURN],
                    referenced_fund_names=["Nonexistent Fund"],
                )
            ],
        )
        errors = validate_claims(memo, _make_fact_pack())
        assert len(errors) == 1
        assert "Nonexistent Fund" in errors[0]


class TestShortlistTopK:
    def test_default_top_k_is_three(self):
        mandate = MandateConfig()
        assert mandate.shortlist_top_k == 3

    def test_top_k_set(self):
        mandate = MandateConfig(shortlist_top_k=2)
        assert mandate.shortlist_top_k == 2

    def test_top_k_slicing_in_fact_pack(self):
        """When top_k is applied, only sliced shortlist should appear in fact pack."""
        shortlist = _make_shortlist()
        # Add a second fund
        second = ScoredFund(
            fund_name="Birch Global Macro",
            metric_values={
                MetricId.ANNUALIZED_RETURN: 0.06,
                MetricId.ANNUALIZED_VOLATILITY: 0.10,
                MetricId.SHARPE_RATIO: 0.60,
                MetricId.MAX_DRAWDOWN: -0.08,
            },
            score_breakdown=[],
            composite_score=0.65,
            rank=2,
            constraint_results=[],
            all_constraints_passed=True,
        )
        full_shortlist = shortlist + [second]

        # Build fact pack with top_k=1 (slice before building)
        effective = full_shortlist[:1]
        fp = build_fact_pack("run-1", effective, _make_universe(), MandateConfig(), "SPY")
        assert len(fp.shortlist) == 1
        assert fp.shortlist[0].fund_name == "Atlas L/S Equity"


class TestAnalystNotesInPrompt:
    def test_no_notes_no_section(self):
        fp = _make_fact_pack()
        prompt = build_memo_prompt(fp)
        assert "Analyst Data Quality Notes" not in prompt

    def test_notes_appear_in_prompt(self):
        notes = [
            WarningResolution(
                category="duplicate",
                fund_name="Atlas L/S Equity",
                original_message="2 duplicate rows found",
                action="ignored",
                analyst_note="Keeping first occurrence",
            ),
            WarningResolution(
                category="outlier",
                fund_name="Atlas L/S Equity",
                original_message="Extreme return 45.0% in 2022-07",
                action="acknowledged",
                analyst_note="Confirmed with manager",
            ),
        ]
        fp = build_fact_pack(
            "run-1", _make_shortlist(), _make_universe(),
            MandateConfig(), "SPY", analyst_notes=notes,
        )
        prompt = build_memo_prompt(fp)
        assert "Analyst Data Quality Notes" in prompt
        assert "duplicate" in prompt
        assert "Keeping first occurrence" in prompt
        assert "Confirmed with manager" in prompt

    def test_fact_pack_analyst_notes_default_empty(self):
        fp = _make_fact_pack()
        assert fp.analyst_notes == []

    def test_fact_pack_analyst_notes_stored(self):
        notes = [
            WarningResolution(
                category="missing_month",
                fund_name="Cedar Credit",
                original_message="Missing 2022-06",
                action="ignored",
                analyst_note="",
            )
        ]
        fp = build_fact_pack(
            "run-1", _make_shortlist(), _make_universe(),
            MandateConfig(), "SPY", analyst_notes=notes,
        )
        assert len(fp.analyst_notes) == 1
        assert fp.analyst_notes[0].category == "missing_month"


class TestPromptFundCount:
    def test_prompt_shows_fund_count(self):
        fp = _make_fact_pack()
        prompt = build_memo_prompt(fp)
        assert "1 fund(s)" in prompt
        assert "ALL 1 fund(s)" in prompt
