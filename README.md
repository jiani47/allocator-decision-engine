# Equi — Allocator Decision Engine

A decision-structuring platform for fund-of-funds analysts. Upload messy manager performance data, and Equi normalizes it, computes deterministic metrics, ranks funds against mandate constraints, and generates traceable IC memos with inline citation badges.

## Quick Start

### Backend

```bash
uv sync
export EQUI_ANTHROPIC_API_KEY=sk-ant-...
uv run uvicorn app.api.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # starts Vite dev server on :5173, proxies API to :8000
```

### Docker

```bash
docker build -t equi .
docker run -p 8000:8000 -e EQUI_ANTHROPIC_API_KEY=sk-ant-... equi
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `EQUI_ANTHROPIC_API_KEY` | Yes | Anthropic API key (also accepts `ANTHROPIC_API_KEY`) |
| `EQUI_ANTHROPIC_MODEL` | No | LLM model (default: `claude-sonnet-4-20250514`) |
| `EQUI_DEFAULT_BENCHMARK_SYMBOL` | No | Default benchmark (default: `SPY`) |

See `app/config.py` for all settings.

## Tests

```bash
uv run pytest
```

## Documentation

- [Architecture](docs/engineering/architecture.md) — System design, data flow, deployment
- [Engineering Standards](docs/engineering/engineering_standards.md) — Code conventions, patterns
- [Data Model Reference](docs/engineering/tech_spec_data_model_ontology_adapter.md) — Pydantic schema reference
- [Product Spec](docs/product/product_spec.md) — Capabilities, workflow, metrics
- [Frontend](frontend/README.md) — Frontend dev setup and architecture
