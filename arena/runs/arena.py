from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from arena.api.deps import ROOT
from arena.runs.report import build_report, failed_match, match_from_replay, write_report
from arena.runs.run_drive import run_drive_from_drafts
from arena.storage import arena_jobs, drafts


def _report_path(job_id: str) -> Path:
    return ROOT / "arena_reports" / f"{job_id}.json"


def _load_replay(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _draft_label(conn: sqlite3.Connection, draft_id: str) -> str:
    row = drafts.get_draft(conn, draft_id)
    return row["name"] if row else draft_id


def _safe_run_match(
    *,
    conn: sqlite3.Connection,
    job_id: str,
    match_index: int,
    offense_draft_id: str,
    defense_draft_id: str,
    seed: int,
    max_plays: int,
) -> tuple[dict[str, Any], bool]:
    match_id = f"{job_id}-{match_index:04d}"
    run_id = f"{match_id}-run"
    try:
        result = run_drive_from_drafts(
            offense_draft_id,
            defense_draft_id,
            int(seed),
            int(max_plays),
            conn=conn,
            run_id=run_id,
        )
        replay = _load_replay(result.replay_path)
        return (
            match_from_replay(
                match_id=match_id,
                replay=replay,
                seed=int(seed),
                replay_url=f"/v1/replays/{run_id}",
                film_room_url=f"/v1/replays/{run_id}/film_room",
            ),
            False,
        )
    except Exception as exc:
        return (
            failed_match(
                match_id=match_id,
                offense_label=_draft_label(conn, offense_draft_id),
                defense_label=_draft_label(conn, defense_draft_id),
                seed=int(seed),
                error=str(exc),
            ),
            True,
        )


def best_of_n_total(payload: dict[str, Any]) -> int:
    return int(payload.get("n") or len(payload.get("seed_pack", [])))


def gauntlet_total(payload: dict[str, Any]) -> int:
    return len(payload.get("opponent_pool", [])) * len(payload.get("seed_pack", []))


def tournament_total(payload: dict[str, Any]) -> int:
    assignments = dict(payload.get("side_assignments", {}))
    offense = [draft_id for draft_id in payload.get("participant_draft_ids", []) if assignments.get(draft_id) == "offense"]
    defense = [draft_id for draft_id in payload.get("participant_draft_ids", []) if assignments.get(draft_id) == "defense"]
    return len(offense) * len(defense) * len(payload.get("seed_pack", []))


def total_runs_for(kind: str, payload: dict[str, Any]) -> int:
    if kind == "arena_best_of_n":
        return best_of_n_total(payload)
    if kind == "arena_gauntlet":
        return gauntlet_total(payload)
    if kind == "arena_tournament":
        return tournament_total(payload)
    raise ValueError(f"unsupported arena job kind: {kind}")


def _finalize(conn: sqlite3.Connection, job_id: str, kind: str, payload: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    public_kind = kind.removeprefix("arena_")
    report = build_report(job_id, public_kind, payload, matches)
    path = _report_path(job_id)
    write_report(path, report)
    arena_jobs.attach_report(conn, job_id, str(path))
    return report


def run_best_of_n_job(conn: sqlite3.Connection, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    seeds = list(payload.get("seed_pack", []))
    n = int(payload.get("n") or len(seeds))
    if len(seeds) < n:
        raise ValueError("seed_pack must contain at least n seeds")
    max_plays = int(payload.get("max_plays", 8))
    arena_jobs.create_progress(conn, job_id, n)
    matches = []
    for index, seed in enumerate(seeds[:n], start=1):
        match, failed = _safe_run_match(
            conn=conn,
            job_id=job_id,
            match_index=index,
            offense_draft_id=payload["offense_draft_id"],
            defense_draft_id=payload["defense_draft_id"],
            seed=int(seed),
            max_plays=max_plays,
        )
        matches.append(match)
        arena_jobs.increment_progress(conn, job_id, failed=failed)
    return _finalize(conn, job_id, "arena_best_of_n", payload, matches)


def run_gauntlet_job(conn: sqlite3.Connection, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    seeds = list(payload.get("seed_pack", []))
    opponents = list(payload.get("opponent_pool", []))
    draft_side = payload.get("draft_side")
    max_plays = int(payload.get("max_plays", 8))
    if draft_side not in {"offense", "defense"}:
        raise ValueError("draft_side must be offense or defense")
    arena_jobs.create_progress(conn, job_id, len(opponents) * len(seeds))
    matches = []
    match_index = 0
    for opponent_id in opponents:
        for seed in seeds:
            match_index += 1
            offense_id = payload["draft_id"] if draft_side == "offense" else opponent_id
            defense_id = opponent_id if draft_side == "offense" else payload["draft_id"]
            match, failed = _safe_run_match(
                conn=conn,
                job_id=job_id,
                match_index=match_index,
                offense_draft_id=offense_id,
                defense_draft_id=defense_id,
                seed=int(seed),
                max_plays=max_plays,
            )
            matches.append(match)
            arena_jobs.increment_progress(conn, job_id, failed=failed)
    return _finalize(conn, job_id, "arena_gauntlet", payload, matches)


def run_tournament_job(conn: sqlite3.Connection, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("format", "round_robin") != "round_robin":
        raise ValueError("only round_robin tournament format is supported")
    seeds = list(payload.get("seed_pack", []))
    assignments = dict(payload.get("side_assignments", {}))
    participants = list(payload.get("participant_draft_ids", []))
    offense = [draft_id for draft_id in participants if assignments.get(draft_id) == "offense"]
    defense = [draft_id for draft_id in participants if assignments.get(draft_id) == "defense"]
    max_plays = int(payload.get("max_plays", 8))
    arena_jobs.create_progress(conn, job_id, len(offense) * len(defense) * len(seeds))
    matches = []
    match_index = 0
    for offense_id in offense:
        for defense_id in defense:
            for seed in seeds:
                match_index += 1
                match, failed = _safe_run_match(
                    conn=conn,
                    job_id=job_id,
                    match_index=match_index,
                    offense_draft_id=offense_id,
                    defense_draft_id=defense_id,
                    seed=int(seed),
                    max_plays=max_plays,
                )
                matches.append(match)
                arena_jobs.increment_progress(conn, job_id, failed=failed)
    return _finalize(conn, job_id, "arena_tournament", payload, matches)


def run_arena_job(conn: sqlite3.Connection, job_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "arena_best_of_n":
        return run_best_of_n_job(conn, job_id, payload)
    if kind == "arena_gauntlet":
        return run_gauntlet_job(conn, job_id, payload)
    if kind == "arena_tournament":
        return run_tournament_job(conn, job_id, payload)
    raise ValueError(f"unsupported arena job kind: {kind}")
