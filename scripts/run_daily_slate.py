from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401
from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.contracts import validate_daily_slate_report, validate_replay_contract
from coachbench.engine import CoachBenchEngine


def offense_agent(kind: str):
    return AdaptiveOffense() if kind == "adaptive" else StaticOffense()


def defense_agent(kind: str):
    return AdaptiveDefense() if kind == "adaptive" else StaticDefense()


def slate_entries(slate: dict):
    if "entries" in slate:
        return slate["entries"]

    seeds = slate.get("seeds", [])
    matchups = slate.get("matchups", [])
    if len(seeds) != len(matchups):
        raise ValueError("Daily Slate seeds and matchups must have equal length, or use explicit entries.")
    return [
        {"seed": seed, "matchup": matchup}
        for seed, matchup in zip(seeds, matchups)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fixed-seed local Daily Slate.")
    parser.add_argument("--slate", default="data/daily_slate/sample_slate.json")
    parser.add_argument("--out", default="data/daily_slate/results.json")
    args = parser.parse_args()

    slate = json.loads(Path(args.slate).read_text(encoding="utf-8"))
    results = []
    replay_dir = Path("data/daily_slate/replays")
    replay_dir.mkdir(parents=True, exist_ok=True)

    for entry in slate_entries(slate):
        seed = entry["seed"]
        matchup = entry["matchup"]
        offense = offense_agent(matchup["offense"])
        defense = defense_agent(matchup["defense"])
        engine = CoachBenchEngine(seed=int(seed))
        replay = engine.run_drive(
            offense,
            defense,
            agent_garage_config={
                "daily_slate_id": slate["slate_id"],
                "offense_type": matchup["offense"],
                "defense_type": matchup["defense"],
            },
        )
        validate_replay_contract(replay)
        replay_path = replay_dir / f"{slate['slate_id']}_{int(seed)}.json"
        replay_path.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
        results.append({
            "seed": int(seed),
            "seed_hash": replay["metadata"]["seed_hash"],
            "matchup": matchup,
            "offense_label": offense.name,
            "defense_label": defense.name,
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "replay_path": replay_path.as_posix(),
            "film_room": replay["film_room"],
        })

    total_points = sum(item["points"] for item in results)
    result_count = max(1, len(results))
    report = {
        "slate_id": slate["slate_id"],
        "results": results,
        "summary": {
            "total_points": total_points,
            "average_points": round(total_points / result_count, 2),
            "touchdown_rate": round(sum(1 for item in results if item["result"] == "touchdown") / result_count, 4),
            "field_goal_rate": round(sum(1 for item in results if item["result"] == "field_goal") / result_count, 4),
            "stopped_rate": round(sum(1 for item in results if item["result"] == "stopped") / result_count, 4),
            "mean_plays_per_drive": round(sum(item["plays"] for item in results) / result_count, 2),
            "suggested_review": "Compare each agent across the fixed Daily Slate entries before treating one result as robust.",
        },
    }
    validate_daily_slate_report(report)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
