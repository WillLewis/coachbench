from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from arena.api.deps import ADMIN_TOKEN, ROOT, error, require_admin_token
from arena.storage.leaderboard import create_season, public_leaderboard as public_leaderboard_snapshot
from arena.worker.queue import enqueue


router = APIRouter()


class SeasonRequest(BaseModel):
    label: str
    seeds: list[int]
    max_plays: int
    opponent_kind: str
    league: str = "sandbox"


def _db():
    from arena.api.app import db
    return db()


@router.post("/v1/admin/seasons", status_code=201)
def admin_create_season(payload: SeasonRequest, _: None = Depends(require_admin_token)) -> dict:
    if payload.league not in {"rookie", "policy", "endpoint", "sandbox", "research"}:
        error("invalid_league", "unknown leaderboard league", 422)
    season_id = create_season(
        _db(),
        payload.label,
        payload.seeds,
        payload.max_plays,
        payload.opponent_kind,
        ROOT / "secrets" / "seasons",
        payload.league,
    )
    season = public_leaderboard_snapshot(_db(), season_id, is_admin=True)
    return {"season_id": season_id, "seed_set_hash": season["seed_set_hash"], "league": payload.league}


@router.post("/v1/admin/seasons/{season_id}/run", status_code=202)
def admin_run_season(season_id: str, _: None = Depends(require_admin_token)) -> dict:
    job_id = enqueue(_db(), "leaderboard_run", {"season_id": season_id})
    return {"season_id": season_id, "status": "pending", "job_id": job_id}


@router.get("/v1/seasons/{season_id}/leaderboard")
def public_leaderboard(season_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    return public_leaderboard_snapshot(_db(), season_id, is_admin=x_admin_token == ADMIN_TOKEN)


@router.get("/v1/seasons/{season_id}/runs/{agent_id}")
def public_runs(season_id: str, agent_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        return {"season_id": season_id, "agent_id": agent_id, "runs": []}
    rows = _db().execute(
        "SELECT seed_hash, points, result, plays, access_tier FROM leaderboard_runs WHERE season_id=? AND agent_id=?",
        (season_id, agent_id),
    ).fetchall()
    return {"season_id": season_id, "agent_id": agent_id, "runs": [dict(row) for row in rows]}
