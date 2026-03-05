"""LLM-based fund re-ranking service."""

from __future__ import annotations

import json
import logging
import math

from pydantic import ValidationError

from app.core.exceptions import ReRankError
from app.core.schemas import (
    LLMReRankResult,
    MandateConfig,
    NormalizedFund,
    NormalizedUniverse,
    ScoredFund,
    WarningResolution,
)
from app.llm.anthropic_client import AnthropicClient

logger = logging.getLogger("equi.llm.rerank")

RERANK_SYSTEM_PROMPT = """\
You are a senior fund-of-funds analyst at an institutional allocator.

Your task is to re-rank a shortlist of funds by combining quantitative metrics \
with qualitative judgment. Consider fee burden, strategy relevance to the mandate, \
liquidity constraints, and data quality when adjusting rankings.

Rules:
- You MUST include every fund from the input in your output (no additions, no removals).
- Reference specific metric_id values (annualized_return, annualized_volatility, \
sharpe_ratio, max_drawdown, benchmark_correlation) in your rationales.
- Never invent or fabricate numbers. Only reference values provided in the input.
- Each rationale should be 2-4 sentences explaining why the fund moved up, down, or stayed.
- key_factors should be short tags like "low_fees", "strategy_fit", "high_sharpe", \
"liquidity_risk", "data_quality_concern", etc.
- The overall_commentary should be 1-2 paragraphs summarizing key themes.

Respond with valid JSON matching this schema:
{
  "reranked_funds": [
    {
      "fund_name": "string",
      "llm_rank": integer,
      "deterministic_rank": integer,
      "rationale": "string (2-4 sentences)",
      "key_factors": ["string", ...],
      "referenced_metric_ids": ["annualized_return", ...]
    }
  ],
  "overall_commentary": "string (1-2 paragraphs)",
  "model_used": "string"
}
"""


def _build_rerank_prompt(
    ranked_shortlist: list[ScoredFund],
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark_symbol: str | None,
    warning_resolutions: list[WarningResolution] | None,
) -> str:
    """Build the user prompt for re-ranking."""
    fund_lookup: dict[str, NormalizedFund] = {
        f.fund_name: f for f in universe.funds
    }

    lines = [
        "# Fund Re-Ranking Request",
        "",
        f"**Mandate:** {mandate.name}",
        f"**Benchmark:** {benchmark_symbol or 'None'}",
        f"**Scoring weights:** {json.dumps({k.value: v for k, v in mandate.weights.items()})}",
        "",
        "## Ranked Funds (deterministic ranking)",
        "",
    ]

    for sf in ranked_shortlist:
        nf = fund_lookup.get(sf.fund_name)
        lines.append(f"### {sf.fund_name}")
        lines.append(f"- Deterministic rank: {sf.rank}")
        lines.append(f"- Composite score: {sf.composite_score:.4f}")
        lines.append(f"- All constraints passed: {sf.all_constraints_passed}")

        # Metric values
        for mid, val in sf.metric_values.items():
            if val is not None and not math.isnan(val):
                lines.append(f"- {mid}: {val:.6f}")

        # Qualitative metadata from universe
        if nf:
            if nf.strategy:
                lines.append(f"- Strategy: {nf.strategy}")
            if nf.liquidity_days is not None:
                lines.append(f"- Liquidity days: {nf.liquidity_days}")
            if nf.management_fee is not None:
                lines.append(f"- Management fee: {nf.management_fee:.4f}")
            if nf.performance_fee is not None:
                lines.append(f"- Performance fee: {nf.performance_fee:.4f}")

        lines.append("")

    # Mandate constraints context
    lines.append("## Mandate Constraints")
    if mandate.min_liquidity_days is not None:
        lines.append(f"- Min liquidity days: {mandate.min_liquidity_days}")
    if mandate.max_drawdown_tolerance is not None:
        lines.append(f"- Max drawdown tolerance: {mandate.max_drawdown_tolerance}")
    if mandate.target_volatility is not None:
        lines.append(f"- Target volatility: {mandate.target_volatility}")
    if mandate.min_annualized_return is not None:
        lines.append(f"- Min annualized return: {mandate.min_annualized_return}")
    if mandate.min_sharpe_ratio is not None:
        lines.append(f"- Min Sharpe ratio: {mandate.min_sharpe_ratio}")
    if mandate.strategy_include:
        lines.append(f"- Strategy include: {mandate.strategy_include}")
    if mandate.strategy_exclude:
        lines.append(f"- Strategy exclude: {mandate.strategy_exclude}")
    lines.append("")

    # Warning resolutions (data quality notes)
    if warning_resolutions:
        lines.append("## Analyst Data Quality Notes")
        for wr in warning_resolutions:
            note = f"- [{wr.category}] {wr.original_message}"
            if wr.analyst_note:
                note += f" — Analyst note: {wr.analyst_note}"
            lines.append(note)
        lines.append("")

    lines.append(
        "Re-rank these funds considering both the quantitative metrics above "
        "and qualitative factors (fees, strategy fit, liquidity, data quality). "
        "Explain your reasoning for each fund's position change."
    )

    return "\n".join(lines)


def rerank_funds(
    client: AnthropicClient,
    ranked_shortlist: list[ScoredFund],
    universe: NormalizedUniverse,
    mandate: MandateConfig,
    benchmark_symbol: str | None = None,
    warning_resolutions: list[WarningResolution] | None = None,
) -> LLMReRankResult:
    """Re-rank funds using LLM. Fail closed on invalid output."""
    prompt = _build_rerank_prompt(
        ranked_shortlist, universe, mandate, benchmark_symbol, warning_resolutions
    )
    raw = client.generate(prompt, RERANK_SYSTEM_PROMPT)

    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ReRankError(f"LLM returned invalid JSON: {e}") from e

    # Inject model_used if not present
    if "model_used" not in data:
        data["model_used"] = client._model

    try:
        result = LLMReRankResult.model_validate(data)
    except ValidationError as e:
        raise ReRankError(f"LLM output failed schema validation: {e}") from e

    # Validate all funds are present
    input_names = {sf.fund_name for sf in ranked_shortlist}
    output_names = {r.fund_name for r in result.reranked_funds}
    missing = input_names - output_names
    if missing:
        logger.warning("LLM re-rank missing funds: %s", missing)

    logger.info(
        "LLM re-ranked %d funds", len(result.reranked_funds)
    )

    return result
