from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Header
from pydantic import BaseModel

from arena.api.deps import ADMIN_TOKEN, ROOT, error
from arena.storage.registry import get_submission
from arena.tiers import ADMIN_ONLY_TIERS
from arena.tiers.league import is_eligible
from arena.worker.queue import enqueue


router = APIRouter()


class ChallengeRequest(BaseModel):
    challenger_agent_id: str
    opponent_kind: str = "static"
    seeds: list[int]
    league: str = "rookie"


def _db():
    from arena.api.app import db
    return db()


@router.post("/v1/challenges", status_code=202)
def create_challenge(payload: ChallengeRequest, x_admin_token: str | None = Header(default=None)) -> dict:
    row = get_submission(_db(), payload.challenger_agent_id)
    if not row:
        error("not_found", "agent not found", 404)
    if row["qualification_status"] != "passed":
        error("not_qualified", "agent must pass qualification before challenges", 422)
    tier = row["access_tier"]
    league = payload.league
    if tier in ADMIN_ONLY_TIERS and x_admin_token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)
    if tier in ADMIN_ONLY_TIERS and x_admin_token == ADMIN_TOKEN and league == "rookie":
        league = "sandbox"
    if not is_eligible(league, tier):
        error("ineligible_league", "agent tier is not eligible for this league", 422)
    challenge_id = secrets.token_hex(8)
    job_id = enqueue(
        _db(),
        "challenge",
        {
            "challenge_id": challenge_id,
            "agent_id": payload.challenger_agent_id,
            "opponent_kind": payload.opponent_kind,
            "seeds": payload.seeds,
            "league": league,
            "access_tier": tier,
        },
    )
    return {"challenge_id": challenge_id, "status": "pending", "job_id": job_id}


@router.get("/v1/challenges/{challenge_id}")
def get_challenge(challenge_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    path = ROOT / "challenges" / challenge_id / "report.json"
    if not path.exists():
        if x_admin_token != ADMIN_TOKEN:
            error("forbidden", "admin token required", 403)
        return {"challenge_id": challenge_id, "status": "pending"}
    import json
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("access_tier") == "sandboxed_code" and x_admin_token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)
    return report
