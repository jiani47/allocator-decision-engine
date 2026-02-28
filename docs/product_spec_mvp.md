
# Document 2: Product Spec – MVP
## Allocator Decision Engine (Analyst Workflow)

---

## A) Product Goal, Success Metrics, and Scope

### Product Goal

Turn messy manager data into a normalized, validated, and defendable investment decision workflow.

The MVP focuses on:

- Efficiency in preprocessing
- Deterministic evaluation
- Claim-level traceability

---

### Success Metrics

MVP is successful when:

1. Analyst can upload a messy CSV and normalize it within 5 minutes.
2. No manual spreadsheet editing is required post-upload.
3. Deterministic metrics are generated consistently.
4. Memo claims can be traced to raw data rows.
5. Analyst voluntarily reuses tool for subsequent evaluation cycles.

---

### Scope (MVP)

Included:

- CSV ingestion
- Schema inference + mapping confirmation
- Data validation warnings
- Canonical normalization
- Deterministic metrics
- Constraint engine
- Ranking logic
- IC memo draft
- Claim-evidence audit view
- Exportable memo
- Immutable DecisionRun record

Out of Scope:

- Multi-user collaboration
- Enterprise auth / RBAC
- Automated vendor ingestion
- Real-time portfolio tracking
- Capital allocation execution
- Advanced ML scoring
- External CRM integration

---

## B) User Workflow & Integration Point

### Current Workflow

Manager CSV → Excel cleanup → Excel metrics → Word memo → IC review

---

### New Workflow (With Product)

1. Upload CSV
2. Confirm schema mapping
3. Review validation warnings
4. Normalize universe
5. Configure constraints + weights
6. Run decision engine
7. Review shortlist + metrics
8. Generate memo
9. Audit claims
10. Export memo + archive run

---

### Integration Point

The product integrates at:

- Data preprocessing
- Metric computation
- IC memo drafting layer

It does not replace:

- Portfolio accounting systems
- CRM systems
- Market data providers

---

## C) MVP Milestones

### Milestone 1 – Ingestion & Normalization

- CSV upload
- Column inference
- User confirmation of schema
- Date normalization
- Return format normalization
- Missing data detection
- Anomaly detection
- Canonical NormalizedUniverse object

Deliverable:
Validated structured universe ready for evaluation.

---

### Milestone 2 – Deterministic Metric Engine

- Annualized return
- Volatility
- Sharpe ratio
- Max drawdown
- Benchmark correlation

Deliverable:
Metrics table for each fund.

---

### Milestone 3 – Constraint & Ranking Layer

- Liquidity constraint
- Max drawdown threshold
- Strategy exclusion
- Weighted ranking system

Deliverable:
Ranked shortlist with pass/fail indicators.

---

### Milestone 4 – Memo + Claim Structuring

- Generate memo from deterministic fact pack
- Extract structured claims
- Enforce claim-to-metric linkage

Deliverable:
Structured memo draft with traceable claims.

---

### Milestone 5 – Audit View + Export

- Claim → metric → raw data mapping view
- DecisionRun storage
- Export memo to Markdown / PDF

Deliverable:
Defendable, archivable decision record.

---

## D) Product Architecture

### Layer 1 – Data Normalization

Responsibilities:

- Schema inference
- Mapping validation
- Data cleaning
- Missing value handling
- Anomaly detection
- Canonical universe generation

Output:
NormalizedUniverse

---

### Layer 2 – Deterministic Decision Engine

Responsibilities:

- Metric computation
- Constraint evaluation
- Weighted ranking
- DecisionRun creation

Output:
Structured fact pack

---

### Layer 3 – Memo & Audit Layer

Responsibilities:

- Memo drafting via LLM
- Claim extraction
- Claim-to-evidence mapping
- Audit visualization

Output:
Defendable IC memo + audit graph

---

### System Design Principles

- Deterministic core
- Generative edge
- Immutable decision runs
- Clear separation of normalization and evaluation layers
- Auditability by default

---
