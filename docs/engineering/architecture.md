# Architecture

## System Overview

Equi is a three-layer pipeline that transforms raw fund performance data into ranked shortlists and auditable investment memos.

```
                    ┌──────────────────────────────────────────────┐
                    │              React Frontend                  │
                    │   (4-step wizard, SSE memo streaming)        │
                    └────────────────────┬─────────────────────────┘
                                         │ HTTP / SSE
                    ┌────────────────────▼─────────────────────────┐
                    │              FastAPI + Router                 │
                    │   /upload /benchmark /rank /rerank            │
                    │   /memo/stream /export/pdf /health            │
                    └────────────────────┬─────────────────────────┘
                                         │
          ┌──────────────────────────────▼──────────────────────────────┐
          │                     services.py                             │
          │   step_parse_raw → step_llm_extract → step_normalize       │
          │   step_fetch_benchmark → step_compute_metrics               │
          │   step_classify_eligibility → step_rank_group               │
          │   step_rerank → step_generate_memo (streaming)              │
          └────┬───────────────────┬────────────────────┬───────────────┘
               │                   │                    │
    ┌──────────▼──────┐  ┌────────▼────────┐  ┌───────▼────────┐
    │ Layer 1:        │  │ Layer 2:        │  │ Layer 3:       │
    │ Normalization   │  │ Decision Engine │  │ Memo & Audit   │
    │ (raw_parser,    │  │ (metrics,       │  │ (memo_service, │
    │  LLM ingestion, │  │  constraints,   │  │  claims,       │
    │  ingest)        │  │  scoring,       │  │  evidence,     │
    │                 │  │  grouping)      │  │  export)       │
    └─────────────────┘  └─────────────────┘  └────────────────┘
```

## Layer 1: Data Normalization

**Goal:** Transform arbitrary CSV/Excel files into a canonical `NormalizedUniverse`.

### Pipeline

1. **Raw parsing** (`raw_parser.py`) — Read file bytes, detect format, classify each row as `header`, `data`, `aggregated`, or `empty`. Output: `RawFileContext`.

2. **LLM extraction** (`llm/ingestion_service.py`) — Send `RawFileContext` (headers + data rows) to Claude. The LLM identifies fund names, date columns, return values, and optional metadata. Output: `LLMIngestionResult` with a list of `LLMExtractedFund`.

3. **Validation** — Check extraction for issues: missing returns, suspicious values, date gaps. Returns a list of validation error strings.

4. **Normalization** (`domains/alt_invest/ingest.py`) — Convert `LLMIngestionResult` into `NormalizedUniverse`: standardize date formats to `YYYY-MM`, convert returns to decimals, compute date ranges. Attach `ValidationWarning` list.

### Key Models

- `RawFileContext` — Headers, classified rows, file hash
- `LLMExtractedFund` — Fund name, monthly returns dict, optional metadata
- `NormalizedUniverse` — List of `NormalizedFund`, warnings, source hash, ingestion method

## Layer 2: Deterministic Decision Engine

**Goal:** Compute metrics, apply constraints, rank funds. All calculations are pure deterministic functions.

### Metrics (`core/metrics/`)

| Metric | Module | Formula |
|--------|--------|---------|
| Annualized Return | `returns.py` | `(prod(1 + ri))^(12/n) - 1` |
| Annualized Volatility | `returns.py` | `std(ri) * sqrt(12)` |
| Sharpe Ratio | `risk.py` | `ann_return / ann_vol` (rf=0) |
| Max Drawdown | `risk.py` | `min(cumulative_wealth / running_max - 1)` |
| Benchmark Correlation | `correlation.py` | `pearson_corr(fund_returns, benchmark_returns)` |

Metrics are computed via `compute_all_metrics()` which iterates all funds, producing a `FundMetrics` per fund with full `MetricResult` lineage (formula text, dependencies, period).

### Constraints (`core/constraints/`)

Independent pass/fail evaluators. Each constraint receives a fund and its metrics, returns a `ConstraintResult` with explanation. Configured via `MandateConfig`:
- Min liquidity days
- Max drawdown tolerance
- Target volatility
- Min annualized return
- Min Sharpe ratio
- Min history months
- Strategy include/exclude lists

### Scoring & Ranking (`core/scoring/`)

1. Normalize each metric to [0, 1] across the eligible universe (min-max)
2. Apply weights from `MandateConfig.weights`
3. Compute composite score = sum of weighted normalized values
4. Sort descending → assign ranks
5. Output: list of `ScoredFund` with full `ScoreComponent` breakdown

### Fund Grouping

Funds can be grouped (e.g., by strategy) for per-group ranking and benchmarking. Each group gets its own `GroupRun` containing metrics, ranking, and optionally its own memo.

- `GroupingCriteria` — User-specified criteria (standard criteria list, free text, max groups)
- `FundGroup` — Group name, member fund names, per-group benchmark
- `GroupRun` — Per-group metrics, ranked shortlist, run candidates, memo, fact pack

### Re-ranking (`llm/rerank_service.py`)

Optional LLM overlay on deterministic rankings. The LLM receives the shortlist with all metrics and qualitative context (warnings, fee data, strategy). Returns `LLMReRankResult` with per-fund `ReRankRationale` including:
- LLM rank vs. deterministic rank
- 2-4 sentence rationale
- Key factors and referenced metric IDs

Re-ranking is advisory — the analyst can adopt or ignore it.

## Layer 3: Memo & Audit

**Goal:** Generate a traceable investment memo from precomputed data.

### Two-Phase Memo Generation

**Phase 1 — Streaming text** (`llm/memo_service.py`):
- Build a `FactPack` from the shortlist, universe summary, mandate, and benchmark
- Stream memo text via Anthropic SDK's streaming API
- Frontend displays text as it arrives via SSE

**Phase 2 — Claims extraction**:
- After memo text is complete, extract structured `Claim` objects
- Each claim includes `source_text` (verbatim sentence from memo), referenced metric IDs, and fund names
- Claims enable inline citation badges in the frontend

### Citation Badges

The frontend post-processes memo markdown to find `source_text` matches and render inline `CitationBadge` components. Each badge opens an evidence popover linking the claim to the underlying metric values and fund data.

### Evidence Audit (`core/evidence/`)

- `fact_pack.py` — Assembles the `FactPack` (deterministic inputs to memo LLM)
- `audit.py` — `build_claim_evidence()` traces a `Claim` back through metric results to source data, producing `MetricEvidence` records

### Export (`core/export.py`)

- Markdown export of memo text
- PDF export via markdown-to-PDF rendering
- JSON export of full `DecisionRun`
- Excel export of ranked shortlist with metrics

## Service Orchestration

`app/services.py` contains thin `step_*` functions that wire layers together without adding business logic:

| Function | Layer | Purpose |
|----------|-------|---------|
| `step_parse_raw()` | L1 | Parse raw file → `RawFileContext` |
| `step_llm_extract()` | L1 | LLM fund extraction → `LLMIngestionResult` |
| `step_normalize_from_llm()` | L1 | Normalize → `NormalizedUniverse` |
| `step_fetch_benchmark()` | L2 | Fetch + align benchmark → `BenchmarkSeries` |
| `step_compute_metrics()` | L2 | Compute all fund metrics → `list[FundMetrics]` |
| `step_classify_eligibility()` | L2 | Mandate constraints → `list[FundEligibility]` |
| `step_rank()` | L2 | Rank universe → `(list[ScoredFund], list[RunCandidate])` |
| `step_rank_group()` | L2 | Per-group rank (fetch benchmark + metrics + rank) → `GroupRun` |
| `step_rerank()` | L2 | LLM re-ranking → `LLMReRankResult` |
| `step_generate_memo()` | L3 | Generate memo → `(MemoOutput, FactPack)` |
| `step_create_run()` | All | Assemble immutable `DecisionRun` |
| `step_build_evidence()` | L3 | Trace claim → evidence |
| `step_export_*()` | L3 | Export as Markdown/JSON/PDF |

## API Layer

FastAPI application (`app/api/app.py`) with:

- **CORS** configured for `localhost:5173` (Vite dev server)
- **Router** mounted at `/api` prefix
- **Static files** served from `static/` (frontend build output) when present
- **Global exception handler** logs and returns 500 for unhandled errors

### Endpoints (`app/api/router.py`)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/health` | — | `{"status": "ok"}` |
| POST | `/api/upload` | `file` (multipart) + `mandate` (JSON string) | `UploadResponse` |
| POST | `/api/benchmark` | `BenchmarkRequest` | `BenchmarkResponse` |
| POST | `/api/rank` | `RankRequest` | `RankResponse` |
| POST | `/api/rerank` | `ReRankRequest` | `ReRankResponse` |
| POST | `/api/memo/stream` | `MemoStreamRequest` | SSE stream |
| POST | `/api/export/pdf` | `ExportPdfRequest` | PDF bytes |

### SSE Streaming Protocol

The `/api/memo/stream` endpoint returns Server-Sent Events:

```
data: {"event": "progress", "message": "Building fact pack..."}
data: {"event": "progress", "message": "Generating memo..."}
data: {"event": "text_delta", "text": "..."}    # repeated
data: {"event": "progress", "message": "Extracting claims..."}
data: {"event": "complete", "group_run": {...}}
data: {"event": "error", "message": "..."}      # on failure
```

## Frontend Architecture

React 19 single-page app with a 4-step wizard:

### Steps

1. **MandateForm** — Configure constraints and weights upfront
2. **UploadReview** — Upload CSV, review LLM interpretation, resolve warnings
3. **RankingView** — Select benchmark, view per-group rankings, optional re-rank
4. **MemoExport** — Stream memo, view citation badges, export Excel/PDF

### State Management

`WizardContext.tsx` provides a React context with all cross-step state:
- Step navigation (with `highestStepReached` for back-navigation)
- Mandate configuration
- Upload results (raw context, LLM result, universe, metrics, eligibility)
- Benchmark selection and group runs
- Warning resolutions
- Memo streaming state

### Hooks

Each API endpoint has a corresponding custom hook:
- `useUpload` — File upload with multipart form
- `useBenchmark` — Benchmark fetch
- `useRank` — Fund ranking
- `useRerank` — LLM re-ranking
- `useMemoStream` — SSE streaming with text accumulation

### Type Mirroring

Frontend TypeScript types in `WizardContext.tsx` mirror Python Pydantic models from `app/core/schemas.py`. The `openapi-typescript` codegen (`npm run codegen`) generates types from the FastAPI OpenAPI spec for request/response schemas.

## Deployment

### Docker Multi-Stage Build

```dockerfile
# Stage 1: Build frontend (node:22-slim)
npm ci && npm run build → /build/dist

# Stage 2: Python runtime (python:3.12-slim)
pip install -r requirements.txt
Copy app/ + frontend dist → static/
uvicorn app.api.app:app --host 0.0.0.0 --port $PORT
```

The FastAPI app serves the frontend build as static files when `static/` exists, enabling single-container deployment.

### Configuration

All settings via environment variables with `EQUI_` prefix (see `app/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `EQUI_ANTHROPIC_API_KEY` | — | Anthropic API key (also accepts `ANTHROPIC_API_KEY`) |
| `EQUI_ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | LLM model |
| `EQUI_ANTHROPIC_MAX_TOKENS` | 4096 | Max output tokens |
| `EQUI_ANTHROPIC_TEMPERATURE` | 0.2 | LLM temperature |
| `EQUI_LOG_LEVEL` | INFO | Logging level |
| `EQUI_MIN_HISTORY_MONTHS` | 12 | Minimum fund history |
| `EQUI_OUTLIER_RETURN_THRESHOLD` | 0.25 | Outlier detection threshold |
| `EQUI_DEFAULT_BENCHMARK_SYMBOL` | SPY | Default benchmark ticker |
| `EQUI_INGESTION_MAX_ROWS` | 2000 | Max rows for raw parsing |
| `EQUI_MAX_FUND_GROUPS` | 5 | Max allowed fund groups |

## Design Decisions

1. **LLM-first ingestion** — CSV layouts vary wildly across managers. LLM extraction handles arbitrary formats without brittle column-mapping heuristics.

2. **Deterministic core, generative edge** — All financial math is pure Python (Pandas/NumPy). LLM is only used for text generation (memos) and qualitative tasks (ingestion, re-ranking). This ensures reproducibility and auditability.

3. **Fact pack pattern** — The LLM never sees raw data directly for memo generation. A structured `FactPack` is assembled from precomputed metrics, ensuring the memo can only reference verified numbers.

4. **Two-phase memo** — Streaming text first (for UX), then extracting structured claims. This avoids forcing the LLM to produce complex structured output in a single pass while streaming.

5. **Citation traceability via `source_text`** — Claims include the verbatim sentence from the memo, enabling the frontend to locate and annotate the exact text with citation badges.

6. **Per-group pipeline** — Fund grouping allows different benchmarks and independent rankings per strategy group, reflecting how analysts actually compare funds.

7. **Re-ranking as advisory overlay** — LLM re-ranking adds qualitative judgment but doesn't replace deterministic scores. The analyst explicitly opts in.

8. **Single-container deployment** — Docker multi-stage build produces one image serving both API and frontend, simplifying deployment.

9. **Frontend type mirroring** — TypeScript types mirror Python Pydantic schemas to catch API contract drift at compile time.

10. **Stateless API** — No database, no server-side sessions. All state lives in the frontend `WizardContext`. Each API call is self-contained with full inputs.
