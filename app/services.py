"""Thin orchestration layer between UI and core logic.

Keeps business logic out of Streamlit. Each function corresponds to a
pipeline step and returns typed results.
"""

from __future__ import annotations

import logging

from app.config import Settings
from app.core.decision_run import create_decision_run
from app.core.evidence.audit import build_claim_evidence, MetricEvidence
from app.core.evidence.fact_pack import build_fact_pack
from app.core.export import export_decision_run_json, export_memo_markdown, export_memo_pdf
from app.core.metrics.compute import compute_all_metrics
from app.core.schemas import (
    BenchmarkSeries,
    Claim,
    ConstraintResult,
    DecisionRun,
    FactPack,
    FundEligibility,
    FundGroup,
    FundMetrics,
    GroupRun,
    LLMIngestionResult,
    LLMReRankResult,
    MandateConfig,
    MemoOutput,
    NormalizedUniverse,
    RawFileContext,
    RunCandidate,
    ScoredFund,
    WarningResolution,
)
from app.core.scoring.ranking import rank_universe
from app.domains.alt_invest.benchmark import (
    align_benchmark_to_universe,
    fetch_benchmark_yfinance,
)
from app.domains.alt_invest.ingest import (
    build_normalized_universe_from_llm,
)
from app.domains.alt_invest.raw_parser import parse_raw_file
from app.llm.anthropic_client import AnthropicClient
from app.llm.memo_service import generate_memo
from app.llm.rerank_service import rerank_funds

logger = logging.getLogger("equi.services")


def step_parse_raw(
    file_content: bytes,
    filename: str,
    max_rows: int = 2000,
) -> RawFileContext:
    """Parse raw file into classified rows for LLM extraction."""
    return parse_raw_file(file_content, filename, max_rows=max_rows)


def step_llm_extract(
    raw_context: RawFileContext,
    settings: Settings,
) -> tuple[LLMIngestionResult, list[str]]:
    """Extract fund data from raw context using LLM.

    Returns (LLMIngestionResult, validation_errors).
    """
    from app.llm.ingestion_service import extract_funds_via_llm, validate_llm_extraction

    client = AnthropicClient(settings)
    result = extract_funds_via_llm(client, raw_context)
    validation_errors = validate_llm_extraction(result)
    return result, validation_errors


def step_normalize_from_llm(
    llm_result: LLMIngestionResult,
    raw_context: RawFileContext,
) -> NormalizedUniverse:
    """Build normalized universe from LLM-extracted fund data."""
    return build_normalized_universe_from_llm(llm_result, raw_context)


def step_fetch_benchmark(
    symbol: str, universe: NormalizedUniverse
) -> BenchmarkSeries:
    """Fetch benchmark from yfinance and align to universe dates."""
    # Determine date range from universe
    all_starts = [f.date_range_start for f in universe.funds]
    all_ends = [f.date_range_end for f in universe.funds]
    start = min(all_starts)
    end = max(all_ends)

    # yfinance expects YYYY-MM-DD; fund dates may be YYYY-MM
    if len(start) == 7:
        start = f"{start}-01"
    if len(end) == 7:
        end = f"{end}-28"

    benchmark = fetch_benchmark_yfinance(symbol, start, end)
    return align_benchmark_to_universe(benchmark, universe)


def step_compute_metrics(
    universe: NormalizedUniverse,
    benchmark: BenchmarkSeries | None = None,
    min_history_months: int = 12,
) -> list[FundMetrics]:
    """Compute all metrics for universe."""
    return compute_all_metrics(universe.funds, benchmark, min_history_months)


def step_classify_eligibility(
    universe: NormalizedUniverse,
    all_metrics: list[FundMetrics],
    mandate: MandateConfig,
) -> list[FundEligibility]:
    """Apply mandate constraints to classify funds as eligible/ineligible.

    Does NOT filter — all funds remain in the universe. Returns eligibility
    status for each fund, including which constraints failed.
    """
    from app.core.scoring.ranking import build_constraints, evaluate_constraints

    constraints = build_constraints(mandate)
    metrics_by_name = {m.fund_name: m for m in all_metrics}

    eligibility: list[FundEligibility] = []
    for fund in universe.funds:
        fm = metrics_by_name.get(fund.fund_name)
        if fm is None or fm.insufficient_history:
            eligibility.append(
                FundEligibility(
                    fund_name=fund.fund_name,
                    eligible=False,
                    failing_constraints=[
                        ConstraintResult(
                            constraint_name="history",
                            passed=False,
                            explanation=f"Insufficient history ({fm.month_count if fm else 0} months)",
                        )
                    ],
                )
            )
            continue

        results = evaluate_constraints(fund, fm, constraints)
        failing = [r for r in results if not r.passed]
        eligibility.append(
            FundEligibility(
                fund_name=fund.fund_name,
                eligible=len(failing) == 0,
                failing_constraints=failing,
            )
        )

    return eligibility



def step_rank(
    universe: NormalizedUniverse,
    all_metrics: list[FundMetrics],
    mandate: MandateConfig,
) -> tuple[list[ScoredFund], list[RunCandidate]]:
    """Rank universe with constraints and weights."""
    return rank_universe(universe, all_metrics, mandate)


def step_generate_memo(
    shortlist: list[ScoredFund],
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark_symbol: str,
    settings: Settings,
    warning_resolutions: list[WarningResolution] | None = None,
) -> tuple[MemoOutput, FactPack]:
    """Generate memo from LLM using fact pack."""
    import uuid

    # Apply top-K filter
    effective_shortlist = shortlist[: mandate.shortlist_top_k]

    run_id = str(uuid.uuid4())
    fact_pack = build_fact_pack(
        run_id,
        effective_shortlist,
        universe,
        mandate,
        benchmark_symbol,
        analyst_notes=warning_resolutions,
    )
    client = AnthropicClient(settings)
    memo = generate_memo(client, fact_pack)
    return memo, fact_pack


def step_rerank(
    group_run: GroupRun,
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    settings: Settings,
    warning_resolutions: list[WarningResolution] | None = None,
) -> LLMReRankResult:
    """Re-rank funds using LLM qualitative judgment."""
    client = AnthropicClient(settings)
    benchmark_symbol = group_run.group.benchmark_symbol
    return rerank_funds(
        client,
        group_run.ranked_shortlist,
        universe,
        mandate,
        benchmark_symbol=benchmark_symbol,
        warning_resolutions=warning_resolutions,
    )


def step_create_run(
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark: BenchmarkSeries | None = None,
    all_fund_metrics: list[FundMetrics] | None = None,
    run_candidates: list[RunCandidate] | None = None,
    ranked_shortlist: list[ScoredFund] | None = None,
    memo: MemoOutput | None = None,
    fact_pack: FactPack | None = None,
    fund_eligibility: list[FundEligibility] | None = None,
    group_runs: list[GroupRun] | None = None,
) -> DecisionRun:
    """Assemble DecisionRun record."""
    return create_decision_run(
        universe=universe,
        benchmark=benchmark,
        mandate=mandate,
        all_fund_metrics=all_fund_metrics or [],
        run_candidates=run_candidates or [],
        ranked_shortlist=ranked_shortlist or [],
        memo=memo,
        fact_pack=fact_pack,
        fund_eligibility=fund_eligibility,
        group_runs=group_runs,
    )


def step_build_evidence(
    claim: Claim, decision_run: DecisionRun
) -> list[MetricEvidence]:
    """Build evidence chain for a claim."""
    return build_claim_evidence(claim, decision_run)


def step_export_markdown(decision_run: DecisionRun) -> str:
    """Export as Markdown."""
    return export_memo_markdown(decision_run)


def step_export_json(decision_run: DecisionRun) -> str:
    """Export as JSON."""
    return export_decision_run_json(decision_run)


def step_export_pdf(decision_run: DecisionRun) -> bytes:
    """Export as PDF."""
    return export_memo_pdf(decision_run)


# ---------------------------------------------------------------------------
# Per-group pipeline helpers
# ---------------------------------------------------------------------------


def build_group_universe(
    universe: NormalizedUniverse, group: FundGroup
) -> NormalizedUniverse:
    """Construct a sub-universe containing only the group's funds."""
    group_set = set(group.fund_names)
    return NormalizedUniverse(
        funds=[f for f in universe.funds if f.fund_name in group_set],
        warnings=[
            w
            for w in universe.warnings
            if w.fund_name in group_set or w.fund_name is None
        ],
        source_file_hash=universe.source_file_hash,
        normalization_timestamp=universe.normalization_timestamp,
        ingestion_method=universe.ingestion_method,
        raw_context=universe.raw_context,
        llm_interpretation_notes=universe.llm_interpretation_notes,
    )


def step_rank_group(
    universe: NormalizedUniverse,
    group: FundGroup,
    mandate: MandateConfig,
    min_history_months: int = 12,
) -> GroupRun:
    """Rank funds within a single group.

    Fetches group benchmark, computes metrics, ranks.
    Returns a GroupRun with populated metrics and ranking.
    """
    group_universe = build_group_universe(universe, group)

    # Use pre-fetched benchmark if available, otherwise fetch
    benchmark = group.benchmark
    if benchmark is None and group.benchmark_symbol:
        benchmark = step_fetch_benchmark(group.benchmark_symbol, group_universe)
        group.benchmark = benchmark

    # Compute metrics for group's funds
    fund_metrics = step_compute_metrics(
        group_universe, benchmark, min_history_months
    )

    # Rank within group
    ranked, run_candidates = step_rank(group_universe, fund_metrics, mandate)

    return GroupRun(
        group=group,
        fund_metrics=fund_metrics,
        ranked_shortlist=ranked,
        run_candidates=run_candidates,
    )


def step_generate_group_memo(
    group_run: GroupRun,
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    settings: Settings,
    warning_resolutions: list[WarningResolution] | None = None,
) -> GroupRun:
    """Generate memo for a single group. Returns updated GroupRun."""
    import uuid

    effective_shortlist = group_run.ranked_shortlist[: mandate.shortlist_top_k]

    group_universe = _build_group_universe(universe, group_run.group)

    run_id = str(uuid.uuid4())
    fact_pack = build_fact_pack(
        run_id,
        effective_shortlist,
        group_universe,
        mandate,
        group_run.group.benchmark_symbol or "None",
        analyst_notes=warning_resolutions,
        group_name=group_run.group.group_name,
        group_rationale=group_run.group.grouping_rationale,
    )

    client = AnthropicClient(settings)
    memo = generate_memo(client, fact_pack)

    group_run.memo = memo
    group_run.fact_pack = fact_pack
    return group_run
