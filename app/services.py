"""Thin orchestration layer between UI and core logic.

Keeps business logic out of Streamlit. Each function corresponds to a
pipeline step and returns typed results.
"""

from __future__ import annotations

import logging

import pandas as pd

from app.config import Settings
from app.core.decision_run import create_decision_run
from app.core.evidence.audit import build_claim_evidence, MetricEvidence
from app.core.evidence.fact_pack import build_fact_pack
from app.core.export import export_decision_run_json, export_memo_markdown
from app.core.hashing import file_hash
from app.core.metrics.compute import compute_all_metrics
from app.core.schemas import (
    BenchmarkSeries,
    Claim,
    ColumnMapping,
    DecisionRun,
    FactPack,
    FundMetrics,
    LLMIngestionResult,
    MandateConfig,
    MemoOutput,
    NormalizedUniverse,
    RawFileContext,
    RunCandidate,
    ScoredFund,
)
from app.core.scoring.ranking import rank_universe
from app.domains.alt_invest.benchmark import (
    align_benchmark_to_universe,
    fetch_benchmark_yfinance,
)
from app.domains.alt_invest.ingest import (
    build_normalized_universe,
    build_normalized_universe_from_llm,
    infer_column_mapping,
    read_csv,
)
from app.domains.alt_invest.raw_parser import parse_raw_file
from app.llm.anthropic_client import AnthropicClient
from app.llm.memo_service import generate_memo

logger = logging.getLogger("equi.services")


def step_upload(
    file_content: bytes, filename: str
) -> tuple[pd.DataFrame, ColumnMapping, str]:
    """Read CSV and infer column mapping. Returns (df, mapping, file_hash)."""
    df = read_csv(file_content, filename)
    mapping = infer_column_mapping(df)
    fhash = file_hash(file_content)
    return df, mapping, fhash


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
    api_key_override: str | None = None,
) -> tuple[LLMIngestionResult, list[str]]:
    """Extract fund data from raw context using LLM.

    Returns (LLMIngestionResult, validation_errors).
    """
    from app.llm.ingestion_service import extract_funds_via_llm, validate_llm_extraction

    client = AnthropicClient(settings, api_key_override=api_key_override)
    result = extract_funds_via_llm(client, raw_context)
    validation_errors = validate_llm_extraction(result)
    return result, validation_errors


def step_normalize_from_llm(
    llm_result: LLMIngestionResult,
    raw_context: RawFileContext,
) -> NormalizedUniverse:
    """Build normalized universe from LLM-extracted fund data."""
    return build_normalized_universe_from_llm(llm_result, raw_context)


def step_normalize(
    df: pd.DataFrame, mapping: ColumnMapping, fhash: str
) -> NormalizedUniverse:
    """Build normalized universe from DataFrame and confirmed mapping."""
    return build_normalized_universe(df, mapping, fhash)


def step_fetch_benchmark(
    symbol: str, universe: NormalizedUniverse
) -> BenchmarkSeries:
    """Fetch benchmark from yfinance and align to universe dates."""
    # Determine date range from universe
    all_starts = [f.date_range_start for f in universe.funds]
    all_ends = [f.date_range_end for f in universe.funds]
    start = min(all_starts)
    end = max(all_ends)

    benchmark = fetch_benchmark_yfinance(symbol, start, end)
    return align_benchmark_to_universe(benchmark, universe)


def step_compute_metrics(
    universe: NormalizedUniverse,
    benchmark: BenchmarkSeries | None = None,
    min_history_months: int = 12,
) -> list[FundMetrics]:
    """Compute all metrics for universe."""
    return compute_all_metrics(universe.funds, benchmark, min_history_months)


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
    api_key_override: str | None = None,
) -> tuple[MemoOutput, FactPack]:
    """Generate memo from LLM using fact pack."""
    import uuid

    run_id = str(uuid.uuid4())
    fact_pack = build_fact_pack(run_id, shortlist, universe, mandate, benchmark_symbol)
    client = AnthropicClient(settings, api_key_override=api_key_override)
    memo = generate_memo(client, fact_pack)
    return memo, fact_pack


def step_create_run(
    universe: NormalizedUniverse,
    benchmark: BenchmarkSeries | None,
    mandate: MandateConfig,
    all_fund_metrics: list[FundMetrics],
    run_candidates: list[RunCandidate],
    ranked_shortlist: list[ScoredFund],
    memo: MemoOutput | None = None,
    fact_pack: FactPack | None = None,
) -> DecisionRun:
    """Assemble DecisionRun record."""
    return create_decision_run(
        universe=universe,
        benchmark=benchmark,
        mandate=mandate,
        all_fund_metrics=all_fund_metrics,
        run_candidates=run_candidates,
        ranked_shortlist=ranked_shortlist,
        memo=memo,
        fact_pack=fact_pack,
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
