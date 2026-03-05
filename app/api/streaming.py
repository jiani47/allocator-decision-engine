"""SSE streaming utilities for memo generation."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Generator

from app.api.schemas import MemoStreamRequest
from app.config import Settings
from app.core.evidence.fact_pack import build_fact_pack
from app.core.schemas import MemoOutput
from app.llm.anthropic_client import AnthropicClient
from app.llm.memo_service import generate_memo_streaming
from app.services import build_group_universe

logger = logging.getLogger("equi.api.streaming")


def memo_stream_sse(
    request: MemoStreamRequest,
    settings: Settings,
) -> Generator[str, None, None]:
    """Real SSE streaming: yields text deltas as they arrive from the LLM.

    Event format: `data: {"event": "<type>", ...}\n\n`
    """
    yield _sse_event("progress", {"message": "Building fact pack..."})

    group_run = request.group_run
    mandate = request.mandate
    effective_shortlist = group_run.ranked_shortlist[: mandate.shortlist_top_k]

    # If AI ranking is adopted, reorder shortlist by LLM ranks
    ai_rationales = []
    if request.use_ai_ranking and group_run.llm_rerank:
        llm_rank_lookup = {
            rr.fund_name: rr.llm_rank
            for rr in group_run.llm_rerank.reranked_funds
        }
        # Sort by LLM rank and overwrite the rank field
        effective_shortlist = sorted(
            effective_shortlist,
            key=lambda sf: llm_rank_lookup.get(sf.fund_name, sf.rank),
        )
        effective_shortlist = [
            sf.model_copy(update={"rank": llm_rank_lookup.get(sf.fund_name, sf.rank)})
            for sf in effective_shortlist
        ]
        # Include rationales for funds in the effective shortlist
        shortlist_names = {sf.fund_name for sf in effective_shortlist}
        ai_rationales = [
            rr for rr in group_run.llm_rerank.reranked_funds
            if rr.fund_name in shortlist_names
        ]

    group_universe = build_group_universe(request.universe, group_run.group)

    run_id = str(uuid.uuid4())
    fact_pack = build_fact_pack(
        run_id,
        effective_shortlist,
        group_universe,
        mandate,
        group_run.group.benchmark_symbol or "None",
        analyst_notes=request.warning_resolutions or None,
        group_name=group_run.group.group_name,
        group_rationale=group_run.group.grouping_rationale,
        ai_rationales=ai_rationales,
    )

    yield _sse_event("progress", {"message": "Generating memo..."})

    client = AnthropicClient(settings)

    try:
        for event_type, payload in generate_memo_streaming(client, fact_pack):
            if event_type == "text_delta":
                yield _sse_event("text_delta", {"text": payload})
            elif event_type == "memo_text_complete":
                yield _sse_event("progress", {"message": "Extracting claims..."})
            elif event_type == "complete":
                memo: MemoOutput = payload  # type: ignore[assignment]
                group_run.memo = memo
                group_run.fact_pack = fact_pack
                yield _sse_event(
                    "complete",
                    {"group_run": group_run.model_dump(mode="json")},
                )
            elif event_type == "error":
                yield _sse_event("error", {"message": str(payload)})
    except Exception as e:
        logger.exception("Memo stream error")
        yield _sse_event("error", {"message": str(e)})


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event."""
    payload = {"event": event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"
