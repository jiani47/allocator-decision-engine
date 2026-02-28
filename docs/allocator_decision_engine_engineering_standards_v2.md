# Engineering Standards -- Allocator Decision Engine (Option B)

## 1. Stack & Library Choices

### Core Stack

-   Python 3.12+
-   FastAPI (API layer)
-   Streamlit (internal micro-SaaS UI)
-   SQLAlchemy 2.x (ORM, explicit session management)
-   SQLite (local persistence for prototype)
-   Pydantic v2 (schemas & structured validation)
-   Anthropic SDK (LLM integration)
-   Pandas + NumPy (financial computation)

### Dev Tooling

-   Package Manager: **uv**
-   Formatter: **black**
-   Linter: **ruff**
-   Testing: **pytest**
-   Test utilities: **pytest-asyncio**, **httpx (test client)**

------------------------------------------------------------------------

## 2. Modern Python Practices (Generic)

### Typing & Validation

-   Use type hints everywhere (no untyped public functions).
-   Prefer `Annotated` + Pydantic models for request/response schemas.
-   Use `dataclass` only for lightweight immutable structures.
-   Avoid dynamic typing patterns unless explicitly justified.

### Dependency Injection

-   Use FastAPI dependency injection for DB sessions and config.
-   Avoid global mutable state.

### Error Handling

-   Never swallow exceptions silently.
-   Raise domain-specific exceptions from the core layer.
-   Translate exceptions to HTTP errors only in the API layer.

### Logging

-   Structured logging (no print statements).
-   Log decision runs, LLM calls, constraint failures.
-   Never log secrets or PII.

### Determinism First

-   All financial calculations must be deterministic.
-   LLM must never be source of truth for numeric outputs.
-   Memo generation uses a precomputed fact pack.

------------------------------------------------------------------------

## 3. FinTech-Specific Design Patterns

### 3.1 Deterministic Core, Generative Edge

-   Metrics, constraints, scoring must be pure deterministic functions.
-   LLM only drafts narrative based on structured JSON.
-   Claims must reference metric IDs or source record IDs.

### 3.2 Versioned Decision Runs

-   Every evaluation produces a `DecisionRun` record.
-   Runs are immutable.
-   Store:
    -   Input dataset hash
    -   Constraint configuration
    -   Scoring weights
    -   Derived metrics
    -   Memo + claims

### 3.3 Evidence Graph

-   Every derived metric stores:
    -   Formula description
    -   Input dependencies
-   Every memo claim stores:
    -   Linked metric IDs
    -   Linked raw source rows

### 3.4 Constraint Engine Pattern

-   Constraints are independent classes.
-   Each returns:
    -   pass/fail
    -   explanation
-   Constraints are composable.

### 3.5 Adapter Pattern (Domain Isolation)

-   Domain-specific models (Fund, ReturnSeries) live in
    `/domains/alt_invest`.
-   Adapter maps domain models to generic decision engine primitives.
-   Core decision engine must not import domain models.

------------------------------------------------------------------------

## 4. Project Structure Rules

    app/
      api.py
      ui.py
      core/
        decision_run.py
        metrics/
        constraints/
        scoring/
        evidence/
      domains/
        alt_invest/
          models.py
          adapter.py
          ingest.py
      llm/
        anthropic_client.py
        memo_service.py
      db/
        models.py
        session.py
    tests/

### Organizational Principles

-   Core logic never imports UI.
-   Domain layer never imports API layer.
-   LLM layer never computes metrics.
-   Database models separate from Pydantic schemas.

------------------------------------------------------------------------

## 5. Naming Conventions

### Classes

-   PascalCase
-   Example: `DecisionRun`, `MaxDrawdownConstraint`, `SharpeRatioMetric`

### Functions

-   snake_case
-   Pure functions preferred for metrics.

### Variables

-   snake_case
-   Avoid single-letter names except loop indices.

### Constants

-   UPPER_SNAKE_CASE

### Files

-   snake_case.py
-   One primary concept per file.

------------------------------------------------------------------------

## 6. Coding Examples (Best Practices)

> These examples are **style + pattern** references. They intentionally avoid prescribing the final domain schema/interfaces,
> which will live in a separate technical spec.

### 6.1 Configuration via `pydantic-settings`
**Goal:** one place for env vars + defaults, typed and testable.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    database_url: str = "sqlite:///./local.db"
    anthropic_api_key: str
    log_level: str = "INFO"
```

Usage:

```python
settings = Settings()  # loads from environment / .env
```

### 6.2 FastAPI dependency for DB session (no global session)
**Goal:** explicit lifecycle + easy integration tests.

```python
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 6.3 Layered error handling (domain exception → API translation)
**Goal:** keep domain logic pure; translate only at API boundary.

```python
class DecisionEngineError(Exception):
    """Base exception for core decision engine errors."""

class InvalidUniverseError(DecisionEngineError):
    pass
```

API layer:

```python
from fastapi import HTTPException

def to_http_error(err: Exception) -> HTTPException:
    if isinstance(err, InvalidUniverseError):
        return HTTPException(status_code=400, detail=str(err))
    return HTTPException(status_code=500, detail="Internal error")
```

### 6.4 Deterministic metric computation as pure functions
**Goal:** metrics are testable, reusable, and side-effect free.

```python
import numpy as np
import pandas as pd

def annualized_return(monthly_returns: pd.Series) -> float:
    r = monthly_returns.dropna().astype(float).to_numpy()
    if r.size == 0:
        raise ValueError("No returns provided")
    growth = np.prod(1.0 + r)
    years = r.size / 12.0
    return float(growth ** (1.0 / years) - 1.0)
```

### 6.5 “Fact pack” pattern (deterministic JSON for LLM input)
**Goal:** LLM sees **only** precomputed facts; never invents numbers.

```python
def build_fact_pack(*, run_id: str, shortlist_rows: list[dict], metrics_rows: list[dict]) -> dict:
    return {
        "run_id": run_id,
        "shortlist": shortlist_rows,
        "metrics": metrics_rows,
        "instructions": {
            "no_new_numbers": True,
            "all_claims_require_evidence": True,
        },
    }
```

### 6.6 Anthropic call wrapper with retries + strict parsing
**Goal:** fail-closed, loggable, testable.

```python
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

client = Anthropic(api_key=settings.anthropic_api_key)

class MemoOutput(BaseModel):
    memo_text: str
    claims: list[dict]  # schema details defined in separate tech spec

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def generate_memo(*, prompt: str) -> MemoOutput:
    msg = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1500,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text  # keep raw for audit logs
    try:
        data = json.loads(raw)
        return MemoOutput.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        # Fail closed so we never ship unstructured claims
        raise RuntimeError(f"Invalid LLM output: {e}") from e
```

### 6.7 Idempotent “DecisionRun” creation (hash inputs)
**Goal:** repeated runs with same inputs can be detected and compared.

```python
import hashlib
import json

def stable_hash(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

### 6.8 Streamlit: keep UI thin, call services
**Goal:** Streamlit file stays declarative; services hold logic.

```python
import streamlit as st
from app.services.runs import run_decision_engine

st.title("Allocator Memo Builder")

uploaded = st.file_uploader("Upload fund universe CSV", type=["csv"])
if uploaded:
    st.success("File uploaded")
    if st.button("Run analysis"):
        with st.spinner("Computing metrics and drafting memo..."):
            run_id = run_decision_engine(uploaded)
        st.toast(f"Run complete: {run_id}")
```

### 6.9 Testing seam: isolate external calls behind ports
**Goal:** integration tests can replace external APIs cleanly.

```python
from typing import Protocol

class BenchmarkProvider(Protocol):
    def get_series(self, symbol: str) -> "pd.Series": ...

class LlmProvider(Protocol):
    def generate(self, prompt: str) -> dict: ...
```

In tests, provide fakes; in production, provide real implementations.


## 7. Testing Strategy

### Philosophy

Prefer **integration tests over unit tests**.

Why: - Financial logic correctness matters in end-to-end flow. -
Decision engine must be validated holistically. - LLM output validation
requires structured pipeline testing.

### Required Test Types

#### 6.1 Metric Engine Integration Test

-   Load synthetic dataset.
-   Run full decision pipeline.
-   Assert computed metrics match expected values.

#### 6.2 Constraint Validation Test

-   Verify constraint failure produces correct explanation.

#### 6.3 Decision Run Snapshot Test

-   Run full pipeline.
-   Assert:
    -   Ranking order
    -   Metric outputs
    -   Stored DecisionRun structure

#### 6.4 Memo Grounding Test

-   Mock Anthropic response.
-   Validate claims reference valid metric IDs.
-   Reject claims with missing references.

### Mocking Rules

-   Never mock metric calculations.
-   Mock only external API calls (LLM, benchmark API).

------------------------------------------------------------------------

## 8. Code Quality Rules

-   No business logic inside Streamlit files.
-   No financial math inside LLM prompts.
-   No ORM queries inside core logic functions.
-   Every metric must have a corresponding test.

------------------------------------------------------------------------

## 9. Productionization Readiness Notes

Even though this is a prototype: - Design DB schema as multi-tenant
ready (org_id field). - DecisionRun immutable by default. - Configurable
constraint parameters stored per run. - LLM prompts versioned and
stored.

------------------------------------------------------------------------

## 10. LLM Interaction Rules

-   Use strict Pydantic schema for LLM output.
-   Temperature low (\<=0.3).
-   Fail closed on invalid JSON.
-   Store prompt + response in DB for traceability.

------------------------------------------------------------------------

## 11. Philosophy

This system is: - Deterministic at the core - Generative at the edge -
Auditable end-to-end - Extensible across domains - Designed for
compliance-grade trust

The goal is not a memo generator. The goal is a reusable decision
intelligence kernel.
