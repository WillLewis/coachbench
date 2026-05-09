from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from arena.api.deps import error, moderate
from arena.assistant.proposal import ProposalRejected, apply_proposal, validate_proposal
from arena.assistant.templates import propose_from_prompt
from arena.llm.budget import BudgetExceeded, LLMBudget
from arena.storage import drafts


router = APIRouter()


def _db():
    from arena.api.app import db

    return db()


class AssistantProposeRequest(BaseModel):
    prompt: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class AssistantAcceptRequest(BaseModel):
    proposal: dict[str, Any]
    draft_name: str | None = None


def _public_draft(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if isinstance(result.get("config_json"), str):
        result["config_json"] = json.loads(result["config_json"])
    return result


def _load_draft(draft_id: str | None) -> dict[str, Any] | None:
    if not draft_id:
        return None
    row = drafts.get_draft(_db(), draft_id)
    if not row:
        error("not_found", "draft not found", 404)
    return _public_draft(row)


def _load_replay(run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None
    candidates = [Path("data/local_runs") / f"{run_id}.json"]
    if run_id.startswith("seed-"):
        seed = run_id.removeprefix("seed-")
        candidates.extend([
            Path("ui/showcase_replays") / f"seed_{seed}.json",
            Path("ui") / "demo_replay.json",
            Path("data") / "demo_replay.json",
        ])
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def _session_id(request: Request, context: dict[str, Any]) -> str:
    return (
        request.headers.get("x-coachbench-session")
        or str(context.get("session_id") or "assistant-session")
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _server_context(payload: AssistantProposeRequest) -> tuple[dict[str, Any], dict[str, Any] | None]:
    client_context = dict(payload.context or {})
    current_draft = _load_draft(client_context.get("current_draft_id"))
    replay = _load_replay(client_context.get("current_run_id"))
    context: dict[str, Any] = {
        "request_type": client_context.get("request_type"),
        "current_draft_id": client_context.get("current_draft_id"),
        "current_draft": current_draft,
        "current_run_id": client_context.get("current_run_id"),
        "selected_play_index": client_context.get("selected_play_index"),
        "selected_identity_id": client_context.get("selected_identity_id"),
        "user_override": client_context.get("user_override"),
        "replay": replay,
    }
    return context, current_draft


def _context_from_proposal_evidence(proposal: dict[str, Any]) -> dict[str, Any]:
    for ref in proposal.get("evidence_refs", []):
        if ref.get("type") != "film_room_event":
            continue
        ref_id = str(ref.get("id") or "")
        run_id = ref_id.split(":play:", 1)[0] if ":play:" in ref_id else None
        replay = _load_replay(run_id)
        if replay:
            return {"replay": replay}
    return {}


@router.post("/v1/assistant/propose")
def propose(payload: AssistantProposeRequest, request: Request) -> dict:
    context, current_draft = _server_context(payload)
    budget = LLMBudget(_db())
    grant = None
    try:
        grant = budget.acquire(_session_id(request, payload.context), _client_ip(request))
        proposal = propose_from_prompt(
            payload.prompt,
            context,
            session_id=grant.session_id,
            ip=grant.ip,
        )
        validate_proposal(proposal, current_draft=current_draft, context=context)
    except BudgetExceeded as exc:
        error("budget_exceeded", str(exc), 429)
    except ProposalRejected as exc:
        error("proposal_rejected", str(exc), 422)
    finally:
        if grant is not None:
            budget.release(grant, tokens_in=0, tokens_out=0, cost_usd_est=0.0)
    return {"proposal": proposal}


def _draft_name(raw: str | None, proposal: dict[str, Any]) -> str:
    name = (raw or f"assistant-{proposal['target_side']}-draft").strip()
    moderate(name)
    return name


@router.post("/v1/assistant/accept", status_code=201)
def accept(payload: AssistantAcceptRequest) -> dict:
    proposal = payload.proposal
    if proposal.get("intent") == "clarify":
        error("proposal_not_acceptable", "clarify_proposals_cannot_be_accepted", 422)
    current_draft = _load_draft(proposal.get("target_draft_id"))
    try:
        validate_proposal(proposal, current_draft=current_draft, context=_context_from_proposal_evidence(proposal))
        config_json = apply_proposal(proposal, current_draft=current_draft)
        if proposal["intent"] == "tweak":
            row = drafts.update_draft(
                _db(),
                proposal["target_draft_id"],
                config_json=config_json,
                identity_id=proposal.get("target_identity_id"),
            )
            if not row:
                error("not_found", "draft not found", 404)
        else:
            row = drafts.create_draft(
                _db(),
                name=_draft_name(payload.draft_name, proposal),
                side_eligibility=config_json["side"],
                tier=config_json["access_tier"],
                config_json=config_json,
                identity_id=proposal.get("target_identity_id"),
            )
    except ProposalRejected as exc:
        error("proposal_rejected", str(exc), 422)
    except ValueError as exc:
        error("invalid_draft_config", str(exc), 422)
    return {"draft": _public_draft(row)}
