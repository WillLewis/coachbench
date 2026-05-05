from __future__ import annotations

import json
from pathlib import Path
import hashlib

from arena.storage.registry import connect
from arena.storage.registry import get_submission, list_submissions, set_qualification_result
from arena.storage.leaderboard import add_run
from arena.worker.queue import claim_next, finish


def process_one(db_path: Path | str = "arena/storage/local/arena.sqlite3") -> bool:
    conn = connect(db_path)
    job = claim_next(conn)
    if not job:
        return False
    try:
        payload = json.loads(job["payload_json"])
        if job["kind"] == "qualification":
            _process_qualification(conn, payload)
        elif job["kind"] == "challenge":
            _process_challenge(conn, payload)
        elif job["kind"] == "leaderboard_run":
            _process_leaderboard(conn, payload)
        else:
            raise ValueError(f"unknown job kind: {job['kind']}")
        finish(conn, job["job_id"], "done")
        return True
    except Exception as exc:
        finish(conn, job["job_id"], "failed", str(exc))
        return False


def _process_qualification(conn, payload: dict) -> None:
    from arena.api.deps import ROOT
    from arena.sandbox.qualification import qualify_agent_source

    source = Path(payload["source_path"]).read_text(encoding="utf-8")
    side = payload["side"]
    report = qualify_agent_source(
        source=source,
        agent_path=payload["agent_path"],
        side=side,
        opponent_path="agents.static_defense.StaticDefense" if side == "offense" else "agents.static_offense.StaticOffense",
        seeds=[42],
        max_plays=1,
    )
    report_path = ROOT / "qualifications" / f"{payload['agent_id']}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    set_qualification_result(conn, payload["agent_id"], "passed" if report["passed"] else "failed", report_path)


def _run_agent_drive(row: dict, seed: int) -> dict:
    if row.get("access_tier") in {"declarative", "prompt_policy", "remote_endpoint"}:
        return _run_tiered_drive(row, seed)
    from scripts._evaluation import load_agent, run_validated_drive

    side = row["side"]
    agent_path = "agents.example_agent.ExampleCustomOffense" if side == "offense" else "agents.example_agent.ExampleCustomDefense"
    opponent_path = "agents.static_defense.StaticDefense" if side == "offense" else "agents.static_offense.StaticOffense"
    replay, failures = run_validated_drive(
        agent=load_agent(agent_path),
        side=side,
        opponent=load_agent(opponent_path),
        seed=seed,
        max_plays=8,
    )
    if failures:
        raise ValueError("agent failed validation during arena run")
    return replay


def _run_tiered_drive(row: dict, seed: int) -> dict:
    from agents.static_defense import StaticDefense
    from agents.static_offense import StaticOffense
    from arena.api.deps import ROOT
    from arena.tiers.factory import tiered_agent_from_submission
    from coachbench.contracts import validate_replay_contract
    from coachbench.engine import CoachBenchEngine

    agent = tiered_agent_from_submission(row, ROOT / "secrets" / "endpoints")
    if row["side"] == "offense":
        replay = CoachBenchEngine(seed=seed).run_drive(agent, StaticDefense())
    else:
        replay = CoachBenchEngine(seed=seed).run_drive(StaticOffense(), agent)
    replay.setdefault("agent_garage_config", {})
    replay["agent_garage_config"]["tier_metadata"] = {
        "agent_id": row["agent_id"],
        "access_tier": row["access_tier"],
        "endpoint_url_hash": row.get("endpoint_url_hash") if row["access_tier"] == "remote_endpoint" else None,
        "fallback_count": getattr(agent, "fallback_count", 0),
        "fallback_reasons": list(getattr(agent, "fallback_reasons", [])),
    }
    validate_replay_contract(replay)
    return replay


def _process_challenge(conn, payload: dict) -> None:
    from arena.api.deps import ROOT
    from coachbench.contracts import validate_challenge_report
    from scripts._evaluation import mean

    row = get_submission(conn, payload["agent_id"])
    replays = []
    paths = []
    out_dir = ROOT / "challenges" / payload["challenge_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for seed in payload["seeds"]:
        replay = _run_agent_drive(row, int(seed))
        replay_path = out_dir / f"{hashlib.sha256(str(seed).encode()).hexdigest()[:12]}.json"
        replay_path.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
        paths.append(str(replay_path))
        replays.append(replay)
    report = {
        "challenge_id": payload["challenge_id"],
        "agent_id": payload["agent_id"],
        "access_tier": row["access_tier"],
        "league": payload.get("league", "sandbox"),
        "opponent_kind": payload.get("opponent_kind", "static"),
        "seeds": [hashlib.sha256(str(seed).encode()).hexdigest()[:12] for seed in payload["seeds"]],
        "summary": {
            "games_played": len(replays),
            "mean_points_per_drive": mean([replay["score"]["points"] for replay in replays]),
            "touchdown_rate": mean([1.0 if replay["score"]["result"] == "touchdown" else 0.0 for replay in replays]),
        },
        "replay_paths": paths,
    }
    validate_challenge_report(report)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _process_leaderboard(conn, payload: dict) -> None:
    from arena.api.deps import ROOT

    season_id = payload["season_id"]
    seeds_path = ROOT / "secrets" / "seasons" / f"{season_id}.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))["seeds"]
    for row in list_submissions(conn, "passed"):
        if row.get("access_tier") != "sandboxed_code":
            continue
        for seed in seeds:
            replay = _run_agent_drive(row, int(seed))
            add_run(conn, season_id, row["agent_id"], int(seed), replay["score"]["points"], replay["score"]["result"], len(replay["plays"]), row["access_tier"])


def main() -> None:
    while process_one():
        pass


if __name__ == "__main__":
    main()
