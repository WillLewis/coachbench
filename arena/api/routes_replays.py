from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from arena.api.deps import error


router = APIRouter()


def _replay_path(run_id: str) -> Path:
    return Path("data/local_runs") / f"{run_id}.json"


def _load_replay(run_id: str) -> dict:
    path = _replay_path(run_id)
    if not path.exists():
        error("not_found", "replay not found", 404)
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/v1/replays/{run_id}")
def get_replay(run_id: str) -> JSONResponse:
    return JSONResponse(_load_replay(run_id))


@router.get("/v1/replays/{run_id}/film_room")
def get_replay_film_room(run_id: str) -> dict:
    replay = _load_replay(run_id)
    return {
        "run_id": run_id,
        "film_room": replay.get("film_room", {}),
        "film_room_tweaks": replay.get("film_room_tweaks", []),
    }
