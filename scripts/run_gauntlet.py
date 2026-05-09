from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Callable
from typing import Any

try:
    from _evaluation import load_agent, mean, parse_seeds, run_validated_drive, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_agent, mean, parse_seeds, run_validated_drive, write_json

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from arena.runs.arena import run_gauntlet_job
from arena.storage.registry import connect


DEFAULT_SEEDS = "42,99,202,311,404,515,628,733,841,956,1063"


def _profiles() -> dict[str, Any]:
    return json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))


def opponents_for(side: str) -> list[tuple[str, Callable[[], Any]]]:
    profiles = _profiles()
    if side == "offense":
        return [
            ("Team A Static Defense", StaticDefense),
            ("Team B Adaptive Defense", AdaptiveDefense),
            (
                "Team B Adaptive Defense - Disguise Specialist",
                lambda: AdaptiveDefense(profiles["defense_archetypes"]["disguise_specialist"]),
            ),
        ]
    return [
        ("Team A Static Offense", StaticOffense),
        ("Team B Adaptive Offense", AdaptiveOffense),
        (
            "Team B Adaptive Offense - Misdirection Artist",
            lambda: AdaptiveOffense(profiles["offense_archetypes"]["misdirection_artist"]),
        ),
    ]


def _aggregate(name: str, replays: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, Any]:
    results = [replay["score"]["result"] for replay in replays]
    points = [replay["score"]["points"] for replay in replays]
    return {
        "name": name,
        "drives_played": len(replays),
        "total_points": sum(points),
        "mean_points": mean(points),
        "touchdown_rate": mean([1.0 if result == "touchdown" else 0.0 for result in results]),
        "invalid_action_count_total": sum(replay["score"]["invalid_action_count"] for replay in replays),
        "validator_failures": failures,
    }


def build_report(agent_path: str, side: str, seeds: list[int], max_plays: int) -> dict[str, Any]:
    opponent_reports = []
    all_failures = []
    for opponent_name, opponent_factory in opponents_for(side):
        replays = []
        failures = []
        for seed in seeds:
            replay, run_failures = run_validated_drive(
                agent=load_agent(agent_path),
                side=side,
                opponent=opponent_factory(),
                seed=seed,
                max_plays=max_plays,
            )
            replay_again, repeat_failures = run_validated_drive(
                agent=load_agent(agent_path),
                side=side,
                opponent=opponent_factory(),
                seed=seed,
                max_plays=max_plays,
            )
            if replay != replay_again:
                run_failures.append({"check": "V4", "detail": "same seed produced different replay"})
            run_failures.extend(repeat_failures)
            replays.append(replay)
            failures.extend({"seed": seed, **failure} for failure in run_failures)
        all_failures.extend({"opponent": opponent_name, **failure} for failure in failures)
        opponent_reports.append(_aggregate(opponent_name, replays, failures))

    return {
        "gauntlet_id": "coachbench_gauntlet_v0",
        "agent": agent_path,
        "side": side,
        "seeds": seeds,
        "opponents": opponent_reports,
        "failures": all_failures,
        "passed": not all_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local CoachBench agent gauntlet.")
    parser.add_argument("--agent")
    parser.add_argument("--side", choices=["offense", "defense"])
    parser.add_argument("--draft-id")
    parser.add_argument("--draft-side", choices=["offense", "defense"])
    parser.add_argument("--opponent-pool")
    parser.add_argument("--db-path", type=Path, default=Path("arena/storage/local/arena.sqlite3"))
    parser.add_argument("--job-id", default="cli_gauntlet")
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    seeds = parse_seeds(args.seeds)
    if args.draft_id:
        if not args.draft_side or not args.opponent_pool:
            raise SystemExit("--draft-side and --opponent-pool are required with --draft-id")
        report = run_gauntlet_job(
            connect(args.db_path),
            args.job_id,
            {
                "draft_id": args.draft_id,
                "draft_side": args.draft_side,
                "opponent_pool": [item for item in args.opponent_pool.split(",") if item],
                "seed_pack": seeds,
                "max_plays": args.max_plays,
            },
        )
    else:
        if not args.agent or not args.side:
            raise SystemExit("--agent and --side are required unless --draft-id is provided")
        report = build_report(args.agent, args.side, seeds, args.max_plays)
    write_json(args.out, report)
    print(f"Wrote {args.out}")
    if "passed" in report and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
