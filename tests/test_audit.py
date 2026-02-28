"""Tests for audit evidence, decision run creation, and export."""

from pathlib import Path

from app.core.decision_run import create_decision_run
from app.core.evidence.audit import FORMULA_DESCRIPTIONS, build_claim_evidence
from app.core.export import export_decision_run_json, export_memo_markdown
from app.core.hashing import file_hash
from app.core.metrics.compute import compute_all_metrics
from app.core.schemas import (
    Claim,
    MandateConfig,
    MemoOutput,
    MetricId,
)
from app.core.scoring.ranking import rank_universe
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    infer_column_mapping,
    read_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _build_full_run():
    """Helper: run the full pipeline on clean CSV to produce a DecisionRun."""
    content = (FIXTURES / "01_clean_universe.csv").read_bytes()
    df = read_csv(content, "01_clean_universe.csv")
    mapping = infer_column_mapping(df)
    universe = build_normalized_universe(df, mapping, file_hash(content))
    all_metrics = compute_all_metrics(universe.funds)
    mandate = MandateConfig()
    ranked = rank_universe(universe, all_metrics, mandate)

    memo = MemoOutput(
        memo_text="# Test Memo\n\nAtlas shows strong returns.",
        claims=[
            Claim(
                claim_id="c1",
                claim_text="Atlas L/S Equity achieved strong annualized return",
                referenced_metric_ids=[MetricId.ANNUALIZED_RETURN],
                referenced_fund_names=["Atlas L/S Equity"],
            ),
            Claim(
                claim_id="c2",
                claim_text="Cedar Credit has lowest drawdown and volatility",
                referenced_metric_ids=[MetricId.MAX_DRAWDOWN, MetricId.ANNUALIZED_VOLATILITY],
                referenced_fund_names=["Cedar Credit"],
            ),
        ],
    )

    run = create_decision_run(
        universe=universe,
        benchmark=None,
        mandate=mandate,
        all_fund_metrics=all_metrics,
        ranked_shortlist=ranked,
        memo=memo,
    )
    return run


class TestDecisionRun:
    def test_creation(self):
        run = _build_full_run()
        assert run.run_id is not None
        assert run.input_hash is not None
        assert len(run.ranked_shortlist) == 3
        assert run.memo is not None

    def test_has_all_fields(self):
        run = _build_full_run()
        assert run.universe is not None
        assert run.mandate is not None
        assert len(run.all_fund_metrics) == 3


class TestClaimEvidence:
    def test_evidence_for_single_metric(self):
        run = _build_full_run()
        claim = run.memo.claims[0]  # Atlas annualized_return
        evidence = build_claim_evidence(claim, run)
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev.metric_id == MetricId.ANNUALIZED_RETURN
        assert ev.fund_name == "Atlas L/S Equity"
        assert ev.computed_value != 0
        assert ev.formula_description == FORMULA_DESCRIPTIONS[MetricId.ANNUALIZED_RETURN]
        assert len(ev.sample_raw_returns) > 0

    def test_evidence_for_multiple_metrics(self):
        run = _build_full_run()
        claim = run.memo.claims[1]  # Cedar: drawdown + vol
        evidence = build_claim_evidence(claim, run)
        assert len(evidence) == 2
        metric_ids = {ev.metric_id for ev in evidence}
        assert MetricId.MAX_DRAWDOWN in metric_ids
        assert MetricId.ANNUALIZED_VOLATILITY in metric_ids


class TestExport:
    def test_markdown_export(self):
        run = _build_full_run()
        md = export_memo_markdown(run)
        assert "# IC Memo" in md
        assert "Atlas L/S Equity" in md
        assert "Ranked Shortlist" in md
        assert "Mandate Configuration" in md
        assert run.run_id[:8] in md

    def test_json_export_roundtrip(self):
        run = _build_full_run()
        json_str = export_decision_run_json(run)
        # Should be valid JSON
        import json
        data = json.loads(json_str)
        assert data["run_id"] == run.run_id
        assert len(data["ranked_shortlist"]) == 3
