# Pipeline Restructuring: Mandate-First, Per-Group Ranking & Memo

## Context

After testing the current 10-step linear pipeline, several UX and workflow issues were identified:
1. **Steps 1-2 feel disconnected** — review interpretation / review warnings / normalize should be a single iterative loop, not 3 linear steps
2. **Mandate should come FIRST** — the analyst already knows their hard rules before seeing the data
3. **Single global benchmark doesn't make sense** — different fund groups should have different benchmarks
4. **Ranking should be per-group** — comparing a value fund against a growth fund is meaningless
5. **One memo per group** — each peer group gets its own IC memo
6. **UI is a 960-line monolith** — `app/ui.py` must be decomposed into reusable widgets and step modules

**Goal:** Restructure the pipeline from 10 linear steps to 9 steps with mandate-first flow, LLM-powered fund grouping, per-group benchmarks/ranking/memos. Decompose monolithic UI into maintainable components.

---

## New Pipeline Flow

| Step | Name | Description |
|------|------|-------------|
| 0 | Mandate | Hard constraints + scoring weights (analyst knows these upfront) |
| 1 | Upload & Process | Upload → parse → LLM extract → normalize → classify eligible/ineligible |
| 2 | Review & Resolve | Combined: interpretation + warnings + eligibility. Ineligible funds grayed out |
| 3 | Fund Grouping | Standard criteria + free text → LLM classifies eligible funds into groups |
| 4 | Group Review & Benchmark | Review/reassign groups, select per-group benchmark |
| 5 | Metrics & Ranking | Per-group metrics computation and ranking |
| 6 | Memo | Per-group IC memo generation |
| 7 | Audit | Per-group claim auditing with source worksheet |
| 8 | Export | Combined or per-group export |

---

## UI Architecture: Component Decomposition

### Current Problem

`app/ui.py` is a 960-line monolith containing: session state management, sidebar, 10 step blocks, helper functions, HTML rendering, and all layout logic. Repeating patterns (navigation buttons, fund tables, metric formatting, alert blocks) are copy-pasted across steps.

### Target Structure

```
app/
  ui.py                         → app entry point: page config, step router, sidebar
  ui/
    __init__.py
    state.py                    → session state: STEPS, _go_to, _reset_from, key cascade
    sidebar.py                  → progress indicator sidebar
    widgets/
      __init__.py
      navigation.py             → back/continue/skip button columns
      fund_table.py             → configurable fund summary dataframe
      metric_format.py          → metric value formatting (%, ratio, NaN)
      alert_block.py            → info/warning/error with optional bullet lists
      warning_panel.py          → per-warning expanders with ack/ignore + notes
      worksheet_viewer.py       → Excel-like HTML table with row highlighting
      fund_details.py           → fund detail expander (metadata + sample returns + source rows)
    steps/
      __init__.py
      step_mandate.py           → Step 0: Mandate form
      step_upload.py            → Step 1: Upload & Process
      step_review.py            → Step 2: Review & Resolve
      step_grouping.py          → Step 3: Fund Grouping
      step_group_config.py      → Step 4: Group Review & Benchmark
      step_ranking.py           → Step 5: Metrics & Ranking (per-group tabs)
      step_memo.py              → Step 6: Memo (per-group tabs)
      step_audit.py             → Step 7: Audit (per-group tabs)
      step_export.py            → Step 8: Export
```

### Reusable Widgets

**`navigation.py`** — Used by every step (currently repeated 7+ times):
```python
def render_nav_buttons(
    back_label: str = "Back",
    back_step: int | None = None,
    forward_label: str = "Continue",
    forward_step: int | None = None,
    forward_primary: bool = True,
    skip_label: str | None = None,
    skip_step: int | None = None,
) -> str | None:
    """Render back/forward/skip button row. Returns which was clicked."""
```

**`fund_table.py`** — Used in review, grouping, ranking steps:
```python
def render_fund_table(
    funds: list[NormalizedFund],
    columns: list[str] = ["fund_name", "strategy", "months", "date_range"],
    eligibility: dict[str, bool] | None = None,  # gray out ineligible
    metrics: dict[str, FundMetrics] | None = None,
    scores: dict[str, ScoredFund] | None = None,
) -> None:
```

**`metric_format.py`** — Used in metrics, ranking, audit steps:
```python
def format_metric(metric_id: MetricId, value: float) -> str:
    """Format metric value: percentages for return/vol/DD, ratio for Sharpe."""
```

**`alert_block.py`** — Used in review, upload, grouping steps:
```python
def render_alerts(
    notes: str | None = None,        # st.info
    ambiguities: list[str] | None = None,  # st.warning bullet list
    errors: list[str] | None = None,       # st.error bullet list
) -> None:
```

**`warning_panel.py`** — Used in review step:
```python
def render_warning_panel(
    warnings: list[ValidationWarning],
    dismissed: set[int],
    eligible_only: bool = False,
) -> None:
    """Render per-warning expanders with ack/ignore buttons and notes."""
```

**`worksheet_viewer.py`** — Existing `_render_worksheet_html()` + `_get_highlight_rows_for_claim()` + `_HIGHLIGHT_COLORS` extracted as-is.

**`fund_details.py`** — Used in review step:
```python
def render_fund_card(fund: LLMExtractedFund, raw_context: RawFileContext) -> None:
    """Render fund detail expander with metadata, sample returns, source rows."""
```

### Entry Point (`app/ui.py`)

Reduced to ~50 lines: page config, session state init, sidebar, step router:
```python
from app.ui.state import STEPS, init_state
from app.ui.sidebar import render_sidebar
from app.ui.steps import (
    step_mandate, step_upload, step_review, step_grouping,
    step_group_config, step_ranking, step_memo, step_audit, step_export,
)

st.set_page_config(...)
init_state()
render_sidebar()

STEP_RENDERERS = [
    step_mandate.render, step_upload.render, step_review.render,
    step_grouping.render, step_group_config.render, step_ranking.render,
    step_memo.render, step_audit.render, step_export.render,
]
STEP_RENDERERS[st.session_state["step"]]()
```

---

## Schema Changes

### New Models (`app/core/schemas.py`)

```python
class FundEligibility(BaseModel):
    """Mandate-based eligibility classification per fund."""
    fund_name: str
    eligible: bool
    failing_constraints: list[ConstraintResult] = Field(default_factory=list)

class GroupingCriteria(BaseModel):
    """User-provided criteria for LLM fund grouping."""
    standard_criteria: list[str] = Field(default_factory=list)
    free_text: str = ""
    max_groups: int = 2

class FundGroup(BaseModel):
    """A group of funds with its own benchmark."""
    group_name: str
    group_id: str
    fund_names: list[str]
    benchmark_symbol: str | None = None
    benchmark: BenchmarkSeries | None = None
    grouping_rationale: str = ""

class GroupRun(BaseModel):
    """Per-group ranking, metrics, and memo."""
    group: FundGroup
    fund_metrics: list[FundMetrics]
    ranked_shortlist: list[ScoredFund]
    run_candidates: list[RunCandidate]
    memo: MemoOutput | None = None
    fact_pack: FactPack | None = None

class LLMGroupingResult(BaseModel):
    """Structured result from LLM fund grouping."""
    groups: list[FundGroup]
    rationale: str
    ambiguities: list[str] = Field(default_factory=list)
```

### Modified Models

**`MandateConfig`** — remove `strategy_include`/`strategy_exclude` (strategy filtering moves to grouping step — analyst doesn't know strategies upfront). Add `min_history_months: int = 12`.

**`DecisionRun`** — add: `fund_eligibility: list[FundEligibility]`, `grouping_criteria: GroupingCriteria | None`, `group_runs: list[GroupRun]`. Keep old fields with defaults for backward compat.

**`FactPack`** — add: `group_name: str = ""`, `group_rationale: str = ""`.

---

## Service Layer Changes

### New Functions (`app/services.py`)

- `step_classify_eligibility(universe, all_metrics, mandate)` → `list[FundEligibility]` — reuses existing `build_constraints()` + `evaluate_constraints()`
- `step_group_funds(universe, eligibility, criteria, all_metrics, settings)` → `LLMGroupingResult` — calls new LLM grouping service
- `_build_group_universe(universe, group)` → `NormalizedUniverse` — filters universe to group's funds only
- `step_rank_group(universe, group, mandate, settings)` → `GroupRun` — fetch benchmark + compute metrics + rank, all scoped to group
- `step_generate_group_memo(group_run, universe, mandate, settings, ...)` → `GroupRun` — generate memo for one group

### New LLM Service (`app/llm/grouping_service.py`)

Follows existing pattern of `ingestion_service.py`:
- `GROUPING_SYSTEM_PROMPT` — instructs LLM to be a fund classifier
- `build_grouping_prompt(eligible_funds, raw_context, criteria, fund_metrics)` — serializes fund data + criteria
- `classify_funds_into_groups(client, ...)` → `LLMGroupingResult` — calls Claude, parses JSON, validates
- `validate_grouping(result, eligible_fund_names)` — checks every fund in exactly one group

### Modules Reused Without Changes

All existing core modules work as-is when called per group with filtered sub-universes:
- `app/core/metrics/` — all metric computation
- `app/core/scoring/normalize.py` — min-max normalization (within-group)
- `app/core/scoring/ranking.py` — `rank_universe()` (per group)
- `app/core/constraints/` — all constraint classes
- `app/domains/alt_invest/raw_parser.py`, `ingest.py`, `benchmark.py`
- `app/llm/anthropic_client.py`, `ingestion_service.py`

---

## Key Design Decisions

1. **Strategy filtering → grouping, not mandate.** Analyst doesn't know strategies upfront.
2. **Single DecisionRun with GroupRun sub-records.** One export covers everything.
3. **Group-scoped normalization.** Min-max within each group for peer comparison.
4. **Existing core reused as-is.** Called per group with filtered sub-universes.
5. **Max 2 groups (configurable).** Via `config.py`, enforced by LLM prompt and UI.
6. **UI decomposed into widgets + step modules.** Entry point reduced to step router.
