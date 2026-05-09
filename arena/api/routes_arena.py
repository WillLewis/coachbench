from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from arena.api.deps import error
from arena.runs.arena import total_runs_for
from arena.storage import arena_jobs, drafts, sessions
from arena.worker.queue import enqueue, get_job


router = APIRouter()


def _db():
    from arena.api.app import db

    return db()


class BestOfNRequest(BaseModel):
    offense_draft_id: str
    defense_draft_id: str
    n: int
    seed_pack: list[int]
    max_plays: int = 8


class GauntletRequest(BaseModel):
    draft_id: str
    draft_side: str
    opponent_pool: list[str]
    seed_pack: list[int]
    max_plays: int = 8


class TournamentRequest(BaseModel):
    participant_draft_ids: list[str]
    side_assignments: dict[str, str]
    seed_pack: list[int]
    format: str = "round_robin"
    max_plays: int = 8


def _require_drafts(ids: list[str]) -> None:
    conn = _db()
    missing = [draft_id for draft_id in ids if not drafts.get_draft(conn, draft_id)]
    if missing:
        error("not_found", f"drafts not found: {missing}", 404)


def _enqueue_arena(kind: str, payload: dict[str, Any]) -> dict:
    conn = _db()
    total = total_runs_for(kind, payload)
    if total <= 0:
        error("invalid_arena_job", "arena job must include at least one run", 422)
    job_id = enqueue(conn, kind, payload)
    arena_jobs.create_progress(conn, job_id, total)
    return {"job_id": job_id}


def _public_session(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["replay_paths"] = json.loads(row["replay_paths_json"])
    del result["replay_paths_json"]
    return result


@router.post("/v1/arena/best_of_n", status_code=202)
def create_best_of_n(payload: BestOfNRequest) -> dict:
    _require_drafts([payload.offense_draft_id, payload.defense_draft_id])
    if payload.n <= 0 or len(payload.seed_pack) < payload.n:
        error("invalid_best_of_n", "seed_pack must contain at least n seeds", 422)
    return _enqueue_arena("arena_best_of_n", payload.model_dump())


@router.post("/v1/arena/gauntlet", status_code=202)
def create_gauntlet(payload: GauntletRequest) -> dict:
    if payload.draft_side not in {"offense", "defense"}:
        error("invalid_gauntlet", "draft_side must be offense or defense", 422)
    _require_drafts([payload.draft_id, *payload.opponent_pool])
    return _enqueue_arena("arena_gauntlet", payload.model_dump())


@router.post("/v1/arena/tournament", status_code=202)
def create_tournament(payload: TournamentRequest) -> dict:
    if payload.format != "round_robin":
        error("invalid_tournament", "only round_robin format is supported", 422)
    _require_drafts(payload.participant_draft_ids)
    unknown = set(payload.side_assignments) - set(payload.participant_draft_ids)
    bad_sides = {side for side in payload.side_assignments.values() if side not in {"offense", "defense"}}
    if unknown or bad_sides:
        error("invalid_tournament", "side_assignments must map participants to offense or defense", 422)
    return _enqueue_arena("arena_tournament", payload.model_dump())


@router.get("/v1/arena/jobs/{job_id}")
def arena_job_status(job_id: str) -> dict:
    conn = _db()
    job = get_job(conn, job_id)
    if not job:
        error("not_found", "arena job not found", 404)
    progress = arena_jobs.get_progress(conn, job_id) or arena_jobs.create_progress(conn, job_id, 0)
    return {
        "job_id": job["job_id"],
        "kind": job["kind"],
        "status": job["status"],
        "completed_runs": progress["completed_runs"],
        "total_runs": progress["total_runs"],
        "failed_runs": progress["failed_runs"],
        "report_path": progress["report_path"],
        "last_error": job["last_error"],
    }


@router.get("/v1/arena/jobs/{job_id}/report")
def arena_job_report(job_id: str) -> dict:
    progress = arena_jobs.get_progress(_db(), job_id)
    if not progress or not progress["report_path"]:
        error("not_found", "arena report not found", 404)
    path = Path(progress["report_path"])
    if not path.exists():
        error("not_found", "arena report file not found", 404)
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/v1/arena/sessions")
def arena_sessions(limit: int = 20) -> dict:
    return {"sessions": [_public_session(row) for row in sessions.list_sessions(_db(), limit=limit)]}
