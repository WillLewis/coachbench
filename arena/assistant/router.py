from __future__ import annotations

import json
import logging
import re
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
    "and cite only supplied graph cards, identity facts, or replay events. If this matches a "
    "canonical_prompt_examples entry, return that non-clarify proposal shape."
)
LOGGER = logging.getLogger("coachbench.llm")
CANONICAL_PROMPTS = {
    "build an offense that punishes pressure without throwing picks.",
    "make my defense disguise more without burning the rush budget.",
    "we got baited by simulated pressure. what should i change?",
    "build a run-first coordinator that unlocks play-action.",
    "give me a safe red-zone defense that prevents explosives.",
}


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


def _is_provider_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    return (
        hasattr(exc, "status_code")
        or "api" in name
        or "http" in name
        or "connection" in name
        or "badrequest" in name
        or "rate" in name
    )


def _clean_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.split(RETRY_REMINDER, 1)[0].lower()).strip()


def _requires_non_clarify(prompt: str) -> bool:
    return _clean_prompt(prompt) in CANONICAL_PROMPTS


def _enforce_launch_semantics(prompt: str, proposal: dict[str, Any]) -> None:
    if _requires_non_clarify(prompt) and proposal.get("intent") == "clarify":
        raise ProposalRejected("canonical launch prompt returned clarify")


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
    _enforce_launch_semantics(prompt, proposal)
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
        except Exception as retry_exc:
            if not _is_provider_error(retry_exc):
                raise
            proposal, usage = _stub(prompt, context, session_id=session_id, ip=ip)
            _log("retry_failed_stub", reason=retry_exc.__class__.__name__)
            return proposal, usage
    except Exception as exc:
        if not _is_provider_error(exc):
            raise
        proposal, usage = _stub(prompt, context, session_id=session_id, ip=ip)
        _log("error_stub", reason=exc.__class__.__name__)
        return proposal, usage
