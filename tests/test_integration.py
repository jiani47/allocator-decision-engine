"""Full pipeline integration test."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from app.core.schemas import (
    LLMExtractedFund,
    LLMIngestionResult,
    MandateConfig,
    MetricId,
    WarningResolution,
)
from app.core.hashing import file_hash
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    infer_column_mapping,
    read_csv,
)
from app.services import (
    step_compute_metrics,
    step_create_run,
    step_export_json,
    step_export_markdown,
    step_normalize_from_llm,
    step_parse_raw,
    step_rank,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestFullPipelineClean:
    """End-to-end pipeline with clean CSV (no LLM)."""

    def test_upload_to_export(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()

        # Step 1: Upload
        df = read_csv(content, "01_clean_universe.csv")
        assert len(df) == 72  # 3 funds * 24 months

        # Step 2: Normalize
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))
        assert len(universe.funds) == 3

        # Step 3: Metrics (no benchmark)
        fund_metrics = step_compute_metrics(universe)
        assert len(fund_metrics) == 3
        for fm in fund_metrics:
            assert not fm.insufficient_history

        # Step 4: Rank with default mandate
        mandate = MandateConfig()
        ranked, run_candidates = step_rank(universe, fund_metrics, mandate)
        assert len(ranked) == 3
        assert ranked[0].rank == 1
        assert len(run_candidates) == 3

        # Step 5: Create run (no memo)
        run = step_create_run(
            universe=universe,
            benchmark=None,
            mandate=mandate,
            all_fund_metrics=fund_metrics,
            run_candidates=run_candidates,
            ranked_shortlist=ranked,
        )
        assert run.run_id is not None
        assert run.metric_version is not None
        assert len(run.ranked_shortlist) == 3
        assert len(run.run_candidates) == 3

        # Step 6: Export
        md = step_export_markdown(run)
        assert "Ranked Shortlist" in md

        json_str = step_export_json(run)
        data = json.loads(json_str)
        assert data["run_id"] == run.run_id


    def test_source_row_indices_present(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        for fund in universe.funds:
            assert len(fund.source_row_indices) == fund.month_count
            assert all(isinstance(i, int) for i in fund.source_row_indices)

    def test_source_row_indices_with_raw_context(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        raw_context = step_parse_raw(content, "01_clean_universe.csv")
        universe = build_normalized_universe(df, mapping, file_hash(content), raw_context=raw_context)

        assert universe.raw_context is not None
        for fund in universe.funds:
            assert len(fund.source_row_indices) == fund.month_count


class TestFullPipelineMessy:
    """End-to-end with messy CSV."""

    def test_messy_csv_normalizes(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()

        df = read_csv(content, "02_messy_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        assert len(universe.funds) == 3
        assert len(universe.warnings) > 0

        fund_metrics = step_compute_metrics(universe)
        mandate = MandateConfig()
        ranked, run_candidates = step_rank(universe, fund_metrics, mandate)

        # All funds should be ranked despite messiness
        assert len(ranked) > 0

    def test_constraint_filtering(self):
        """Test that drawdown constraint pushes failing funds to the bottom."""
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))
        fund_metrics = step_compute_metrics(universe)

        # Use a very tight drawdown tolerance so at least one fund fails
        mandate = MandateConfig(max_drawdown_tolerance=-0.001)
        ranked, _ = step_rank(universe, fund_metrics, mandate)

        # At least one fund should fail the constraint
        failing = [sf for sf in ranked if not sf.all_constraints_passed]
        assert len(failing) > 0
        # Failing funds should be ranked after passing funds
        passing = [sf for sf in ranked if sf.all_constraints_passed]
        if passing and failing:
            assert max(sf.rank for sf in passing) < min(sf.rank for sf in failing)


class TestLLMPathIntegration:
    """Integration test using LLM extraction path (mocked LLM, real everything else)."""

    def test_llm_path_upload_to_export(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()

        # Step 0: Parse raw file
        raw_context = step_parse_raw(content, "01_clean_universe.csv")
        assert len(raw_context.data_rows) == 72
        assert len(raw_context.headers) == 5

        # Step 1: Simulate LLM extraction (mock the LLM call, use real data)
        llm_result = LLMIngestionResult(
            funds=[
                LLMExtractedFund(
                    fund_name="Atlas L/S Equity",
                    strategy="Long/Short Equity",
                    liquidity_days=45,
                    monthly_returns={
                        f"2022-{m:02d}": 0.01 * (m % 5 - 2)
                        for m in range(1, 13)
                    } | {
                        f"2023-{m:02d}": 0.01 * (m % 5 - 2)
                        for m in range(1, 13)
                    },
                    source_row_indices=list(range(1, 25)),
                ),
                LLMExtractedFund(
                    fund_name="Birch Global Macro",
                    strategy="Global Macro",
                    liquidity_days=90,
                    monthly_returns={
                        f"2022-{m:02d}": 0.008 * (m % 4 - 1)
                        for m in range(1, 13)
                    } | {
                        f"2023-{m:02d}": 0.008 * (m % 4 - 1)
                        for m in range(1, 13)
                    },
                    source_row_indices=list(range(25, 49)),
                ),
                LLMExtractedFund(
                    fund_name="Cedar Credit",
                    strategy="Credit",
                    liquidity_days=30,
                    monthly_returns={
                        f"2022-{m:02d}": 0.005 * (m % 3 - 1)
                        for m in range(1, 13)
                    } | {
                        f"2023-{m:02d}": 0.005 * (m % 3 - 1)
                        for m in range(1, 13)
                    },
                    source_row_indices=list(range(49, 73)),
                ),
            ],
            interpretation_notes="Extracted 3 funds from clean CSV",
            ambiguities=[],
        )

        # Step 2: Normalize from LLM result
        universe = step_normalize_from_llm(llm_result, raw_context)
        assert len(universe.funds) == 3
        assert universe.ingestion_method == "llm"
        assert universe.column_mapping is None

        # Step 3: Compute metrics (no benchmark)
        fund_metrics = step_compute_metrics(universe)
        assert len(fund_metrics) == 3
        for fm in fund_metrics:
            assert not fm.insufficient_history

        # Step 4: Rank
        mandate = MandateConfig()
        ranked, run_candidates = step_rank(universe, fund_metrics, mandate)
        assert len(ranked) == 3
        assert ranked[0].rank == 1

        # Step 5: Create run (no memo)
        run = step_create_run(
            universe=universe,
            benchmark=None,
            mandate=mandate,
            all_fund_metrics=fund_metrics,
            run_candidates=run_candidates,
            ranked_shortlist=ranked,
        )
        assert run.run_id is not None

        # Step 6: Export
        md = step_export_markdown(run)
        assert "Ranked Shortlist" in md

        json_str = step_export_json(run)
        data = json.loads(json_str)
        assert data["run_id"] == run.run_id


class TestTopKIntegration:
    """Test top-K shortlist slicing through the pipeline."""

    def test_top_k_limits_shortlist(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df = read_csv(content, "01_clean_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))
        fund_metrics = step_compute_metrics(universe)

        # Rank all 3 funds
        mandate = MandateConfig(shortlist_top_k=1)
        ranked, run_candidates = step_rank(universe, fund_metrics, mandate)
        assert len(ranked) == 3  # All 3 are still ranked

        # But when building fact pack for memo, only top 1 should be included
        from app.core.evidence.fact_pack import build_fact_pack

        effective = ranked[: mandate.shortlist_top_k]
        fp = build_fact_pack("test", effective, universe, mandate, "SPY")
        assert len(fp.shortlist) == 1
        assert fp.shortlist[0].rank == 1

    def test_warning_resolutions_flow_to_fact_pack(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()
        df = read_csv(content, "02_messy_universe.csv")
        mapping = infer_column_mapping(df)
        universe = build_normalized_universe(df, mapping, file_hash(content))

        assert len(universe.warnings) > 0

        # Simulate analyst resolutions
        resolutions = [
            WarningResolution(
                category=universe.warnings[0].category,
                fund_name=universe.warnings[0].fund_name,
                original_message=universe.warnings[0].message,
                action="ignored",
                analyst_note="Data verified with manager",
            )
        ]

        fund_metrics = step_compute_metrics(universe)
        mandate = MandateConfig()
        ranked, _ = step_rank(universe, fund_metrics, mandate)

        from app.core.evidence.fact_pack import build_fact_pack, build_memo_prompt

        fp = build_fact_pack("test", ranked, universe, mandate, "SPY", analyst_notes=resolutions)
        assert len(fp.analyst_notes) == 1
        assert fp.analyst_notes[0].analyst_note == "Data verified with manager"

        prompt = build_memo_prompt(fp)
        assert "Data verified with manager" in prompt
        assert "Analyst Data Quality Notes" in prompt
