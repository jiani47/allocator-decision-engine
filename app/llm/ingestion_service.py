"""LLM-based fund extraction from raw file context."""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from app.core.exceptions import LLMIngestionError
from app.core.schemas import LLMExtractedFund, LLMIngestionResult, RawFileContext
from app.llm.anthropic_client import AnthropicClient

logger = logging.getLogger("equi.llm.ingestion")

INGESTION_SYSTEM_PROMPT = """\
You are a data engineer specializing in alternative investment fund data.
Your task is to extract structured fund performance data from raw spreadsheet rows.

Rules:
- Extract each fund as a separate object with its monthly return time series.
- Dates MUST be in YYYY-MM format (e.g., "2022-01" not "2022-01-01").
- Returns MUST be decimal values (e.g., 0.012 for 1.2%, -0.008 for -0.8%).
  If the source data uses percentages (e.g., "1.2%"), convert to decimals.
- Include source_row_indices for every fund so results are traceable.
- If a column is not present for optional fields (strategy, liquidity_days,
  management_fee, performance_fee), set them to null.
- Do NOT invent data. Only extract what is present in the raw rows.
- If anything is ambiguous, note it in the ambiguities list.

Respond with valid JSON matching this schema:
{
  "funds": [
    {
      "fund_name": "string",
      "strategy": "string or null",
      "liquidity_days": "integer or null",
      "management_fee": "float or null",
      "performance_fee": "float or null",
      "monthly_returns": {"YYYY-MM": float, ...},
      "source_row_indices": [int, ...]
    }
  ],
  "interpretation_notes": "string describing how you interpreted the data",
  "ambiguities": ["string", ...]
}
"""


def build_ingestion_prompt(raw_context: RawFileContext) -> str:
    """Build the user prompt from raw file context."""
    lines = [
        f"File: {raw_context.filename}",
        f"Total rows: {raw_context.total_rows}",
        "",
        f"Headers (row {raw_context.header_row_index}): {json.dumps(raw_context.headers)}",
        "",
        f"Data rows ({len(raw_context.data_rows)} rows):",
    ]

    for row in raw_context.data_rows:
        lines.append(f"  Row {row.row_index}: {json.dumps(row.cells)}")

    if raw_context.aggregated_rows:
        lines.append("")
        lines.append(f"Aggregated/summary rows ({len(raw_context.aggregated_rows)} rows, SKIP these):")
        for row in raw_context.aggregated_rows:
            lines.append(f"  Row {row.row_index}: {json.dumps(row.cells)}")

    lines.append("")
    lines.append(
        "Extract all funds with their monthly return time series from the data rows above. "
        "Convert any percentage values to decimals and dates to YYYY-MM format."
    )

    return "\n".join(lines)


def extract_funds_via_llm(
    client: AnthropicClient,
    raw_context: RawFileContext,
) -> LLMIngestionResult:
    """Extract fund data from raw file context using LLM.

    Follows the same pattern as memo_service.generate_memo():
    prompt -> LLM -> strip fences -> JSON parse -> Pydantic validate -> fail closed.
    """
    prompt = build_ingestion_prompt(raw_context)
    raw = client.generate(prompt, INGESTION_SYSTEM_PROMPT)

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
        raise LLMIngestionError(f"LLM returned invalid JSON: {e}") from e

    try:
        result = LLMIngestionResult.model_validate(data)
    except ValidationError as e:
        raise LLMIngestionError(f"LLM output failed schema validation: {e}") from e

    logger.info(
        "LLM extracted %d funds, %d ambiguities",
        len(result.funds),
        len(result.ambiguities),
    )

    return result


def validate_llm_extraction(result: LLMIngestionResult) -> list[str]:
    """Deterministic post-checks on LLM extraction results.

    Returns a list of validation error strings (empty = all good).
    """
    errors: list[str] = []

    if not result.funds:
        errors.append("LLM extracted zero funds")
        return errors

    # Check for duplicate fund names
    names = [f.fund_name for f in result.funds]
    seen: set[str] = set()
    for name in names:
        if name in seen:
            errors.append(f"Duplicate fund name: {name}")
        seen.add(name)

    date_pattern = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

    for fund in result.funds:
        # Check minimum months
        if len(fund.monthly_returns) < 2:
            errors.append(
                f"Fund '{fund.fund_name}' has fewer than 2 months of data "
                f"({len(fund.monthly_returns)} months)"
            )

        for date_key, ret_val in fund.monthly_returns.items():
            # Validate date format
            if not date_pattern.match(date_key):
                errors.append(
                    f"Fund '{fund.fund_name}': invalid date format '{date_key}' "
                    f"(expected YYYY-MM)"
                )

            # Validate return is in reasonable decimal range
            # Monthly returns > 100% or < -100% are almost certainly errors
            if abs(ret_val) > 1.0:
                errors.append(
                    f"Fund '{fund.fund_name}': return {ret_val} for {date_key} "
                    f"looks like a percentage, not a decimal (|value| > 1.0)"
                )

    return errors
