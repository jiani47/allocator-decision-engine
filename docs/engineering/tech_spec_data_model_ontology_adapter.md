
# Tech Spec – Data Model + Ontology + Adapter
## Allocator Decision Engine (MVP)

---

# 1. Design Goals

This document defines the formal data model, ontology, and adapter boundary for the Allocator Decision Engine (MVP).

Design principles:

- Strict separation between domain ontology (Alternative Investments) and decision engine primitives.
- Deterministic core; generative layer at the edge.
- Immutable DecisionRun objects.
- Minimal but enforceable data lineage.
- SQLite + SQLAlchemy compatible.
- Monthly-return-only support in V1.

---

# 2. Conceptual Separation

## 2.1 Domain Ontology (Alt Investment)

Objects reflecting allocator reality:

- Fund
- Strategy (string label in V1)
- FundMonthlyReturn
- Mandate
- Benchmark

---

## 2.2 Decision Engine Primitives

Cross-domain abstractions:

- Candidate
- CandidateTimeSeries
- Attribute (key/value metadata)
- DecisionRun
- MetricResult
- ConstraintResult
- ScoreResult
- Claim
- EvidenceRef

---

## 2.3 Adapter Pattern

`AltInvestAdapter` bridges:

Domain ↔ Kernel

It maps:

- Fund → Candidate
- FundMonthlyReturn → CandidateTimeSeries
- Strategy/liquidity/fees → Candidate attributes

The kernel never imports domain models directly.

---

# 3. Database Schema (MVP)

## 3.1 Ingestion & Normalization Layer

### source_file

- id (PK)
- filename
- content_hash (sha256)
- uploaded_at
- raw_bytes_path
- notes (optional)

---

### ingestion_mapping

- id (PK)
- source_file_id (FK)
- mapping_json
- return_format (DECIMAL / PERCENT_STRING / AUTO)
- date_format_hint (optional)
- fund_name_normalization (json)
- created_at

Example mapping_json:

{
  "fund_name": "Fund",
  "date": "Month",
  "monthly_return": "Net Return"
}

---

### raw_row

- id (PK)
- source_file_id (FK)
- row_index
- raw_json

---

### normalized_universe

- id (PK)
- source_file_id (FK)
- ingestion_mapping_id (FK)
- universe_hash
- status (VALID / WARN / ERROR)
- warnings_json
- created_at

---

### normalized_fund

- id (PK)
- normalized_universe_id (FK)
- fund_key
- display_name
- strategy (nullable)
- liquidity_days (nullable)
- management_fee (nullable)
- performance_fee (nullable)

---

### normalized_return

- id (PK)
- normalized_fund_id (FK)
- period (YYYY-MM first-of-month)
- monthly_return (float decimal)
- raw_row_id (FK)

Unique constraint:
(normalized_fund_id, period)

---

## 3.2 Evaluation Layer

### mandate

- id (PK)
- name
- liquidity_max_days
- max_drawdown
- target_volatility
- strategy_includes_json
- strategy_excludes_json
- weights_json
- created_at

---

### benchmark_series

- id (PK)
- symbol
- source (YAHOO / FRED / OFFLINE)
- start_period
- end_period
- series_hash
- created_at

---

### benchmark_return

- id (PK)
- benchmark_series_id (FK)
- period
- monthly_return
- raw_json (optional)

Unique:
(benchmark_series_id, period)

---

### decision_run

- id (PK)
- normalized_universe_id (FK)
- mandate_id (FK)
- benchmark_series_id (FK)
- run_hash
- metric_version
- status (SUCCESS / FAILED)
- created_at

---

### run_candidate

- id (PK)
- decision_run_id (FK)
- normalized_fund_id (FK)
- included (bool)
- exclusion_reason (nullable)

---

## 3.3 Results & Audit Layer

### metric_result

- id (PK)
- decision_run_id (FK)
- normalized_fund_id (FK)
- metric_key
- value
- period_start
- period_end
- formula_text
- dependencies_json
- created_at

---

### constraint_result

- id (PK)
- decision_run_id (FK)
- normalized_fund_id (FK)
- constraint_key
- passed (bool)
- details_json

---

### score_result

- id (PK)
- decision_run_id (FK)
- normalized_fund_id (FK)
- score
- rank
- score_breakdown_json

---

### llm_artifact

- id (PK)
- decision_run_id (FK)
- provider
- model
- prompt_version
- prompt_text
- response_text
- created_at

---

### memo

- id (PK)
- decision_run_id (FK)
- memo_text
- created_at

---

### claim

- id (PK)
- memo_id (FK)
- claim_text
- normalized_fund_id (nullable)
- evidence_refs_json

EvidenceRef types:

Metric reference:

{
  "type": "metric",
  "metric_key": "SHARPE",
  "fund_id": 12
}

Raw row reference:

{
  "type": "raw_row",
  "raw_row_id": 332
}

Benchmark reference:

{
  "type": "benchmark",
  "symbol": "SPY",
  "period_start": "2022-01",
  "period_end": "2023-12"
}

---

# 4. Ontology Contracts (Pydantic Models)

Define strict Pydantic contracts:

- NormalizedUniverse
- NormalizedFund
- MonthlyReturnPoint
- MandateConfig
- DecisionRunSummary
- ClaimEvidenceRef

---

# 5. MVP Guardrails

- Monthly-only frequency enforced.
- Single benchmark per run.
- Single mandate per run.
- Deterministic metric_version required.
- Claim must include at least one EvidenceRef.
- raw_row preserved for lineage.

---

# 6. Non-Goals

- Graph lineage engine.
- Real-time ingestion.
- Multi-tenant RBAC.
- Portfolio optimization solver.
- Multi-benchmark comparison.
- Factor model decomposition.

---

# 7. Architectural Integrity Rule

Domain layer cannot import decision engine layer.
Decision engine cannot import UI layer.
LLM layer cannot compute metrics.
Audit layer cannot mutate DecisionRun.

Separation of concerns is mandatory.
