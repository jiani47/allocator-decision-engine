# Equi — Allocator Decision Engine

## Product Context

Equi is a decision-structuring platform for fund-of-funds investment analysts. It converts messy manager performance data into normalized, validated, ranked, and traceable investment decisions.

**Primary user:** Investment analyst at a fund-of-funds or RIA — the person who owns data preprocessing, metric computation, and IC memo drafting.

**Core workflow (V1):**
Upload CSV → Confirm schema mapping → Review validation warnings → Normalize universe → Configure mandate constraints + weights → Run decision engine → Review ranked shortlist → Generate memo → Audit claims → Export + archive

**What this is NOT:** a robo-allocator, a dashboard, a DDQ tool, a portfolio management system, or a generic AI memo generator.

## Architecture

Three-layer architecture with strict boundaries:

1. **Data Normalization Layer** — Schema inference, column mapping, date/return normalization, missing data detection, anomaly detection, canonical `NormalizedUniverse` output
2. **Deterministic Decision Engine** — Metric computation, constraint evaluation, weighted ranking, `DecisionRun` creation
3. **Memo & Audit Layer** — LLM-drafted memo from precomputed fact pack, claim extraction, claim-to-evidence mapping

**Key invariant: Deterministic core, generative edge.** All financial calculations are deterministic pure functions. LLM only drafts narrative from structured JSON fact packs. Claims must reference metric IDs.

## Tech Stack

- **Language:** Python 3.12+
- **API:** FastAPI
- **UI:** Streamlit (internal micro-SaaS)
- **ORM:** SQLAlchemy 2.x (explicit session management)
- **DB:** SQLite (local prototype)
- **Schemas:** Pydantic v2
- **LLM:** Anthropic SDK (Claude)
- **Computation:** Pandas + NumPy
- **Package manager:** uv
- **Formatter:** black
- **Linter:** ruff
- **Testing:** pytest, pytest-asyncio, httpx

## Project Structure

```
app/
  api.py                    # FastAPI routes
  ui.py                     # Streamlit UI (thin, declarative)
  core/
    decision_run.py          # Immutable DecisionRun record
    metrics/                 # Pure deterministic metric functions
    constraints/             # Independent constraint classes (pass/fail + explanation)
    scoring/                 # Weighted ranking logic
    evidence/                # Claim-to-data traceability
  domains/
    alt_invest/
      models.py              # Domain models (Fund, ReturnSeries)
      adapter.py             # Maps domain models → engine primitives
      ingest.py              # CSV ingestion + normalization
  llm/
    anthropic_client.py      # Anthropic call wrapper with retries
    memo_service.py          # Fact pack → memo generation
  db/
    models.py                # SQLAlchemy ORM models
    session.py               # Session factory + dependency
tests/
```

## Engineering Principles

### Dependency Direction
- Core logic never imports UI or API
- Domain layer never imports API layer
- LLM layer never computes metrics
- DB models separate from Pydantic schemas
- Core decision engine must not import domain models (adapter pattern)

### Determinism
- All financial calculations must be deterministic pure functions
- LLM must never be source of truth for numeric outputs
- Memo generation uses a precomputed fact pack only
- Every evaluation produces an immutable `DecisionRun` record

### Code Quality
- Type hints on all public functions
- Pydantic v2 models for all request/response schemas
- Domain-specific exceptions in core; translate to HTTP only at API boundary
- Structured logging (no print statements)
- No business logic inside Streamlit files
- No financial math inside LLM prompts
- No ORM queries inside core logic functions

### Testing
- Prefer integration tests over unit tests
- Never mock metric calculations
- Mock only external API calls (LLM, benchmark API)
- Every metric must have a corresponding test

### LLM Interaction
- Strict Pydantic schema for LLM output
- Temperature <= 0.3
- Fail closed on invalid JSON
- Store prompt + response for traceability

### Naming
- Classes: `PascalCase` (e.g., `DecisionRun`, `MaxDrawdownConstraint`)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`, one primary concept per file

## MVP Scope

**V1 metrics:** Annualized return, annualized volatility, Sharpe ratio (rf=0), max drawdown, benchmark correlation

**V1 input:** Single CSV, monthly return time series per fund. Required columns after mapping: `fund_name`, `date`, `monthly_return`. Optional: `strategy`, `liquidity_days`, `management_fee`, `performance_fee`.

**V1 mandate:** Single mandate per run with min liquidity, max drawdown tolerance, target volatility, strategy include/exclude lists, weight sliders (return, Sharpe, drawdown penalty).

**V1 benchmark:** Single benchmark per run fetched from public API (Yahoo Finance / FRED), monthly adjusted close converted to returns.

**Explicit non-goals for V1:** multi-user collaboration, enterprise auth, automated vendor ingestion, real-time tracking, capital allocation execution, advanced ML, rolling metrics, factor models, VaR/CVaR, regime detection.
