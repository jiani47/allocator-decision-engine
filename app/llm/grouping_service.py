"""LLM-based fund grouping into comparison peer groups."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.core.exceptions import FundGroupingError
from app.core.schemas import (
    FundMetrics,
    GroupingCriteria,
    LLMGroupingResult,
    MetricId,
    NormalizedFund,
    RawFileContext,
)
from app.llm.anthropic_client import AnthropicClient

logger = logging.getLogger("equi.llm.grouping")

GROUPING_SYSTEM_PROMPT = """\
You are a fund-of-funds analyst classifying investment funds into comparison peer groups.

Your task is to assign each eligible fund to exactly one peer group based on the data provided.

Rules:
- Use the fund data provided: strategy, key metrics, liquidity, and fees.
- Use any unstructured notes from the raw file context if available.
- Follow the analyst's standard criteria and free text instructions closely.
- Each fund must go into exactly one group — no fund may be left out or duplicated.
- The number of groups must not exceed the specified max_groups.
- Provide a descriptive group_name and a rationale for each group.
- Provide an overall rationale explaining your grouping approach.
- If any assignments are uncertain, list them in the ambiguities array.
- Do NOT invent fund names. Only use the fund names provided.

Respond with valid JSON matching this schema:
{
  "groups": [
    {
      "group_name": "descriptive name for the peer group",
      "group_id": "group_1",
      "fund_names": ["Fund A", "Fund B"],
      "grouping_rationale": "why these funds are grouped together"
    }
  ],
  "rationale": "overall explanation of grouping approach",
  "ambiguities": ["any uncertain assignments or edge cases"]
}
"""


def build_grouping_prompt(
    eligible_funds: list[NormalizedFund],
    raw_context: RawFileContext | None,
    criteria: GroupingCriteria,
    fund_metrics: list[FundMetrics],
) -> str:
    """Build the user prompt from eligible fund data and grouping criteria."""
    metrics_by_name = {m.fund_name: m for m in fund_metrics}

    lines = [
        f"Number of eligible funds: {len(eligible_funds)}",
        f"Maximum groups allowed: {criteria.max_groups}",
        "",
        "--- Eligible Funds ---",
    ]

    for fund in eligible_funds:
        lines.append(f"\nFund: {fund.fund_name}")
        lines.append(f"  Strategy: {fund.strategy or 'N/A'}")
        lines.append(f"  Liquidity days: {fund.liquidity_days or 'N/A'}")
        lines.append(f"  Management fee: {fund.management_fee or 'N/A'}")
        lines.append(f"  Performance fee: {fund.performance_fee or 'N/A'}")

        fm = metrics_by_name.get(fund.fund_name)
        if fm and not fm.insufficient_history:
            ann_ret = fm.get_value(MetricId.ANNUALIZED_RETURN)
            vol = fm.get_value(MetricId.ANNUALIZED_VOLATILITY)
            sharpe = fm.get_value(MetricId.SHARPE_RATIO)
            max_dd = fm.get_value(MetricId.MAX_DRAWDOWN)
            lines.append("  Key metrics:")
            lines.append(f"    Annualized return: {ann_ret}")
            lines.append(f"    Annualized volatility: {vol}")
            lines.append(f"    Sharpe ratio: {sharpe}")
            lines.append(f"    Max drawdown: {max_dd}")

    # Include analyst criteria
    lines.append("")
    lines.append("--- Grouping Criteria ---")
    if criteria.standard_criteria:
        lines.append("Standard criteria:")
        for c in criteria.standard_criteria:
            lines.append(f"  - {c}")
    if criteria.free_text:
        lines.append(f"Analyst instructions: {criteria.free_text}")

    # Include raw context notes if available (non-numeric cell data)
    if raw_context and raw_context.data_rows:
        # Extract any notes columns — look for cells that are non-numeric text
        notes_found = False
        for row in raw_context.data_rows:
            for cell in row.cells:
                if cell and not _is_numeric(cell) and len(cell) > 20:
                    if not notes_found:
                        lines.append("")
                        lines.append("--- Additional Notes from Source File ---")
                        notes_found = True
                    lines.append(f"  Row {row.row_index}: {cell}")
                    break  # One note per row is enough

    lines.append("")
    lines.append(
        f"Classify the {len(eligible_funds)} funds above into at most "
        f"{criteria.max_groups} peer groups. "
        "Every fund must appear in exactly one group."
    )

    return "\n".join(lines)


def _is_numeric(s: str) -> bool:
    """Check if a string looks like a number."""
    try:
        float(s.replace("%", "").replace(",", "").strip())
        return True
    except ValueError:
        return False


def classify_funds_into_groups(
    client: AnthropicClient,
    eligible_funds: list[NormalizedFund],
    raw_context: RawFileContext | None,
    criteria: GroupingCriteria,
    fund_metrics: list[FundMetrics],
) -> LLMGroupingResult:
    """Classify eligible funds into peer groups using LLM.

    Follows the same pattern as ingestion_service.extract_funds_via_llm():
    prompt -> LLM -> strip fences -> JSON parse -> Pydantic validate -> fail closed.
    """
    prompt = build_grouping_prompt(eligible_funds, raw_context, criteria, fund_metrics)
    raw = client.generate(prompt, GROUPING_SYSTEM_PROMPT)

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
        raise FundGroupingError(f"LLM returned invalid JSON: {e}") from e

    try:
        result = LLMGroupingResult.model_validate(data)
    except ValidationError as e:
        raise FundGroupingError(f"LLM output failed schema validation: {e}") from e

    logger.info(
        "LLM grouped %d funds into %d groups, %d ambiguities",
        sum(len(g.fund_names) for g in result.groups),
        len(result.groups),
        len(result.ambiguities),
    )

    return result


def validate_grouping(
    result: LLMGroupingResult,
    eligible_fund_names: set[str],
    max_groups: int,
) -> list[str]:
    """Deterministic post-checks on LLM grouping results.

    Returns a list of validation error strings (empty = all good).
    """
    errors: list[str] = []

    # At least 1 group with at least 1 fund
    if not result.groups:
        errors.append("LLM returned zero groups")
        return errors

    non_empty_groups = [g for g in result.groups if g.fund_names]
    if not non_empty_groups:
        errors.append("All groups are empty (no funds assigned)")
        return errors

    # Number of groups <= max_groups
    if len(result.groups) > max_groups:
        errors.append(
            f"LLM returned {len(result.groups)} groups, exceeding max_groups={max_groups}"
        )

    # Every eligible fund appears in at least one group
    assigned_funds: list[str] = []
    for group in result.groups:
        assigned_funds.extend(group.fund_names)

    assigned_set = set(assigned_funds)
    missing = eligible_fund_names - assigned_set
    if missing:
        errors.append(f"Funds missing from grouping: {sorted(missing)}")

    # No fund appears in multiple groups
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in assigned_funds:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    if duplicates:
        errors.append(f"Funds appear in multiple groups: {sorted(duplicates)}")

    return errors
