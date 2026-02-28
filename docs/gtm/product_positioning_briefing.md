# Allocator Decision Engine — Product Positioning
## Analyst-First Strategy (Fund-of-Funds Focus)

---

## Target Customer

Independent RIAs and Fund-of-Funds platforms evaluating external hedge funds, private credit, private equity, and alternative managers.

## Core Thesis

Fund-of-funds firms are not lacking performance analytics tools.
They are lacking structured, repeatable, defensible decision workflows.

The Allocator Decision Engine is a normalization and decision structuring platform purpose-built for alternative investment analysts.

---

## Primary User Persona

### Investment Analyst (Allocator, Fund-of-Funds / RIA)

We deliberately choose the lower-ranking investment analyst — not the CIO or committee — as the primary user.

Why:

1. Analysts own the data processing and preparation workflow.
2. Analysts feel the operational pain most directly.
3. Analysts are the internal champions who influence tool adoption.
4. If analysts trust and reuse the system, committee buy-in follows naturally.
5. If analysts do not adopt it, committee-level positioning is irrelevant.

The product is designed as a force multiplier for analysts, not as an executive AI dashboard.

---

## What Makes This Fund-of-Funds Specific

Unlike generic analytics tools, this product understands:

- Heterogeneous manager reporting formats
- Inconsistent time series lengths
- Liquidity gating terms
- Fee structure variance
- Strategy classification ambiguity
- Mandate-driven filtering logic

It embeds allocator workflow into the system.

---

## Current Stack & Pain Points

### Current Stack

Typical analyst workflow includes:

- CSV / Excel files from fund managers
- Excel for normalization and metric computation
- Word or Google Docs for IC memo drafting
- Email + shared drives for document exchange
- Possibly a performance analytics platform (metrics only)

### Pain Point 1: Data Normalization & Validation

Analysts receive messy, unnormalized data from managers. This requires schema understanding, column mapping, date normalization, handling missing data, detecting anomalies, aligning time ranges, and verifying completeness.

This preprocessing step is: manual, repetitive, error-prone, poorly documented, and difficult to reproduce. Before any metric is computed, substantial manual effort is required.

### Pain Point 2: Lack of Traceability in Decision Outputs

After normalization, metrics are computed in Excel and memo claims are written manually. No structured link exists between raw data, metric calculations, and memo claims.

This creates risk: hard to defend numbers in committee, no audit trail, difficult to reproduce past decisions, knowledge locked in spreadsheets.

---

## Why Existing Tools Do Not Solve This

### Excel

- Flexible but fragile. No schema enforcement, no repeatability, no built-in audit graph.
- Solves computation flexibility, not process structure.

### Analytics Suites

- Compute metrics, provide dashboards, but assume clean structured data.
- Do not solve messy ingestion. Do not generate traceable IC memos.
- They solve analysis, not normalization + traceability.

### DDQ / Workflow Tools

- Focus on document management, questionnaire tracking, compliance workflows.
- Do not address metric grounding or fund universe normalization.

### AI Analyst Tools

- Provide narrative or Q&A, but assume structured data exists.
- Not built around deterministic evaluation + audit linkage.
- They operate after normalization, not before it.

---

## Prioritization Decisions

### 1. Data Normalization Layer First

It is the highest friction point, the least solved by existing tools, drives recurring monthly workflow usage, and creates structural lock-in. Without solving preprocessing, we are merely another ranking tool.

### 2. Deterministic Decision Engine Before Advanced AI

Trust is built on deterministic, reproducible metrics. AI narrative without traceability reduces credibility. Institutional adoption requires auditability. AI is layered on top of structured facts, not replacing them.

### 3. Efficiency First, Intelligence Later

V1: remove manual normalization friction, create consistent evaluation workflow, introduce structured traceability. Deep differentiation (adaptive models, portfolio simulation, cross-run memory) comes later.

---

## Positioning Statement

For fund-of-funds analysts who receive inconsistent manager data and must produce defendable IC memos, the Allocator Decision Engine converts messy fund reports into normalized, validated, ranked, and traceable investment decisions.

Unlike Excel or generic analytics dashboards, it enforces repeatable normalization and links every memo claim back to raw performance data.

It is not: a robo allocator, a DDQ automation tool, a generic AI memo generator, or a market data provider.

It is a deterministic evaluation kernel with structured auditability.
