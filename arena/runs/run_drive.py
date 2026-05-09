from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from arena.api.deps import ROOT
from arena.storage.registry import connect
from arena.storage import drafts, sessions
from arena.tiers.factory import tiered_agent_from_submission
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine


@dataclass(frozen=True)
class RunResult:
    run_id: str
    replay_path: str
    replay_url: str
    summary: dict[str, Any]


def _load_conn():
    from arena.api.app import db

    return db()


def _resolve_conn(conn: sqlite3.Connection | None = None, db_path: Path | str | None = None) -> sqlite3.Connection:
    if conn is not None:
        return conn
    if db_path is not None:
        return connect(db_path)
    return _load_conn()


def _config_payload(draft: dict[str, Any]) -> dict[str, Any]:
    return json.loads(draft["config_json"])


def _ensure_slot_compatible(draft: dict[str, Any], slot: str) -> None:
    payload = _config_payload(draft)
    if payload.get("side") != slot:
        raise ValueError(f"{slot}_draft_id must reference a {slot} config")
    if draft["side_eligibility"] not in {slot, "either"}:
        raise ValueError(f"{slot}_draft_id is not eligible for {slot}")


def _materialize_submission_row(draft: dict[str, Any], root: Path) -> dict[str, Any]:
    config_dir = root / "draft_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{draft['id']}_v{draft['version']}.json"
    config_path.write_text(json.dumps(_config_payload(draft), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload = _config_payload(draft)
    return {
        "agent_id": draft["id"],
        "label": draft["name"],
        "side": payload["side"],
        "access_tier": draft["tier"],
        "tier_config_path": str(config_path),
        "endpoint_url_hash": None,
    }


def run_drive_from_drafts(
    offense_draft_id: str,
    defense_draft_id: str,
    seed: int,
    max_plays: int = 8,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str | None = None,
    run_id: str | None = None,
) -> RunResult:
    conn = _resolve_conn(conn, db_path)
    offense_draft = drafts.get_draft(conn, offense_draft_id)
    defense_draft = drafts.get_draft(conn, defense_draft_id)
    if not offense_draft:
        raise ValueError("offense draft not found")
    if not defense_draft:
        raise ValueError("defense draft not found")
    _ensure_slot_compatible(offense_draft, "offense")
    _ensure_slot_compatible(defense_draft, "defense")

    session = sessions.create_session(
        conn,
        offense_draft_id=offense_draft_id,
        defense_draft_id=defense_draft_id,
        opponent_label=defense_draft["name"],
        seed=int(seed),
        status="running",
        session_id=run_id,
    )
    run_id = session["id"]
    try:
        offense_agent = tiered_agent_from_submission(_materialize_submission_row(offense_draft, ROOT))
        defense_agent = tiered_agent_from_submission(_materialize_submission_row(defense_draft, ROOT))
        replay = CoachBenchEngine(seed=int(seed)).run_drive(
            offense_agent,
            defense_agent,
            max_plays=int(max_plays),
            agent_garage_config={
                "drafts": {
                    "offense": {
                        "id": offense_draft["id"],
                        "name": offense_draft["name"],
                        "version": offense_draft["version"],
                        "tier": offense_draft["tier"],
                    },
                    "defense": {
                        "id": defense_draft["id"],
                        "name": defense_draft["name"],
                        "version": defense_draft["version"],
                        "tier": defense_draft["tier"],
                    },
                }
            },
        )
        validate_replay_contract(replay)
        out_dir = Path("data/local_runs")
        out_dir.mkdir(parents=True, exist_ok=True)
        replay_path = out_dir / f"{run_id}.json"
        replay_path.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
        sessions.attach_replays(conn, run_id, [str(replay_path)])
        sessions.update_session_status(conn, run_id, "completed")
        summary = {
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "offense": replay["agents"]["offense"],
            "defense": replay["agents"]["defense"],
        }
        return RunResult(
            run_id=run_id,
            replay_path=str(replay_path),
            replay_url=f"/v1/runs/{run_id}/replay",
            summary=summary,
        )
    except Exception:
        sessions.update_session_status(conn, run_id, "failed")
        raise
