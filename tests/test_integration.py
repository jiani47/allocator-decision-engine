"""Full pipeline integration test."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from app.core.schemas import MandateConfig, MetricId
from app.services import (
    step_compute_metrics,
    step_create_run,
    step_export_json,
    step_export_markdown,
    step_normalize,
    step_rank,
    step_upload,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestFullPipelineClean:
    """End-to-end pipeline with clean CSV (no LLM)."""

    def test_upload_to_export(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()

        # Step 1: Upload
        df, mapping, fhash = step_upload(content, "01_clean_universe.csv")
        assert len(df) == 72  # 3 funds * 24 months

        # Step 2: Normalize
        universe = step_normalize(df, mapping, fhash)
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


class TestFullPipelineMessy:
    """End-to-end with messy CSV."""

    def test_messy_csv_normalizes(self):
        content = (FIXTURES / "02_messy_universe.csv").read_bytes()

        df, mapping, fhash = step_upload(content, "02_messy_universe.csv")
        universe = step_normalize(df, mapping, fhash)

        assert len(universe.funds) == 3
        assert len(universe.warnings) > 0

        fund_metrics = step_compute_metrics(universe)
        mandate = MandateConfig()
        ranked, run_candidates = step_rank(universe, fund_metrics, mandate)

        # All funds should be ranked despite messiness
        assert len(ranked) > 0

    def test_constraint_filtering(self):
        content = (FIXTURES / "01_clean_universe.csv").read_bytes()
        df, mapping, fhash = step_upload(content, "01_clean_universe.csv")
        universe = step_normalize(df, mapping, fhash)
        fund_metrics = step_compute_metrics(universe)

        # Exclude Global Macro
        mandate = MandateConfig(strategy_exclude=["Global Macro"])
        ranked, _ = step_rank(universe, fund_metrics, mandate)

        birch = next(sf for sf in ranked if sf.fund_name == "Birch Global Macro")
        assert not birch.all_constraints_passed
        # Birch should be ranked last
        assert birch.rank == len(ranked)
