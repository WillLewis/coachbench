from __future__ import annotations

import json
import logging
import time
from typing import Any

from arena.llm.client import (
    LLMHttpError,
    LLMSchemaInvalid,
    LLMTimeout,
    LLMUnavailable,
    call_llm_real,
    configured_model,
)
from arena.llm.context import pack_context
from arena.llm.usage import LLMUsage, ZERO_USAGE
from arena.storage import llm_budget as budget_storage

from .proposal import ProposalRejected, validate_proposal
from .templates import propose_from_prompt


RETRY_REMINDER = (
    "\n\nReturn JSON only. The object must match task_schema exactly, use only legal_parameters, "
    "and cite only supplied graph cards, identity facts, or replay events."
)
LOGGER = logging.getLogger("coachbench.llm")


def _log(path: str, *, tokens_in: int = 0, tokens_out: int = 0, latency_ms: int = 0, reason: str | None = None) -> None:
    payload = {
        "path": path,
        "model": configured_model(),
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "latency_ms": int(latency_ms),
    }
    if reason:
        payload["reason"] = reason
    LOGGER.info("assistant_llm_route %s", json.dumps(payload, sort_keys=True))


def _stub(prompt: str, context: dict[str, Any], *, session_id: str, ip: str) -> tuple[dict[str, Any], LLMUsage]:
    return propose_from_prompt(prompt, context, session_id=session_id, ip=ip), ZERO_USAGE


def _budget_state(budget, session_id: str) -> dict[str, Any]:
    conn = getattr(budget, "conn", None)
    calls = budget_storage.count_session_calls(conn, session_id) if conn is not None else 0
    max_calls = getattr(budget, "max_calls_per_session", 0)
    return {
        "remaining_calls_in_session": max(0, int(max_calls) - int(calls)),
        "kill_switch": budget.is_killed(),
    }


def _normalize_film_room_evidence(proposal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    run_id = context.get("current_run_id")
    if not run_id:
        return proposal
    for ref in proposal.get("evidence_refs", []):
        if ref.get("type") == "film_room_event" and str(ref.get("id", "")).startswith("play:"):
            ref["id"] = f"{run_id}:{ref['id']}"
    return proposal


def _real_once(
    prompt: str,
    context: dict[str, Any],
    *,
    session_id: str,
    ip: str,
    budget,
    current_draft: dict[str, Any] | None,
) -> tuple[dict[str, Any], LLMUsage, int]:
    started = time.monotonic()
    packed = pack_context(prompt=prompt, server_context=context, budget_state=_budget_state(budget, session_id))
    proposal, usage = call_llm_real(prompt, packed, session_id=session_id, ip=ip)
    proposal = _normalize_film_room_evidence(proposal, context)
    validate_proposal(proposal, current_draft=current_draft, context=context)
    latency_ms = int((time.monotonic() - started) * 1000)
    return proposal, usage, latency_ms


def select_proposer(
    prompt: str,
    context: dict[str, Any],
    *,
    session_id: str,
    ip: str,
    budget,
    current_draft: dict[str, Any] | None,
) -> tuple[dict[str, Any], LLMUsage]:
    if budget.is_killed():
        proposal, usage = _stub(prompt, context, session_id=session_id, ip=ip)
        _log("killed_stub")
        return proposal, usage

    try:
        proposal, usage, latency_ms = _real_once(
            prompt,
            context,
            session_id=session_id,
            ip=ip,
            budget=budget,
            current_draft=current_draft,
        )
        _log("real", tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, latency_ms=latency_ms)
        return proposal, usage
    except (LLMUnavailable, LLMTimeout, LLMHttpError) as exc:
        proposal, usage = _stub(prompt, context, session_id=session_id, ip=ip)
        _log("error_stub", reason=exc.__class__.__name__)
        return proposal, usage
    except (LLMSchemaInvalid, ProposalRejected) as exc:
        first_reason = exc.__class__.__name__
        try:
            proposal, usage, latency_ms = _real_once(
                prompt + RETRY_REMINDER,
                context,
                session_id=session_id,
                ip=ip,
                budget=budget,
                current_draft=current_draft,
            )
            _log("retry_real", tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, latency_ms=latency_ms, reason=first_reason)
            return proposal, usage
        except (LLMUnavailable, LLMTimeout, LLMHttpError, LLMSchemaInvalid, ProposalRejected) as retry_exc:
            proposal, usage = _stub(prompt, context, session_id=session_id, ip=ip)
            _log("retry_failed_stub", reason=retry_exc.__class__.__name__)
            return proposal, usage
