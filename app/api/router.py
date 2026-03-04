"""API routes for the Equi decision engine."""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.api.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    ExportPdfRequest,
    MemoStreamRequest,
    RankRequest,
    RankResponse,
    UploadResponse,
)
from app.api.streaming import memo_stream_sse
from app.config import Settings
from app.core.metrics.returns import annualized_return, annualized_volatility
from app.core.metrics.risk import max_drawdown, sharpe_ratio
from app.core.schemas import FundGroup, MandateConfig
from app.services import (
    step_classify_eligibility,
    step_compute_metrics,
    step_fetch_benchmark,
    step_llm_extract,
    step_normalize_from_llm,
    step_parse_raw,
    step_rank_group,
)

logger = logging.getLogger("equi.api")

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok", "version": "1.0.0"}


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    mandate: str = Form(...),
) -> UploadResponse:
    """Upload a fund data file and run the full ingestion pipeline.

    The mandate parameter is a JSON string of MandateConfig.
    """
    settings = Settings()
    mandate_config = MandateConfig.model_validate_json(mandate)

    content = await file.read()
    filename = file.filename or "upload.csv"

    raw_context = step_parse_raw(content, filename, max_rows=settings.ingestion_max_rows)
    llm_result, validation_errors = step_llm_extract(raw_context, settings)
    universe = step_normalize_from_llm(llm_result, raw_context)
    fund_metrics = step_compute_metrics(
        universe, None, mandate_config.min_history_months
    )
    eligibility = step_classify_eligibility(universe, fund_metrics, mandate_config)

    return UploadResponse(
        raw_context=raw_context,
        llm_result=llm_result,
        llm_validation_errors=validation_errors,
        universe=universe,
        fund_metrics=fund_metrics,
        eligibility=eligibility,
    )


@router.post("/benchmark", response_model=BenchmarkResponse)
def benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    """Fetch benchmark data and compute benchmark metrics."""
    bm = step_fetch_benchmark(request.symbol, request.universe)

    # Compute benchmark metrics for display
    bm_periods = sorted(bm.monthly_returns.keys())
    bm_returns = pd.Series([bm.monthly_returns[p] for p in bm_periods])
    bm_metrics = {
        "annualized_return": float(annualized_return(bm_returns)),
        "annualized_volatility": float(annualized_volatility(bm_returns)),
        "sharpe_ratio": float(sharpe_ratio(bm_returns)),
        "max_drawdown": float(max_drawdown(bm_returns)),
    }

    return BenchmarkResponse(benchmark=bm, benchmark_metrics=bm_metrics)


@router.post("/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    """Rank funds within a group based on mandate constraints and weights."""
    eligible_names = [e.fund_name for e in request.eligibility if e.eligible]
    if not eligible_names:
        eligible_names = [f.fund_name for f in request.universe.funds]

    default_group = FundGroup(
        group_name="All Funds",
        group_id="default",
        fund_names=eligible_names,
        benchmark_symbol=request.benchmark.symbol if request.benchmark else None,
        benchmark=request.benchmark,
        grouping_rationale="",
    )

    group_run = step_rank_group(
        request.universe,
        default_group,
        request.mandate,
        min_history_months=request.mandate.min_history_months,
    )

    return RankResponse(group_run=group_run)


@router.post("/memo/stream")
def memo_stream(request: MemoStreamRequest) -> StreamingResponse:
    """Stream memo generation via SSE."""
    settings = Settings()
    return StreamingResponse(
        memo_stream_sse(request, settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/export/pdf")
def export_pdf(request: ExportPdfRequest) -> Response:
    """Export memo markdown as PDF."""
    from app.core.export import render_markdown_to_pdf

    pdf_bytes = render_markdown_to_pdf(request.markdown)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=equi_memo.pdf"
        },
    )
