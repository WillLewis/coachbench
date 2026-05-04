from __future__ import annotations

"""Build PLAN 9.3 comparison answers from fixed-seed local matrix runs.

Thresholds are observational, not pass/fail gates:
- adaptive offense outperforms when adaptation_lift_offense > 0.
- adaptive defense suppresses when suppression_lift_defense > 0.
- adaptive-vs-adaptive sequencing is nontrivial when pair diversity > 0.5.
- no obvious degeneracy means no side calls one concept in at least 70% of calls.
"""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_teams, mean, parse_seeds, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_teams, mean, parse_seeds, run_direction, write_json

from coachbench.contracts import validate_comparison_report
from coachbench.team_config import TeamConfig


DEFAULT_SEEDS = "42,99,202,311,404,515,628,733,841,956,1063"


def _case_summary(label: str, replays: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case": label,
        "mean_points": mean([replay["score"]["points"] for replay in replays]),
        "mean_plays": mean([len(replay["plays"]) for replay in replays]),
        "results": Counter(replay["score"]["result"] for replay in replays),
    }


def _run_case(
    label: str,
    offense_team: TeamConfig,
    defense_team: TeamConfig,
    seeds: list[int],
    max_plays: int,
) -> list[dict[str, Any]]:
    return [
        run_direction(
            offense_team=offense_team,
            defense_team=defense_team,
            seed=seed,
            max_plays=max_plays,
            matchup_direction=label,
        )
        for seed in seeds
    ]


def _degenerate_flags(cases: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {"offense": Counter(), "defense": Counter()}
    for replays in cases.values():
        for replay in replays:
            for play in replay["plays"]:
                counts["offense"][play["public"]["offense_action"]["concept_family"]] += 1
                counts["defense"][play["public"]["defense_action"]["coverage_family"]] += 1

    flags = []
    for side, counter in counts.items():
        total = sum(counter.values())
        for concept, count in sorted(counter.items()):
            frequency = round(count / total, 4) if total else 0.0
            if frequency >= 0.7:
                flags.append({"side": side, "concept": concept, "frequency": frequency})
    return flags


def _pair_diversity(replays: list[dict[str, Any]]) -> float:
    pairs = []
    for replay in replays:
        pairs.extend(
            (
                play["public"]["offense_action"]["concept_family"],
                play["public"]["defense_action"]["coverage_family"],
            )
            for play in replay["plays"]
        )
    return round(len(set(pairs)) / len(pairs), 4) if pairs else 0.0


def build_report(team_a_path: Path, team_b_path: Path, seeds: list[int], max_plays: int = 8) -> dict[str, Any]:
    team_a, team_b = load_teams(team_a_path, team_b_path)
    cases = {
        "a_oc_vs_a_dc": _run_case("a_oc_vs_a_dc", team_a, team_a, seeds, max_plays),
        "b_oc_vs_a_dc": _run_case("b_oc_vs_a_dc", team_b, team_a, seeds, max_plays),
        "a_oc_vs_b_dc": _run_case("a_oc_vs_b_dc", team_a, team_b, seeds, max_plays),
        "b_oc_vs_b_dc": _run_case("b_oc_vs_b_dc", team_b, team_b, seeds, max_plays),
    }
    summaries = [_case_summary(label, replays) for label, replays in cases.items()]
    by_case = {summary["case"]: summary for summary in summaries}
    adaptation_lift = round(by_case["b_oc_vs_a_dc"]["mean_points"] - by_case["a_oc_vs_a_dc"]["mean_points"], 4)
    suppression_lift = round(by_case["a_oc_vs_a_dc"]["mean_points"] - by_case["a_oc_vs_b_dc"]["mean_points"], 4)
    diversity = _pair_diversity(cases["b_oc_vs_b_dc"])
    degeneracies = _degenerate_flags(cases)

    metrics = {
        "adaptation_lift_offense": adaptation_lift,
        "suppression_lift_defense": suppression_lift,
        "sequencing_diversity_b_vs_b": diversity,
        "degenerate_strategy_flags": degeneracies,
    }
    return {
        "report_id": "comparison_report_v0",
        "team_a": {"team_id": team_a.team_id, "label": team_a.label},
        "team_b": {"team_id": team_b.team_id, "label": team_b.label},
        "seeds": seeds,
        "cases": summaries,
        "answers": {
            "adaptive_offense_outperforms_static_offense": adaptation_lift > 0,
            "adaptive_defense_suppresses_static_offense": suppression_lift > 0,
            "adaptive_vs_adaptive_has_nontrivial_sequencing": diversity > 0.5,
            "graph_creates_no_obvious_degeneracies": degeneracies == [],
        },
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic Team A/B comparison report.")
    parser.add_argument("--team-a", required=True, type=Path)
    parser.add_argument("--team-b", required=True, type=Path)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.team_a, args.team_b, parse_seeds(args.seeds))
    validate_comparison_report(report)
    write_json(args.out, report)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
