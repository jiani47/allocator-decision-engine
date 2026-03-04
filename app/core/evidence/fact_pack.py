"""Fact pack builder and memo prompt construction."""

from __future__ import annotations

import json

from app.core.schemas import (
    FactPack,
    MandateConfig,
    MetricId,
    NormalizedUniverse,
    ScoredFund,
    WarningResolution,
)


def build_fact_pack(
    run_id: str,
    shortlist: list[ScoredFund],
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark_symbol: str,
    analyst_notes: list[WarningResolution] | None = None,
    group_name: str = "",
    group_rationale: str = "",
) -> FactPack:
    """Assemble the deterministic fact pack that the LLM will use."""
    universe_summary = {
        "total_funds": len(universe.funds),
        "date_range": f"{min(f.date_range_start for f in universe.funds)} to {max(f.date_range_end for f in universe.funds)}",
        "strategies": list({f.strategy for f in universe.funds if f.strategy}),
        "warning_count": len(universe.warnings),
    }

    return FactPack(
        run_id=run_id,
        shortlist=shortlist,
        universe_summary=universe_summary,
        mandate=mandate,
        benchmark_symbol=benchmark_symbol,
        analyst_notes=analyst_notes or [],
        group_name=group_name,
        group_rationale=group_rationale,
    )


def build_memo_prompt(fact_pack: FactPack) -> str:
    """Convert fact pack to a structured prompt for the LLM."""
    # Serialize shortlist for the prompt
    shortlist_data = []
    for sf in fact_pack.shortlist:
        fund_data = {
            "fund_name": sf.fund_name,
            "rank": sf.rank,
            "composite_score": round(sf.composite_score, 4),
            "all_constraints_passed": sf.all_constraints_passed,
            "metrics": {k.value: round(v, 6) if v is not None else None for k, v in sf.metric_values.items()},
            "score_breakdown": [
                {
                    "metric": sc.metric_id.value,
                    "raw": round(sc.raw_value, 6) if sc.raw_value is not None else None,
                    "normalized": round(sc.normalized_value, 4),
                    "weight": sc.weight,
                    "contribution": round(sc.weighted_contribution, 4),
                }
                for sc in sf.score_breakdown
            ],
            "constraint_results": [
                {"name": cr.constraint_name, "passed": cr.passed, "explanation": cr.explanation}
                for cr in sf.constraint_results
            ],
        }
        shortlist_data.append(fund_data)

    mandate_data = fact_pack.mandate.model_dump()
    n_funds = len(fact_pack.shortlist)

    # Build analyst notes section if present
    analyst_notes_section = ""
    if fact_pack.analyst_notes:
        notes_lines = []
        for note in fact_pack.analyst_notes:
            fund_str = f' Fund "{note.fund_name}"' if note.fund_name else ""
            analyst_str = f' -- Analyst: "{note.analyst_note}"' if note.analyst_note else ""
            notes_lines.append(
                f"- [{note.category}]{fund_str}: {note.original_message} "
                f"(Action: {note.action}){analyst_str}"
            )
        analyst_notes_section = f"""

## Analyst Data Quality Notes

The analyst reviewed the following data quality warnings and provided these notes.
Include a "Data Quality Notes" section at the end of the memo summarizing these items.

{chr(10).join(notes_lines)}
"""

    # Build group context section if present
    group_context_section = ""
    scope_description = "the shortlist"
    if fact_pack.group_name:
        group_context_section = f"""
**Group:** {fact_pack.group_name}
**Grouping Rationale:** {fact_pack.group_rationale}
"""
        scope_description = f"the **{fact_pack.group_name}** peer group ({n_funds} funds)"

    prompt = f"""You are a senior investment analyst drafting an Investment Committee (IC) memo.

Based on the following deterministic evaluation results, draft a structured IC memo.

## Evaluation Data

**Universe:** {json.dumps(fact_pack.universe_summary)}
**Benchmark:** {fact_pack.benchmark_symbol}
**Mandate Configuration:** {json.dumps(mandate_data, default=str)}
{group_context_section}
**Ranked Shortlist ({n_funds} fund(s)):**
{json.dumps(shortlist_data, indent=2, default=str)}
{analyst_notes_section}
## Instructions

1. Draft a professional IC memo with sections: Executive Summary, Universe Overview, Top Recommendations, Risk Considerations, Constraint Analysis. This memo covers {scope_description}.
2. The shortlist contains the top {n_funds} fund(s). Provide analysis of ALL {n_funds} fund(s) in the shortlist. Do not omit any fund from the analysis.
3. Every factual claim MUST reference specific metric_id values from this list: {[m.value for m in MetricId]}
4. Every claim MUST reference specific fund names from the shortlist.
5. Do NOT invent any numbers not present in the data above.
6. Do NOT hallucinate performance figures.
7. Format numbers appropriately (percentages for returns/vol/drawdown, ratios for Sharpe).
8. If analyst data quality notes are provided above, include a "Data Quality Notes" section at the end of the memo summarizing the analyst's review decisions.

## Output Format

Return ONLY valid JSON matching this exact schema:
{{
  "memo_text": "The full memo text in markdown format",
  "claims": [
    {{
      "claim_id": "claim_1",
      "claim_text": "The exact sentence containing a factual claim",
      "referenced_metric_ids": ["annualized_return", "sharpe_ratio"],
      "referenced_fund_names": ["Fund Name"]
    }}
  ]
}}

Extract 3-8 key factual claims from your memo. Each claim must have at least one metric_id and one fund_name reference."""

    return prompt


MEMO_SYSTEM_PROMPT = (
    "You are a senior investment analyst at a fund-of-funds. "
    "You produce structured, evidence-based IC memos. "
    "You never invent numbers — you only reference data provided to you. "
    "You always output valid JSON."
)
