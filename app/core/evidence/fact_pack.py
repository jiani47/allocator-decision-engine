"""Fact pack builder and memo prompt construction."""

from __future__ import annotations

import json
from datetime import date

from app.core.schemas import (
    FactPack,
    MandateConfig,
    MetricId,
    NormalizedUniverse,
    PortfolioContext,
    ReRankRationale,
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
    ai_rationales: list[ReRankRationale] | None = None,
    portfolio_context: PortfolioContext | None = None,
) -> FactPack:
    """Assemble the fact pack that the LLM will use."""
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
        ai_rationales=ai_rationales or [],
        portfolio_context=portfolio_context,
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

    # Build AI rationales section if present
    ai_rationales_section = ""
    if fact_pack.ai_rationales:
        rationale_lines = []
        for rr in sorted(fact_pack.ai_rationales, key=lambda r: r.llm_rank):
            factors = ", ".join(rr.key_factors) if rr.key_factors else "none"
            rationale_lines.append(
                f"- **{rr.fund_name}** (AI Rank #{rr.llm_rank}, "
                f"Det. Rank #{rr.deterministic_rank}): "
                f"{rr.rationale} [key factors: {factors}]"
            )
        ai_rationales_section = f"""

## AI-Assisted Ranking Context

An AI analyst re-ranked the shortlist considering qualitative factors (fees, strategy fit,
liquidity, data quality) alongside quantitative metrics. The ranking above reflects the
AI-assisted order. Incorporate these qualitative insights into the memo's analysis.

{chr(10).join(rationale_lines)}
"""

    # Build portfolio context section if present
    portfolio_context_section = ""
    if fact_pack.portfolio_context:
        pc = fact_pack.portfolio_context
        holdings_lines = []
        for h in pc.holdings:
            holdings_lines.append(
                f"  - {h.get('fund_name', 'Unknown')} ({h.get('strategy', 'N/A')}): "
                f"{h.get('weight', 0) * 100:.1f}% allocation"
            )
        gov_items = []
        for k, v in pc.governance.items():
            if v is not None:
                gov_items.append(f"  - {k}: {v}")
        portfolio_context_section = f"""

## Portfolio Context

This allocation is being made for **{pc.portfolio_name}** ({pc.strategy}).
{f"AUM: ${pc.aum / 1_000_000:.0f}M" if pc.aum else ""}

**Current Holdings:**
{chr(10).join(holdings_lines) if holdings_lines else "  (none)"}

**Governance Mandate Floors:**
{chr(10).join(gov_items) if gov_items else "  (none)"}

When drafting the memo, consider how new allocations fit within this existing portfolio — discuss diversification benefits, overlap with current holdings, and compliance with governance constraints.
"""

    ranking_basis = "AI-assisted" if fact_pack.ai_rationales else "deterministic"

    prompt = f"""You are a senior investment analyst drafting an Investment Committee (IC) memo.

Based on the following {ranking_basis} evaluation results, draft a structured IC memo.

## Evaluation Data

**Date:** {date.today().isoformat()}
**Universe:** {json.dumps(fact_pack.universe_summary)}
**Benchmark:** {fact_pack.benchmark_symbol}
**Mandate Configuration:** {json.dumps(mandate_data, default=str)}
{group_context_section}
**Ranked Shortlist ({n_funds} fund(s)):**
{json.dumps(shortlist_data, indent=2, default=str)}
{analyst_notes_section}{ai_rationales_section}{portfolio_context_section}
## Instructions

1. Draft a professional IC memo with sections: Executive Summary, Universe Overview, Top Recommendations, Risk Considerations, Constraint Analysis. This memo covers {scope_description}.
2. The shortlist contains the top {n_funds} fund(s). Provide analysis of ALL {n_funds} fund(s) in the shortlist. Do not omit any fund from the analysis.
3. Every factual claim MUST reference specific metric_id values from this list: {[m.value for m in MetricId]}
4. Every claim MUST reference specific fund names from the shortlist.
5. Do NOT invent any numbers not present in the data above.
6. Do NOT hallucinate performance figures.
7. Format numbers appropriately (percentages for returns/vol/drawdown, ratios for Sharpe).
8. If analyst data quality notes are provided above, include a "Data Quality Notes" section at the end of the memo summarizing the analyst's review decisions.
9. In the Top Recommendations section, reference funds by rank (e.g., 'Rank #1'), not by composite score.
10. If Portfolio Context is provided above, include a "Portfolio Fit" section discussing how recommended funds complement the existing holdings, any strategy overlaps, and governance compliance.

## Output Format

Output ONLY the memo text in markdown format. Do NOT wrap in JSON or code fences. Start directly with the markdown heading."""

    return prompt


def build_claims_prompt(memo_text: str, fact_pack: FactPack) -> str:
    """Build a prompt to extract claims from a finished memo."""
    fund_names = [sf.fund_name for sf in fact_pack.shortlist]
    metric_ids = [m.value for m in MetricId]

    return f"""Locate exact sentences in the following IC memo that make factual claims about fund performance.

## Memo Text

{memo_text}

## Instructions

1. Identify 3-8 key sentences that assert specific numeric facts about funds.
2. Each claim MUST reference at least one metric_id from: {metric_ids}
3. Each claim MUST reference at least one fund name from: {fund_names}
4. The `source_text` field MUST be an exact verbatim copy of a sentence from the memo above. Do NOT paraphrase, shorten, or alter it in any way. It will be used for exact text matching against the memo.
5. The `claim_text` field should be a short human-readable summary of the claim (can be paraphrased).

## Output Format

Return ONLY valid JSON matching this exact schema:
{{
  "claims": [
    {{
      "claim_id": "claim_1",
      "claim_text": "Short summary of the factual claim",
      "source_text": "Copy the exact sentence from the memo verbatim — it must appear character-for-character in the memo text above",
      "referenced_metric_ids": ["annualized_return", "sharpe_ratio"],
      "referenced_fund_names": ["Fund Name"]
    }}
  ]
}}"""


MEMO_SYSTEM_PROMPT = (
    "You are a senior investment analyst at a fund-of-funds. "
    "You produce structured, evidence-based IC memos. "
    "You never invent numbers — you only reference data provided to you."
)


CLAIMS_SYSTEM_PROMPT = (
    "You are an analyst extracting factual claims from IC memos. "
    "You output only valid JSON."
)
