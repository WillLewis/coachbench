from __future__ import annotations

import argparse
import hashlib
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
from coachbench.contracts import validate_match_matrix_report
from coachbench.engine import CoachBenchEngine


def case_seed(base_seed: int, case_label: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_label}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def matrix_questions(results: list[dict]) -> list[dict]:
    by_case = {item["case"]: item for item in results}
    static_vs_static = by_case["A_static_offense_vs_A_static_defense"]
    adaptive_offense_vs_static_defense = by_case["B_adaptive_offense_vs_A_static_defense"]
    static_offense_vs_adaptive_defense = by_case["A_static_offense_vs_B_adaptive_defense"]
    adaptive_vs_adaptive = by_case["B_adaptive_offense_vs_B_adaptive_defense"]

    return [
        {
            "id": "adaptive_offense_lift_vs_same_defense",
            "question": "Does adaptive offense outperform static offense against the same defense?",
            "baseline_case": static_vs_static["case"],
            "comparison_case": adaptive_offense_vs_static_defense["case"],
            "metric": "points",
            "baseline_value": static_vs_static["points"],
            "comparison_value": adaptive_offense_vs_static_defense["points"],
            "answer": "yes" if adaptive_offense_vs_static_defense["points"] > static_vs_static["points"] else "no",
        },
        {
            "id": "adaptive_defense_suppression_vs_same_offense",
            "question": "Does adaptive defense suppress static offense?",
            "baseline_case": static_vs_static["case"],
            "comparison_case": static_offense_vs_adaptive_defense["case"],
            "metric": "opponent_points",
            "baseline_value": static_vs_static["points"],
            "comparison_value": static_offense_vs_adaptive_defense["points"],
            "answer": "yes" if static_offense_vs_adaptive_defense["points"] < static_vs_static["points"] else "no",
        },
        {
            "id": "adaptive_vs_adaptive_nontrivial_sequencing",
            "question": "Does adaptive-vs-adaptive produce nontrivial sequencing?",
            "baseline_case": None,
            "comparison_case": adaptive_vs_adaptive["case"],
            "metric": "turning_point_graph_cards",
            "baseline_value": None,
            "comparison_value": adaptive_vs_adaptive["turning_point"]["graph_card_ids"],
            "answer": "yes" if adaptive_vs_adaptive["turning_point"]["graph_card_ids"] else "no",
        },
        {
            "id": "obvious_exploits_or_degenerate_strategies",
            "question": "Does the graph create obvious exploits or degenerate strategies?",
            "baseline_case": None,
            "comparison_case": "all_cases",
            "metric": "case_points",
            "baseline_value": None,
            "comparison_value": {case["case"]: case["points"] for case in results},
            "answer": "needs_review",
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Team A/B interaction matrix.")
    parser.add_argument("--out", default="data/match_matrix_report.json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cases = [
        ("A_static_offense", StaticOffense(), "A_static_defense", StaticDefense()),
        ("B_adaptive_offense", AdaptiveOffense(), "A_static_defense", StaticDefense()),
        ("A_static_offense", StaticOffense(), "B_adaptive_defense", AdaptiveDefense()),
        ("B_adaptive_offense", AdaptiveOffense(), "B_adaptive_defense", AdaptiveDefense()),
    ]
    results = []
    for off_key, off_agent, def_key, def_agent in cases:
        label = f"{off_key}_vs_{def_key}"
        seed = case_seed(args.seed, label)
        engine = CoachBenchEngine(seed=seed)
        replay = engine.run_drive(off_agent, def_agent, agent_garage_config={"matrix_case": label})
        results.append({
            "case": label,
            "seed": seed,
            "points": replay["score"]["points"],
            "result": replay["score"]["result"],
            "plays": len(replay["plays"]),
            "film_room_headline": replay["film_room"]["headline"],
            "turning_point": replay["film_room"]["turning_point"],
        })

    report = {
        "report_id": "team-interaction-matrix-v0",
        "seed_start": args.seed,
        "cases": results,
        "questions": matrix_questions(results),
    }
    validate_match_matrix_report(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
