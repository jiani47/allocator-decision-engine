"""Fact pack builder and memo prompt construction."""

from __future__ import annotations

import json

from app.core.schemas import (
    FactPack,
    MandateConfig,
    MetricId,
    NormalizedUniverse,
    ScoredFund,
)


def build_fact_pack(
    run_id: str,
    shortlist: list[ScoredFund],
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark_symbol: str,
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
            "metrics": {k.value: round(v, 6) for k, v in sf.metrics.items()},
            "constraint_results": [
                {"name": cr.constraint_name, "passed": cr.passed, "explanation": cr.explanation}
                for cr in sf.constraint_results
            ],
        }
        shortlist_data.append(fund_data)

    mandate_data = fact_pack.mandate.model_dump()

    prompt = f"""You are a senior investment analyst drafting an Investment Committee (IC) memo.

Based on the following deterministic evaluation results, draft a structured IC memo.

## Evaluation Data

**Run ID:** {fact_pack.run_id}
**Universe:** {json.dumps(fact_pack.universe_summary)}
**Benchmark:** {fact_pack.benchmark_symbol}
**Mandate Configuration:** {json.dumps(mandate_data, default=str)}

**Ranked Shortlist:**
{json.dumps(shortlist_data, indent=2, default=str)}

## Instructions

1. Draft a professional IC memo with sections: Executive Summary, Universe Overview, Top Recommendations, Risk Considerations, Constraint Analysis.
2. Every factual claim MUST reference specific metric_id values from this list: {[m.value for m in MetricId]}
3. Every claim MUST reference specific fund names from the shortlist.
4. Do NOT invent any numbers not present in the data above.
5. Do NOT hallucinate performance figures.
6. Format numbers appropriately (percentages for returns/vol/drawdown, ratios for Sharpe).

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
