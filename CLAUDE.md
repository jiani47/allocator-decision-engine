# Equi — Allocator Decision Engine

## Product Context

Equi is a decision-structuring platform for fund-of-funds investment analysts. It converts messy manager performance data into normalized, validated, ranked, and traceable investment decisions.

**Primary user:** Investment analyst at a fund-of-funds or RIA.

**Core workflow:**
Upload CSV → LLM extraction → Review interpretation & warnings → Configure mandate → Select benchmark → Rank per group → Optional LLM re-rank → Stream memo → Audit via citation badges → Export (Excel/PDF)

**What this is NOT:** a robo-allocator, a dashboard, a DDQ tool, a portfolio management system, or a generic AI memo generator.

## Architecture

Three-layer architecture with strict boundaries:

1. **Data Normalization Layer** — Raw file parsing, LLM-based fund extraction, date/return normalization, validation warnings, canonical `NormalizedUniverse` output
2. **Deterministic Decision Engine** — Metric computation, constraint evaluation, weighted ranking, fund grouping, `DecisionRun` creation
3. **Memo & Audit Layer** — Two-phase LLM memo (streaming text + claims extraction), inline citation badges with evidence popovers, Excel/PDF export

**LLM touchpoints (3):** (1) CSV ingestion — extract fund data from arbitrary layouts, (2) Re-ranking — qualitative judgment overlay on deterministic scores, (3) Memo generation — narrative from precomputed fact pack + claims extraction.

**Key invariant: Deterministic core, generative edge.** All financial calculations are deterministic pure functions. LLM only drafts narrative from structured JSON fact packs. Claims must reference metric IDs and include `source_text` for citation matching.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, Pandas, NumPy
- **Frontend:** React 19, TypeScript, Vite, shadcn/ui (Radix), Tailwind CSS
- **LLM:** Anthropic SDK — model: `claude-sonnet-4-20250514`
- **Legacy UI:** Streamlit (still functional at `app/ui/`)
- **Deployment:** Docker multi-stage (Node build → Python runtime), uvicorn
- **Dev tools:** uv, black, ruff, pytest, pytest-asyncio, httpx
- **API types:** `openapi-typescript` codegen (`npm run codegen`)

## Project Structure

```
app/
  config.py                  # Settings (pydantic-settings, EQUI_ prefix)
  services.py                # Orchestration layer (step_* functions)
  api/
    app.py                   # FastAPI app + static file mount
    router.py                # API endpoints
    schemas.py               # Request/response models
    streaming.py             # SSE memo streaming
  core/
    schemas.py               # All Pydantic domain models (single source of truth)
    decision_run.py           # Immutable DecisionRun assembly
    exceptions.py             # Domain-specific exceptions
    export.py                # Markdown/PDF/JSON export
    hashing.py               # Stable input hashing
    metrics/                 # Pure metric functions (returns, risk, correlation)
    constraints/             # Constraint classes (liquidity)
    scoring/                 # Weighted ranking logic
    evidence/                # Fact pack builder + claim-to-evidence audit
  domains/
    alt_invest/
      adapter.py             # Domain → engine primitives
      benchmark.py           # yfinance fetch + alignment
      ingest.py              # Normalization from LLM extraction
      raw_parser.py          # CSV/Excel raw parsing + row classification
  llm/
    anthropic_client.py      # Anthropic wrapper (retries, structured output)
    ingestion_service.py     # LLM fund extraction from raw file context
    memo_service.py          # Fact pack → memo generation (streaming)
    rerank_service.py        # LLM re-ranking with rationales
  ui/                        # Legacy Streamlit UI
frontend/
  src/
    context/WizardContext.tsx # Central state (types mirror Python schemas)
    steps/                   # 4 wizard steps (MandateForm, UploadReview, RankingView, MemoExport)
    hooks/                   # API hooks (useUpload, useBenchmark, useRank, useRerank, useMemoStream)
    components/              # Shared components (CitationBadge, CalcSheet, ClaimsPanel, etc.)
tests/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/upload` | Upload CSV + LLM extraction + normalization + metrics |
| POST | `/benchmark` | Fetch benchmark data from yfinance |
| POST | `/rank` | Rank funds within a group by mandate |
| POST | `/rerank` | LLM re-ranking with qualitative rationales |
| POST | `/memo/stream` | Stream memo generation via SSE |
| POST | `/export/pdf` | Export memo markdown as PDF |

## Engineering Principles

### Dependency Direction
- Core logic never imports UI, API, or LLM
- Domain layer never imports API layer
- LLM layer never computes metrics — receives precomputed fact packs
- Core decision engine uses adapter pattern (no domain model imports)

### Determinism
- All financial calculations are deterministic pure functions
- LLM must never be source of truth for numeric outputs
- Memo generation uses a precomputed `FactPack` only
- Every evaluation produces an immutable `DecisionRun` record

### Code Quality
- Type hints on all public functions
- Pydantic v2 models for all request/response schemas
- Domain-specific exceptions in core; translate to HTTP only at API boundary
- Structured logging (no print statements)
- No financial math inside LLM prompts

### Frontend Conventions
- Hooks own all API interaction logic (one hook per endpoint)
- TypeScript types mirror Python Pydantic models (via `openapi-typescript` codegen)
- shadcn/ui primitives for all UI components
- `WizardContext` manages all cross-step state

### Citation Traceability
- Claims include `source_text` for verbatim sentence matching in memo
- Citation badges rendered inline via markdown post-processing
- Evidence popovers link claims → metrics → raw data

### Two-Phase Memo Generation
- Phase 1: Stream memo text via SSE for real-time display
- Phase 2: Extract structured claims with metric references from completed memo

### Testing
- Prefer integration tests over unit tests
- Never mock metric calculations
- Mock only external API calls (LLM, benchmark API)
- Every metric must have a corresponding test

### LLM Interaction
- Strict Pydantic schema for all LLM outputs
- Temperature: 0.2
- Fail closed on invalid JSON
- Store prompt + response for traceability

### Naming
- Classes: `PascalCase` (e.g., `DecisionRun`, `ScoredFund`)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`, one primary concept per file

## Key Models (`app/core/schemas.py`)

- **Ingestion:** `RowClassification`, `RawRow`, `RawFileContext`, `LLMExtractedFund`, `LLMIngestionResult`
- **Normalization:** `ColumnMapping`, `ValidationWarning`, `WarningResolution`, `NormalizedFund`, `NormalizedUniverse`
- **Metrics:** `MetricId` (5 metrics), `MetricResult`, `FundMetrics`, `BenchmarkSeries`
- **Constraints:** `ConstraintResult`, `FundEligibility`, `MandateConfig`, `RunCandidate`
- **Scoring:** `ScoreComponent`, `ScoredFund`
- **Grouping:** `GroupingCriteria`, `FundGroup`, `LLMGroupingResult`, `GroupRun`
- **Re-ranking:** `ReRankRationale`, `LLMReRankResult`
- **Memo:** `FactPack`, `MemoOutput`, `Claim` (with `source_text`)
- **Decision:** `DecisionRun` (immutable run record)

## Configuration

All settings via `EQUI_` prefixed env vars (see `app/config.py`):
- `EQUI_ANTHROPIC_API_KEY` (also accepts `ANTHROPIC_API_KEY`)
- `EQUI_ANTHROPIC_MODEL` (default: `claude-sonnet-4-20250514`)
- `EQUI_ANTHROPIC_TEMPERATURE` (default: 0.2)
- `EQUI_DEFAULT_BENCHMARK_SYMBOL` (default: SPY)
- `EQUI_INGESTION_MAX_ROWS` (default: 2000)

## Metrics (V1)

| Metric | Formula |
|--------|---------|
| Annualized Return | `(prod(1 + ri))^(12/n) - 1` |
| Annualized Volatility | `std(ri) * sqrt(12)` |
| Sharpe Ratio | `ann_return / ann_vol` (rf=0) |
| Max Drawdown | `min(cumulative_wealth / running_max - 1)` |
| Benchmark Correlation | `pearson_corr(fund, benchmark)` |
