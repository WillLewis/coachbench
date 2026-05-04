from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from _evaluation import mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import mean, parse_seeds, run_direction, write_json

from coachbench.contracts import validate_budget_leaderboard_report
from coachbench.roster_budget import RosterBudget, load_roster
from coachbench.team_config import TeamConfig, load_team


DEFAULT_SEEDS = "42,99,202,311,404"


def _entry(team: TeamConfig, roster: RosterBudget) -> dict[str, Any]:
    return {
        "entry_id": f"{team.team_id}+{roster.roster_id}",
        "team": team,
        "roster": roster,
    }


def _entry_summary(entry: dict[str, Any], replays: list[dict[str, Any]]) -> dict[str, Any]:
    points = [replay["score"]["points"] for replay in replays]
    results = [replay["score"]["result"] for replay in replays]
    return {
        "entry_id": entry["entry_id"],
        "team_id": entry["team"].team_id,
        "roster_id": entry["roster"].roster_id,
        "label": f"{entry['team'].label} + {entry['roster'].label}",
        "budget_points": entry["roster"].budget_points,
        "games_played": len(replays),
        "total_points": sum(points),
        "mean_points_per_drive": mean(points),
        "touchdown_rate": mean([1.0 if result == "touchdown" else 0.0 for result in results]),
        "field_goal_rate": mean([1.0 if result == "field_goal" else 0.0 for result in results]),
        "stopped_rate": mean([1.0 if result == "stopped" else 0.0 for result in results]),
        "mean_plays_per_drive": mean([len(replay["plays"]) for replay in replays]),
        "invalid_action_count_total": sum(replay["score"]["invalid_action_count"] for replay in replays),
    }


def build_report(team_paths: list[Path], roster_paths: list[Path], seeds: list[int], max_plays: int) -> dict[str, Any]:
    if len(team_paths) < 2:
        raise ValueError("Budget leaderboard requires at least two teams")
    if not roster_paths:
        raise ValueError("Budget leaderboard requires at least one roster")
    teams = [load_team(path) for path in team_paths]
    rosters = [load_roster(path) for path in roster_paths]
    entries = [_entry(team, roster) for team in teams for roster in rosters]
    replays_by_entry = {entry["entry_id"]: [] for entry in entries}
    raw_drives = []

    for i, entry_i in enumerate(entries):
        for entry_j in entries[i + 1:]:
            for seed in seeds:
                for offense_entry, defense_entry in ((entry_i, entry_j), (entry_j, entry_i)):
                    direction = f"{offense_entry['entry_id']}_oc_vs_{defense_entry['entry_id']}_dc"
                    replay = run_direction(
                        offense_team=offense_entry["team"],
                        defense_team=defense_entry["team"],
                        seed=seed,
                        max_plays=max_plays,
                        matchup_direction=direction,
                        offense_roster=offense_entry["roster"],
                        defense_roster=defense_entry["roster"],
                    )
                    replays_by_entry[offense_entry["entry_id"]].append(replay)
                    raw_drives.append({
                        "seed": seed,
                        "entry_id": offense_entry["entry_id"],
                        "opponent_entry_id": defense_entry["entry_id"],
                        "direction": direction,
                        "points": replay["score"]["points"],
                        "result": replay["score"]["result"],
                        "plays": len(replay["plays"]),
                    })

    entry_summaries = [_entry_summary(entry, replays_by_entry[entry["entry_id"]]) for entry in entries]
    standings = [
        {"rank": index + 1, "entry_id": item["entry_id"], "mean_points_per_drive": item["mean_points_per_drive"], "total_points": item["total_points"]}
        for index, item in enumerate(sorted(entry_summaries, key=lambda row: (-row["mean_points_per_drive"], -row["total_points"], row["entry_id"])))
    ]
    report = {
        "report_id": "budget_leaderboard_v0",
        "entries": entry_summaries,
        "seeds": seeds,
        "standings": standings,
        "raw_drives": raw_drives,
    }
    validate_budget_leaderboard_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local budget-mode leaderboard.")
    parser.add_argument("--teams", required=True)
    parser.add_argument("--rosters", required=True)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(
        [Path(item) for item in args.teams.split(",") if item],
        [Path(item) for item in args.rosters.split(",") if item],
        parse_seeds(args.seeds),
        args.max_plays,
    )
    write_json(args.out, report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
