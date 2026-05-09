from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from arena.api.deps import error
from arena.runs.run_drive import run_drive_from_drafts
from arena.storage import sessions


router = APIRouter()


def _db():
    from arena.api.app import db

    return db()


class DriveRunRequest(BaseModel):
    offense_draft_id: str
    defense_draft_id: str
    seed: int
    max_plays: int = 8


def _public_session(row: dict) -> dict:
    result = dict(row)
    result["replay_paths"] = json.loads(row["replay_paths_json"])
    del result["replay_paths_json"]
    return result


@router.post("/v1/runs/drive", status_code=201)
def run_drive(payload: DriveRunRequest) -> dict:
    try:
        result = run_drive_from_drafts(
            payload.offense_draft_id,
            payload.defense_draft_id,
            payload.seed,
            payload.max_plays,
        )
    except ValueError as exc:
        error("invalid_run_request", str(exc), 422)
    return {
        "run_id": result.run_id,
        "replay_url": result.replay_url,
        "summary": result.summary,
    }


@router.get("/v1/runs/{run_id}/replay")
def get_run_replay(run_id: str) -> JSONResponse:
    path = Path("data/local_runs") / f"{run_id}.json"
    if not path.exists():
        error("not_found", "run replay not found", 404)
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@router.get("/v1/sessions")
def list_run_sessions(limit: int = 20) -> dict:
    return {"sessions": [_public_session(row) for row in sessions.list_sessions(_db(), limit=limit)]}
