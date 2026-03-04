"""Request/response models for the API layer.

Wraps core domain models from app.core.schemas for HTTP transport.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.schemas import (
    BenchmarkSeries,
    FundEligibility,
    FundMetrics,
    GroupRun,
    LLMIngestionResult,
    MandateConfig,
    NormalizedUniverse,
    RawFileContext,
    ScoredFund,
    WarningResolution,
)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response from POST /api/upload."""

    raw_context: RawFileContext
    llm_result: LLMIngestionResult
    llm_validation_errors: list[str]
    universe: NormalizedUniverse
    fund_metrics: list[FundMetrics]
    eligibility: list[FundEligibility]


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


class BenchmarkRequest(BaseModel):
    """Request body for POST /api/benchmark."""

    symbol: str
    universe: NormalizedUniverse


class BenchmarkResponse(BaseModel):
    """Response from POST /api/benchmark."""

    benchmark: BenchmarkSeries
    benchmark_metrics: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rank
# ---------------------------------------------------------------------------


class RankRequest(BaseModel):
    """Request body for POST /api/rank."""

    universe: NormalizedUniverse
    mandate: MandateConfig
    benchmark: BenchmarkSeries | None = None
    eligibility: list[FundEligibility] = Field(default_factory=list)


class RankResponse(BaseModel):
    """Response from POST /api/rank."""

    group_run: GroupRun


# ---------------------------------------------------------------------------
# Memo Stream
# ---------------------------------------------------------------------------


class MemoStreamRequest(BaseModel):
    """Request body for POST /api/memo/stream."""

    group_run: GroupRun
    universe: NormalizedUniverse
    mandate: MandateConfig
    warning_resolutions: list[WarningResolution] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportPdfRequest(BaseModel):
    """Request body for POST /api/export/pdf."""

    markdown: str
