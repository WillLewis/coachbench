from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_teams, mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_teams, mean, parse_seeds, run_direction, write_json

from coachbench.contracts import validate_mirrored_seed_report
from coachbench.roster_budget import load_roster


DEFAULT_SEEDS = "42,99,202,311,404,515,628,733,841,956,1063"


def _roster_summary(path: Path) -> dict[str, Any]:
    roster = load_roster(path)
    return roster.to_public_dict()


def build_report(
    team_a_path: Path,
    team_b_path: Path,
    offense_roster_path: Path,
    defense_roster_path: Path,
    seeds: list[int],
    max_plays: int,
) -> dict[str, Any]:
    team_a, team_b = load_teams(team_a_path, team_b_path)
    offense_roster = load_roster(offense_roster_path)
    defense_roster = load_roster(defense_roster_path)
    drives = []
    drive_1_points = []
    drive_2_points = []

    for seed in seeds:
        for direction_id, offense_team, defense_team, bucket in (
            ("drive_1", team_a, team_b, drive_1_points),
            ("drive_2", team_b, team_a, drive_2_points),
        ):
            direction = f"{direction_id}:{offense_team.team_id}_oc_vs_{defense_team.team_id}_dc"
            replay = run_direction(
                offense_team=offense_team,
                defense_team=defense_team,
                seed=seed,
                max_plays=max_plays,
                matchup_direction=direction,
                offense_roster=offense_roster,
                defense_roster=defense_roster,
            )
            bucket.append(replay["score"]["points"])
            drives.append({
                "seed": seed,
                "direction": direction,
                "points": replay["score"]["points"],
                "result": replay["score"]["result"],
                "plays": len(replay["plays"]),
                "film_room_headline": replay["film_room"]["headline"],
            })

    report = {
        "report_id": "mirrored_seed_v0",
        "team_a": {"team_id": team_a.team_id, "label": team_a.label},
        "team_b": {"team_id": team_b.team_id, "label": team_b.label},
        "offense_roster": _roster_summary(offense_roster_path),
        "defense_roster": _roster_summary(defense_roster_path),
        "seeds": seeds,
        "drives": drives,
        "roster_lift_offense": round(mean(drive_1_points) - mean(drive_2_points), 4),
        "notes": "Mirrored rosters - difference is agent skill.",
    }
    validate_mirrored_seed_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mirrored-seed evaluation with shared roster budgets.")
    parser.add_argument("--team-a", required=True, type=Path)
    parser.add_argument("--team-b", required=True, type=Path)
    parser.add_argument("--offense-roster", required=True, type=Path)
    parser.add_argument("--defense-roster", required=True, type=Path)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(
        args.team_a,
        args.team_b,
        args.offense_roster,
        args.defense_roster,
        parse_seeds(args.seeds),
        args.max_plays,
    )
    write_json(args.out, report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
