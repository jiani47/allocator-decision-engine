# Engineering Standards

## 1. Stack & Library Choices

### Backend
| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| API | FastAPI |
| Schemas | Pydantic v2 + pydantic-settings |
| Computation | Pandas + NumPy |
| LLM | Anthropic SDK (Claude), tenacity for retries |
| Package manager | uv |
| Formatter | black |
| Linter | ruff |
| Testing | pytest, pytest-asyncio, httpx |

### Frontend
| Layer | Choice |
|-------|--------|
| Framework | React 19 + TypeScript |
| Build | Vite 7 |
| Components | shadcn/ui (Radix primitives) |
| Styling | Tailwind CSS 4 |
| Icons | lucide-react |
| Markdown | react-markdown + remark-gfm |
| Excel export | xlsx |
| API types | openapi-typescript codegen |

### Deployment
| Layer | Choice |
|-------|--------|
| Container | Docker multi-stage (node:22-slim → python:3.12-slim) |
| Server | uvicorn |
| Static serving | FastAPI StaticFiles mount |

## 2. Type Safety

### Python
- Type hints on all public functions
- Pydantic v2 `BaseModel` for all data structures
- `BaseSettings` for configuration (with `EQUI_` prefix)
- Strict Pydantic schemas for all LLM outputs — fail closed on invalid JSON

### TypeScript
- Strict mode enabled
- Types mirror Python Pydantic models (snake_case preserved in JSON)
- API request/response types generated via `openapi-typescript` (`npm run codegen`)
- No `any` types — use proper union types for metric IDs, enums, etc.

## 3. Dependency Direction

```
API layer (router, schemas, streaming)
    ↓
services.py (orchestration)
    ↓
┌─────────────┬──────────────────┬─────────────────┐
│ core/       │ domains/         │ llm/            │
│ (schemas,   │ (alt_invest/)    │ (anthropic,     │
│  metrics,   │                  │  ingestion,     │
│  scoring,   │                  │  memo, rerank)  │
│  evidence)  │                  │                 │
└─────────────┴──────────────────┴─────────────────┘
```

Rules:
- **core/** never imports UI, API, domains, or LLM
- **domains/** never imports API or LLM
- **llm/** never computes metrics — receives precomputed data
- **services.py** wires layers together but adds no business logic
- **Frontend hooks** own API interaction; components are pure render

## 4. Error Handling

Domain-specific exceptions live in `app/core/exceptions.py`. Translate to HTTP only at the API boundary:

```python
# In core/
class ReRankError(Exception): ...

# In router.py
try:
    result = step_rerank(...)
except ReRankError as e:
    raise HTTPException(status_code=502, detail=str(e)) from e
```

Global exception handler in `app/api/app.py` catches unhandled errors, logs them, and returns 500.

## 5. Configuration

All settings via `pydantic-settings` with `EQUI_` prefix:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="EQUI_",
        extra="ignore",
    )
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_temperature: float = 0.2
    # ...
```

The `ANTHROPIC_API_KEY` fallback (without prefix) is supported for convenience.

## 6. Deterministic Core

### Immutable DecisionRun
Every evaluation produces an immutable `DecisionRun` record containing all inputs, computed metrics, scores, and outputs. The `input_hash` field enables reproducibility checks.

### Versioned Metrics
`METRIC_VERSION` in `app/core/schemas.py` tracks formula versions. Stored in every `DecisionRun` so results can be attributed to specific formula implementations.

### Evidence Graph
- `MetricResult` stores `formula_text` and `dependencies`
- `Claim` stores `source_text` and `referenced_metric_ids`
- `build_claim_evidence()` traces claims through metric results to source data

## 7. LLM Interaction Patterns

### AnthropicClient (`app/llm/anthropic_client.py`)
Thin wrapper with two methods:

```python
class AnthropicClient:
    def generate(self, prompt: str, system_prompt: str) -> str: ...
    def generate_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]: ...
```

- Retries: 3 attempts with exponential backoff (tenacity)
- Temperature: 0.2 (configured via settings)
- Structured logging of model calls and response sizes

### Fact Pack Pattern
The LLM never sees raw data for memo generation. A `FactPack` is assembled from precomputed, validated metrics:

```python
fact_pack = build_fact_pack(
    run_id, effective_shortlist, universe, mandate,
    benchmark_symbol, analyst_notes=warning_resolutions,
    group_name=..., group_rationale=..., ai_rationales=...,
)
client = AnthropicClient(settings)
memo = generate_memo(client, fact_pack)
```

### Two-Phase Memo
1. **Stream text** — `generate_memo_streaming()` yields `(event_type, payload)` tuples
2. **Extract claims** — After text is complete, parse structured `Claim` objects with `source_text` for citation matching

### Re-ranking Schema Validation
LLM re-ranking output is validated against `LLMReRankResult` Pydantic schema. Invalid JSON triggers `ReRankError`, surfaced as HTTP 502.

## 8. Citation Traceability

End-to-end audit chain:

```
Raw data → NormalizedFund → FundMetrics (with MetricResult lineage)
    → ScoredFund → FactPack → MemoOutput
    → Claim (source_text + referenced_metric_ids)
    → CitationBadge (frontend) → Evidence popover
```

Every claim references specific metric IDs and fund names, enabling the frontend to render inline citation badges that link back to the underlying data.

## 9. Frontend Standards

### Component Architecture
- **Wizard steps** (`steps/`) — One component per step, receives state from `WizardContext`
- **Hooks** (`hooks/`) — One hook per API endpoint, owns fetch logic and loading/error state
- **Components** (`components/`) — Reusable UI primitives (CitationBadge, CalcSheet, ClaimsPanel, etc.)
- **Context** (`context/WizardContext.tsx`) — Central state management, all cross-step state

### Conventions
- Hooks own all API interaction logic — components never call fetch directly
- shadcn/ui primitives for all UI elements (Button, Dialog, Popover, etc.)
- Tailwind CSS for styling — no CSS modules or styled-components
- `WizardContext` provides 25+ setter/action functions for state mutations
- Step navigation uses `highestStepReached` to allow backward navigation without data loss

### SSE Streaming
Memo streaming uses native `EventSource`-compatible fetch with manual SSE parsing in `useMemoStream`. Events: `progress`, `text_delta`, `complete`, `error`.

## 10. Testing

### Strategy
- Prefer integration tests over unit tests
- Never mock metric calculations — test with real Pandas/NumPy
- Mock only external API calls (Anthropic SDK, yfinance)
- Every metric must have a corresponding test
- Use httpx `AsyncClient` for API endpoint tests

### Running Tests
```bash
uv run pytest                    # all tests
uv run pytest tests/ -x         # stop on first failure
uv run pytest -k "test_sharpe"  # specific test
```

## 11. Logging

Structured logging via Python `logging` module:

```python
logger = logging.getLogger("equi.services")
logger.info("Calling Anthropic model=%s", self._model)
```

- Logger names follow module hierarchy: `equi.api`, `equi.services`, `equi.llm`, etc.
- No print statements
- No secrets or PII in log messages
- Log level configurable via `EQUI_LOG_LEVEL`

## 12. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `DecisionRun`, `ScoredFund` |
| Functions/variables | snake_case | `compute_all_metrics`, `fund_name` |
| Constants | UPPER_SNAKE_CASE | `METRIC_VERSION` |
| Files | snake_case.py | `memo_service.py` |
| Env vars | EQUI_ prefix + UPPER_SNAKE | `EQUI_ANTHROPIC_API_KEY` |
| React components | PascalCase | `CitationBadge`, `RankingView` |
| React hooks | camelCase with use prefix | `useMemoStream`, `useRank` |
| CSS classes | Tailwind utility classes | `className="flex gap-2"` |
