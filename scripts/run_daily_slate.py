from __future__ import annotations

import argparse
import json
from pathlib import Path

import _path  # noqa: F401
from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.engine import CoachBenchEngine


def offense_agent(kind: str):
    return AdaptiveOffense() if kind == "adaptive" else StaticOffense()


def defense_agent(kind: str):
    return AdaptiveDefense() if kind == "adaptive" else StaticDefense()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fixed-seed local Daily Slate.")
    parser.add_argument("--slate", default="data/daily_slate/sample_slate.json")
    parser.add_argument("--out", default="data/daily_slate/results.json")
    args = parser.parse_args()

    slate = json.loads(Path(args.slate).read_text(encoding="utf-8"))
    seeds = slate["seeds"]
    matchups = slate["matchups"]
    results = []

    for index, seed in enumerate(seeds):
        matchup = matchups[index % len(matchups)]
        engine = CoachBenchEngine(seed=int(seed))
        replay = engine.run_drive(
            offense_agent(matchup["offense"]),
            defense_agent(matchup["defense"]),
            agent_garage_config={
                "daily_slate_id": slate["slate_id"],
                "offense_type": matchup["offense"],
                "defense_type": matchup["defense"],
            },
        )
        results.append({
            "seed_hash": replay["metadata"]["seed_hash"],
            "matchup": matchup,
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "film_room": replay["film_room"],
        })

    report = {
        "slate_id": slate["slate_id"],
        "results": results,
        "summary": {
            "total_points": sum(item["points"] for item in results),
            "average_points": round(sum(item["points"] for item in results) / max(1, len(results)), 2),
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
