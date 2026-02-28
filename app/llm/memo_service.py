"""Memo generation orchestrator."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.core.evidence.fact_pack import MEMO_SYSTEM_PROMPT, build_memo_prompt
from app.core.exceptions import MemoGenerationError
from app.core.schemas import Claim, FactPack, MemoOutput, MetricId
from app.llm.anthropic_client import AnthropicClient

logger = logging.getLogger("equi.llm.memo")


def generate_memo(client: AnthropicClient, fact_pack: FactPack) -> MemoOutput:
    """Generate IC memo from fact pack. Fail closed on invalid output."""
    prompt = build_memo_prompt(fact_pack)
    raw = client.generate(prompt, MEMO_SYSTEM_PROMPT)

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
        raise MemoGenerationError(f"LLM returned invalid JSON: {e}") from e

    try:
        memo = MemoOutput.model_validate(data)
    except ValidationError as e:
        raise MemoGenerationError(f"LLM output failed schema validation: {e}") from e

    # Validate claims
    errors = validate_claims(memo, fact_pack)
    if errors:
        logger.warning("Claim validation warnings: %s", errors)

    return memo


def validate_claims(memo: MemoOutput, fact_pack: FactPack) -> list[str]:
    """Check that all claims reference valid metric IDs and fund names."""
    valid_metric_ids = {m.value for m in MetricId}
    valid_fund_names = {sf.fund_name for sf in fact_pack.shortlist}

    errors: list[str] = []
    for claim in memo.claims:
        for mid in claim.referenced_metric_ids:
            if mid.value not in valid_metric_ids:
                errors.append(
                    f"Claim '{claim.claim_id}' references unknown metric: {mid}"
                )
        for fname in claim.referenced_fund_names:
            if fname not in valid_fund_names:
                errors.append(
                    f"Claim '{claim.claim_id}' references unknown fund: {fname}"
                )

    return errors
