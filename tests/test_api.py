"""Tests for the FastAPI REST API."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import app
from app.core.schemas import (
    BenchmarkSeries,
    ConstraintResult,
    FundEligibility,
    FundMetrics,
    GroupRun,
    FundGroup,
    LLMExtractedFund,
    LLMIngestionResult,
    MandateConfig,
    MetricId,
    MetricResult,
    NormalizedFund,
    NormalizedUniverse,
    RawFileContext,
    RawRow,
    RowClassification,
    ScoredFund,
    ScoreComponent,
    RunCandidate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_raw_context() -> RawFileContext:
    return RawFileContext(
        filename="test.csv",
        file_hash="abc123",
        headers=["Fund", "Date", "Return"],
        header_row_index=0,
        data_rows=[
            RawRow(row_index=1, cells=["FundA", "2023-01", "0.01"], classification=RowClassification.DATA),
        ],
        total_rows=2,
    )


def _make_fund(name: str = "FundA") -> NormalizedFund:
    returns = {f"2023-{m:02d}": 0.01 for m in range(1, 13)}
    return NormalizedFund(
        fund_name=name,
        monthly_returns=returns,
        date_range_start="2023-01",
        date_range_end="2023-12",
        month_count=12,
    )


def _make_universe() -> NormalizedUniverse:
    return NormalizedUniverse(
        funds=[_make_fund("FundA"), _make_fund("FundB")],
        source_file_hash="abc123",
        normalization_timestamp="2024-01-01T00:00:00Z",
        ingestion_method="llm",
        raw_context=_make_raw_context(),
    )


def _make_fund_metrics(name: str = "FundA") -> FundMetrics:
    return FundMetrics(
        fund_name=name,
        metric_results=[
            MetricResult(metric_id=MetricId.ANNUALIZED_RETURN, value=0.12, period_start="2023-01", period_end="2023-12", formula_text="geometric mean"),
            MetricResult(metric_id=MetricId.ANNUALIZED_VOLATILITY, value=0.15, period_start="2023-01", period_end="2023-12", formula_text="std * sqrt(12)"),
            MetricResult(metric_id=MetricId.SHARPE_RATIO, value=0.80, period_start="2023-01", period_end="2023-12", formula_text="ret / vol"),
            MetricResult(metric_id=MetricId.MAX_DRAWDOWN, value=-0.10, period_start="2023-01", period_end="2023-12", formula_text="min dd"),
        ],
        date_range_start="2023-01",
        date_range_end="2023-12",
        month_count=12,
    )


def _make_llm_result() -> LLMIngestionResult:
    return LLMIngestionResult(
        funds=[
            LLMExtractedFund(
                fund_name="FundA",
                monthly_returns={f"2023-{m:02d}": 0.01 for m in range(1, 13)},
            ),
            LLMExtractedFund(
                fund_name="FundB",
                monthly_returns={f"2023-{m:02d}": 0.02 for m in range(1, 13)},
            ),
        ],
        interpretation_notes="Test",
    )


def _make_mandate() -> MandateConfig:
    return MandateConfig(min_history_months=12)


def _make_benchmark() -> BenchmarkSeries:
    return BenchmarkSeries(
        symbol="SPY",
        monthly_returns={f"2023-{m:02d}": 0.01 for m in range(1, 13)},
        source="yfinance",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
@patch("app.api.router.step_classify_eligibility")
@patch("app.api.router.step_compute_metrics")
@patch("app.api.router.step_normalize_from_llm")
@patch("app.api.router.step_llm_extract")
@patch("app.api.router.step_parse_raw")
async def test_upload(mock_parse, mock_llm, mock_norm, mock_metrics, mock_elig):
    mock_parse.return_value = _make_raw_context()
    mock_llm.return_value = (_make_llm_result(), [])
    mock_norm.return_value = _make_universe()
    mock_metrics.return_value = [_make_fund_metrics("FundA"), _make_fund_metrics("FundB")]
    mock_elig.return_value = [
        FundEligibility(fund_name="FundA", eligible=True),
        FundEligibility(fund_name="FundB", eligible=True),
    ]

    mandate = _make_mandate()
    csv_content = b"Fund,Date,Return\nFundA,2023-01,0.01"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            data={"mandate": mandate.model_dump_json()},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "universe" in data
    assert "fund_metrics" in data
    assert "eligibility" in data
    assert len(data["eligibility"]) == 2


@pytest.mark.asyncio
@patch("app.api.router.step_fetch_benchmark")
async def test_benchmark(mock_fetch):
    bm = _make_benchmark()
    mock_fetch.return_value = bm

    universe = _make_universe()
    body = {"symbol": "SPY", "universe": universe.model_dump(mode="json")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/benchmark", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["benchmark"]["symbol"] == "SPY"
    assert "benchmark_metrics" in data
    assert "annualized_return" in data["benchmark_metrics"]


@pytest.mark.asyncio
@patch("app.api.router.step_rank_group")
async def test_rank(mock_rank):
    group_run = GroupRun(
        group=FundGroup(group_name="All", group_id="default", fund_names=["FundA"]),
        fund_metrics=[_make_fund_metrics("FundA")],
        ranked_shortlist=[
            ScoredFund(
                fund_name="FundA",
                metric_values={MetricId.ANNUALIZED_RETURN: 0.12},
                score_breakdown=[],
                composite_score=0.85,
                rank=1,
                constraint_results=[],
                all_constraints_passed=True,
            )
        ],
        run_candidates=[RunCandidate(fund_name="FundA", included=True)],
    )
    mock_rank.return_value = group_run

    universe = _make_universe()
    mandate = _make_mandate()
    body = {
        "universe": universe.model_dump(mode="json"),
        "mandate": mandate.model_dump(mode="json"),
        "eligibility": [
            {"fund_name": "FundA", "eligible": True, "failing_constraints": []},
            {"fund_name": "FundB", "eligible": True, "failing_constraints": []},
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/rank", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "group_run" in data
    assert data["group_run"]["ranked_shortlist"][0]["fund_name"] == "FundA"


@pytest.mark.asyncio
@patch("app.api.router.step_export_pdf")
@patch("app.api.router.step_create_run")
async def test_export_pdf(mock_create, mock_export):
    from app.core.schemas import DecisionRun

    mock_create.return_value = DecisionRun(
        run_id="test-run-id",
        input_hash="hash",
        timestamp="2024-01-01T00:00:00Z",
        metric_version="1.0.0",
        universe=_make_universe(),
        mandate=_make_mandate(),
        all_fund_metrics=[],
        run_candidates=[],
        ranked_shortlist=[],
    )
    mock_export.return_value = b"%PDF-1.4 fake pdf content"

    universe = _make_universe()
    mandate = _make_mandate()
    body = {
        "universe": universe.model_dump(mode="json"),
        "mandate": mandate.model_dump(mode="json"),
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/export/pdf", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert b"PDF" in resp.content
