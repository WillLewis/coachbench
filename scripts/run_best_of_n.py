from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_teams, mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_teams, mean, parse_seeds, run_direction, write_json

from coachbench.contracts import validate_best_of_n_report
from coachbench.team_config import TeamConfig


DEFAULT_SEEDS = "42,99,202,311,404,515,628,733,841,956,1063"


def _aggregate(team: TeamConfig, replays: list[dict[str, Any]]) -> dict[str, Any]:
    results = [replay["score"]["result"] for replay in replays]
    games = len(replays)
    return {
        "team_id": team.team_id,
        "label": team.label,
        "games_played": games,
        "total_points": sum(replay["score"]["points"] for replay in replays),
        "mean_points_per_drive": mean([replay["score"]["points"] for replay in replays]),
        "touchdown_rate": mean([1.0 if result == "touchdown" else 0.0 for result in results]),
        "field_goal_rate": mean([1.0 if result == "field_goal" else 0.0 for result in results]),
        "stopped_rate": mean([1.0 if result == "stopped" else 0.0 for result in results]),
        "mean_plays_per_drive": mean([len(replay["plays"]) for replay in replays]),
        "invalid_action_count_total": sum(replay["score"]["invalid_action_count"] for replay in replays),
    }


def build_report(team_a_path: Path, team_b_path: Path, seeds: list[int], max_plays: int) -> dict[str, Any]:
    team_a, team_b = load_teams(team_a_path, team_b_path)
    team_replays = {team_a.team_id: [], team_b.team_id: []}
    drives = []

    for seed in seeds:
        for offense_team, defense_team in ((team_a, team_b), (team_b, team_a)):
            direction = f"{offense_team.team_id}_oc_vs_{defense_team.team_id}_dc"
            replay = run_direction(
                offense_team=offense_team,
                defense_team=defense_team,
                seed=seed,
                max_plays=max_plays,
                matchup_direction=direction,
            )
            team_replays[offense_team.team_id].append(replay)
            drives.append({
                "seed": seed,
                "direction": direction,
                "points": replay["score"]["points"],
                "result": replay["score"]["result"],
                "plays": len(replay["plays"]),
                "film_room_headline": replay["film_room"]["headline"],
            })

    return {
        "report_id": "best_of_n_v0",
        "team_a": _aggregate(team_a, team_replays[team_a.team_id]),
        "team_b": _aggregate(team_b, team_replays[team_b.team_id]),
        "seeds": seeds,
        "drives": drives,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic best-of-N red-zone evaluation.")
    parser.add_argument("--team-a", required=True, type=Path)
    parser.add_argument("--team-b", required=True, type=Path)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.team_a, args.team_b, parse_seeds(args.seeds), args.max_plays)
    validate_best_of_n_report(report)
    write_json(args.out, report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
