"""DecisionRun assembly."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.hashing import stable_hash
from app.core.schemas import (
    BenchmarkSeries,
    DecisionRun,
    FactPack,
    FundEligibility,
    FundMetrics,
    GroupRun,
    METRIC_VERSION,
    MandateConfig,
    MemoOutput,
    NormalizedUniverse,
    RunCandidate,
    ScoredFund,
)


def create_decision_run(
    universe: NormalizedUniverse,
    benchmark: BenchmarkSeries | None,
    mandate: MandateConfig,
    all_fund_metrics: list[FundMetrics],
    run_candidates: list[RunCandidate],
    ranked_shortlist: list[ScoredFund],
    memo: MemoOutput | None = None,
    fact_pack: FactPack | None = None,
    fund_eligibility: list[FundEligibility] | None = None,
    group_runs: list[GroupRun] | None = None,
) -> DecisionRun:
    """Assemble immutable DecisionRun record."""
    input_data = {
        "source_file_hash": universe.source_file_hash,
        "mandate": mandate.model_dump(),
        "benchmark_symbol": benchmark.symbol if benchmark else None,
    }

    return DecisionRun(
        run_id=str(uuid.uuid4()),
        input_hash=stable_hash(input_data),
        timestamp=datetime.now(timezone.utc).isoformat(),
        metric_version=METRIC_VERSION,
        universe=universe,
        benchmark=benchmark,
        mandate=mandate,
        all_fund_metrics=all_fund_metrics,
        run_candidates=run_candidates,
        ranked_shortlist=ranked_shortlist,
        memo=memo,
        fact_pack=fact_pack,
        fund_eligibility=fund_eligibility or [],
        group_runs=group_runs or [],
    )
