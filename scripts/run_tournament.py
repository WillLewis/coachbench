from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from _evaluation import mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import mean, parse_seeds, run_direction, write_json

from coachbench.team_config import TeamConfig, load_team
from coachbench.contracts import validate_tournament_report


DEFAULT_SEEDS = "42,99,202,311,404"


def _team_summary(team: TeamConfig, replays: list[dict[str, Any]], head_to_head: dict[str, Any], rank: int) -> dict[str, Any]:
    points = [replay["score"]["points"] for replay in replays]
    results = [replay["score"]["result"] for replay in replays]
    return {
        "rank": rank,
        "team_id": team.team_id,
        "label": team.label,
        "games_played": len(replays),
        "mean_points_per_drive": mean(points),
        "touchdown_rate": mean([1.0 if result == "touchdown" else 0.0 for result in results]),
        "total_points": sum(points),
        "validator_failures": [],
        "head_to_head": head_to_head,
    }


def _result_bucket(points_for: int, points_against: int) -> str:
    if points_for > points_against:
        return "wins"
    if points_for < points_against:
        return "losses"
    return "ties"


def build_report(team_paths: list[Path], seeds: list[int], max_plays: int) -> dict[str, Any]:
    if len(team_paths) < 2:
        raise ValueError("Tournament requires at least two teams")
    teams = [load_team(path) for path in team_paths]
    replays_by_team = {team.team_id: [] for team in teams}
    h2h = {team.team_id: {} for team in teams}
    raw_drives = []

    for i, team_i in enumerate(teams):
        for team_j in teams[i + 1:]:
            pair_points = {team_i.team_id: [], team_j.team_id: []}
            for seed in seeds:
                replay_i = run_direction(
                    offense_team=team_i,
                    defense_team=team_j,
                    seed=seed,
                    max_plays=max_plays,
                    matchup_direction=f"{team_i.team_id}_oc_vs_{team_j.team_id}_dc",
                )
                replay_j = run_direction(
                    offense_team=team_j,
                    defense_team=team_i,
                    seed=seed,
                    max_plays=max_plays,
                    matchup_direction=f"{team_j.team_id}_oc_vs_{team_i.team_id}_dc",
                )
                for team, opponent, replay in ((team_i, team_j, replay_i), (team_j, team_i, replay_j)):
                    replays_by_team[team.team_id].append(replay)
                    pair_points[team.team_id].append(replay["score"]["points"])
                    raw_drives.append({
                        "seed": seed,
                        "team_id": team.team_id,
                        "opponent_team_id": opponent.team_id,
                        "direction": f"{team.team_id}_oc_vs_{opponent.team_id}_dc",
                        "points": replay["score"]["points"],
                        "result": replay["score"]["result"],
                        "plays": len(replay["plays"]),
                    })
                bucket_i = _result_bucket(replay_i["score"]["points"], replay_j["score"]["points"])
                bucket_j = _result_bucket(replay_j["score"]["points"], replay_i["score"]["points"])
                h2h[team_i.team_id].setdefault(team_j.team_id, {"wins": 0, "losses": 0, "ties": 0, "mean_points_diff": 0.0})[bucket_i] += 1
                h2h[team_j.team_id].setdefault(team_i.team_id, {"wins": 0, "losses": 0, "ties": 0, "mean_points_diff": 0.0})[bucket_j] += 1
            diff_i = mean(pair_points[team_i.team_id]) - mean(pair_points[team_j.team_id])
            h2h[team_i.team_id][team_j.team_id]["mean_points_diff"] = round(diff_i, 4)
            h2h[team_j.team_id][team_i.team_id]["mean_points_diff"] = round(-diff_i, 4)

    ranking = sorted(
        teams,
        key=lambda team: (
            -mean([replay["score"]["points"] for replay in replays_by_team[team.team_id]]),
            -sum(replay["score"]["points"] for replay in replays_by_team[team.team_id]),
            team.team_id,
        ),
    )
    standings = [
        _team_summary(team, replays_by_team[team.team_id], h2h[team.team_id], rank)
        for rank, team in enumerate(ranking, start=1)
    ]
    return {
        "report_id": "tournament_v0",
        "teams": [{"team_id": team.team_id, "label": team.label} for team in teams],
        "seeds": seeds,
        "standings": standings,
        "raw_drives": raw_drives,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local CoachBench round-robin tournament.")
    parser.add_argument("--teams", required=True)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = build_report([Path(item) for item in args.teams.split(",") if item], parse_seeds(args.seeds), args.max_plays)
    validate_tournament_report(report)
    write_json(args.out, report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
