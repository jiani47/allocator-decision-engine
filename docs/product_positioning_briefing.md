
# Document 1: Product Positioning / Briefing
## Allocator Decision Engine (Analyst-First Strategy)

---

## A) Primary User Persona and Why

### Primary Persona: Investment Analyst (Allocator, Fund-of-Funds / RIA)

We deliberately choose the lower-ranking investment analyst — not the CIO or committee — as the primary user.

Why:

1. Analysts own the data processing and preparation workflow.
2. Analysts feel the operational pain most directly.
3. Analysts are the internal champions who influence tool adoption.
4. If analysts trust and reuse the system, committee buy-in follows naturally.
5. If analysts do not adopt it, committee-level positioning is irrelevant.

The product is designed as a force multiplier for analysts, not as an executive AI dashboard.

---

## B) Current Stack and Identified Pain Points

### Current Stack

Typical analyst workflow includes:

- CSV / Excel files from fund managers
- Excel for normalization and metric computation
- Word or Google Docs for IC memo drafting
- Email + shared drives for document exchange
- Possibly a performance analytics platform (metrics only)

### Pain Point 1: Data Normalization & Validation

The invariant:

Analysts receive messy, unnormalized data from managers.

This requires:

- Schema understanding
- Column mapping
- Date normalization
- Handling missing data
- Detecting anomalies
- Aligning time ranges
- Verifying completeness and freshness

This preprocessing step is:

- Manual
- Repetitive
- Error-prone
- Poorly documented
- Difficult to reproduce

Before any metric is computed, substantial manual effort is required.

---

### Pain Point 2: Lack of Traceability in Decision Outputs

After normalization:

- Metrics are computed in Excel
- Memo claims are written manually
- No structured link exists between:
  - Raw data
  - Metric calculations
  - Memo claims

This creates risk:

- Hard to defend numbers in committee
- No audit trail
- Difficult to reproduce past decisions
- Knowledge locked in spreadsheets

---

## C) Why Existing Tools Do Not Solve These Pain Points

### Excel

- Flexible but fragile
- No schema enforcement
- No repeatability
- No built-in audit graph
- Heavy manual effort

Excel solves computation flexibility, not process structure.

---

### Analytics Suites

- Compute metrics
- Provide dashboards
- Assume clean, structured data
- Do not solve messy ingestion
- Do not generate traceable IC memos

They solve analysis, not normalization + traceability.

---

### DDQ / Workflow Tools

- Focus on document management
- Questionnaire tracking
- Compliance workflows
- Not performance normalization or decision structuring

They do not address metric grounding or fund universe normalization.

---

### AI Analyst Tools

- Provide narrative or Q&A
- Assume structured data exists
- Not built around deterministic evaluation + audit linkage

They operate after normalization, not before it.

---

## D) Prioritization Decisions and Rationale

Based on the above, we prioritize:

### 1. Data Normalization Layer First

Because:

- It is the highest friction point.
- It is the least solved by existing tools.
- It drives recurring monthly workflow usage.
- It creates structural lock-in.

Without solving preprocessing, we are merely another ranking tool.

---

### 2. Deterministic Decision Engine Before Advanced AI

Because:

- Trust is built on deterministic, reproducible metrics.
- AI narrative without traceability reduces credibility.
- Institutional adoption requires auditability.

AI is layered on top of structured facts, not replacing them.

---

### 3. Efficiency First, Intelligence Later

Version 1 focus:

- Remove manual normalization friction.
- Create consistent evaluation workflow.
- Introduce structured traceability.

Deep differentiation (adaptive models, portfolio simulation, cross-run memory) comes later.

---

## Positioning Statement

The Allocator Decision Engine is:

A structured normalization and decision workflow system for investment analysts.

It is not:

- A robo allocator
- A DDQ automation tool
- A generic AI memo generator
- A market data provider

It is a deterministic evaluation kernel with structured auditability.

---
