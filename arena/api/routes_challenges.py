from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from arena.api.deps import ROOT, error, require_admin_token
from arena.storage.registry import get_submission
from arena.worker.queue import enqueue


router = APIRouter()


class ChallengeRequest(BaseModel):
    challenger_agent_id: str
    opponent_kind: str = "static"
    seeds: list[int]


def _db():
    from arena.api.app import db
    return db()


@router.post("/v1/challenges", status_code=202)
def create_challenge(payload: ChallengeRequest, _: None = Depends(require_admin_token)) -> dict:
    row = get_submission(_db(), payload.challenger_agent_id)
    if not row:
        error("not_found", "agent not found", 404)
    if row["qualification_status"] != "passed":
        error("not_qualified", "agent must pass qualification before challenges", 422)
    challenge_id = secrets.token_hex(8)
    job_id = enqueue(
        _db(),
        "challenge",
        {"challenge_id": challenge_id, "agent_id": payload.challenger_agent_id, "opponent_kind": payload.opponent_kind, "seeds": payload.seeds},
    )
    return {"challenge_id": challenge_id, "status": "pending", "job_id": job_id}


@router.get("/v1/challenges/{challenge_id}")
def get_challenge(challenge_id: str, _: None = Depends(require_admin_token)) -> dict:
    path = ROOT / "challenges" / challenge_id / "report.json"
    if not path.exists():
        return {"challenge_id": challenge_id, "status": "pending"}
    import json
    return json.loads(path.read_text(encoding="utf-8"))
