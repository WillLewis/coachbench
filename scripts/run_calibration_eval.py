from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_teams, mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_teams, mean, parse_seeds, run_direction, write_json

from coachbench.contracts import validate_calibration_eval_report
from coachbench.matchup_traits import load_matchup_traits
from coachbench.scouting import belief_calibration_error, load_scouting_report


DEFAULT_SEEDS = "42,99,202,311,404,515,628,733,841,956,1063"


def _calibration_from_replay(replay: dict[str, Any], traits) -> tuple[dict[str, Any], dict[str, Any]]:
    last = replay["plays"][-1]
    offense = belief_calibration_error(traits, last["offense_observed"]["belief_after"])
    defense = belief_calibration_error(traits, last["defense_observed"]["belief_after"])
    return offense, defense


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    offense_reports = [item["offense"] for item in items]
    defense_reports = [item["defense"] for item in items]
    traits = offense_reports[0]["calibrated_traits"] if offense_reports else []
    return {
        "offense_mae": mean([report["mean_absolute_error"] for report in offense_reports]),
        "defense_mae": mean([report["mean_absolute_error"] for report in defense_reports]),
        "per_trait_offense_mae": {
            trait: mean([report["per_trait_error"][trait] for report in offense_reports])
            for trait in traits
        },
        "per_trait_defense_mae": {
            trait: mean([report["per_trait_error"][trait] for report in defense_reports])
            for trait in traits
        },
    }


def _run_pass(team_a, team_b, traits, offense_scouting, defense_scouting, seeds: list[int], max_plays: int) -> dict[str, Any]:
    calibrations = []
    for seed in seeds:
        for offense_team, defense_team in ((team_a, team_b), (team_b, team_a)):
            replay = run_direction(
                offense_team=offense_team,
                defense_team=defense_team,
                seed=seed,
                max_plays=max_plays,
                matchup_direction=f"{offense_team.team_id}_oc_vs_{defense_team.team_id}_dc",
                matchup_traits=traits,
                offense_scouting=offense_scouting,
                defense_scouting=defense_scouting,
            )
            offense, defense = _calibration_from_replay(replay, traits)
            calibrations.append({"offense": offense, "defense": defense})
    return _summarize(calibrations)


def build_report(
    team_a_path: Path,
    team_b_path: Path,
    matchup_traits_path: Path,
    offense_scouting_path: Path | None,
    defense_scouting_path: Path | None,
    seeds: list[int],
    max_plays: int,
) -> dict[str, Any]:
    team_a, team_b = load_teams(team_a_path, team_b_path)
    traits = load_matchup_traits(matchup_traits_path)
    offense_scouting = load_scouting_report(offense_scouting_path) if offense_scouting_path else None
    defense_scouting = load_scouting_report(defense_scouting_path) if defense_scouting_path else None
    with_scouting = _run_pass(team_a, team_b, traits, offense_scouting, defense_scouting, seeds, max_plays)
    without_scouting = _run_pass(team_a, team_b, traits, None, None, seeds, max_plays)
    report = {
        "report_id": "calibration_eval_v0",
        "team_a": {"team_id": team_a.team_id, "label": team_a.label},
        "team_b": {"team_id": team_b.team_id, "label": team_b.label},
        "matchup_traits": {"matchup_id": traits.matchup_id, "label": traits.label},
        "scouting": {
            "offense_report_id": offense_scouting.report_id if offense_scouting else None,
            "defense_report_id": defense_scouting.report_id if defense_scouting else None,
        },
        "seeds": seeds,
        "with_scouting": with_scouting,
        "without_scouting": without_scouting,
        "scouting_mae_lift": {
            "offense": round(without_scouting["offense_mae"] - with_scouting["offense_mae"], 4),
            "defense": round(without_scouting["defense_mae"] - with_scouting["defense_mae"], 4),
        },
    }
    validate_calibration_eval_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hidden-trait calibration evaluation.")
    parser.add_argument("--team-a", required=True, type=Path)
    parser.add_argument("--team-b", required=True, type=Path)
    parser.add_argument("--matchup-traits", required=True, type=Path)
    parser.add_argument("--offense-scouting", type=Path)
    parser.add_argument("--defense-scouting", type=Path)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    write_json(
        args.out,
        build_report(
            args.team_a,
            args.team_b,
            args.matchup_traits,
            args.offense_scouting,
            args.defense_scouting,
            parse_seeds(args.seeds),
            args.max_plays,
        ),
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
