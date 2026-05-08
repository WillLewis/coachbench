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


GARAGE_SEED_PACK = Path("tests/fixtures/garage_knob_seeds.json")


def case_seed(base_seed: int, case_label: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{case_label}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def load_agent_garage_profiles() -> dict:
    return json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))


def profile_config(profiles: dict, group: str, key: str) -> dict:
    profile = dict(profiles[group][key])
    profile["profile_key"] = key
    return profile


def garage_seed_pack() -> list[int]:
    if not GARAGE_SEED_PACK.exists():
        return [6, 10, 42, 72, 99]
    payload = json.loads(GARAGE_SEED_PACK.read_text(encoding="utf-8"))
    return [int(seed) for seed in payload["seeds"]]


def garage_pack_case(base_seed: int, case_label: str, offense_profile: dict, defense_profile: dict) -> dict:
    seeds = garage_seed_pack()
    replays = [
        CoachBenchEngine(seed=seed).run_drive(
            AdaptiveOffense(offense_profile),
            AdaptiveDefense(defense_profile),
            agent_garage_config={
                "matrix_case": case_label,
                "source": "agent_garage_profiles_v1",
                "offense_profile": offense_profile,
                "defense_profile": defense_profile,
            },
        )
        for seed in seeds
    ]
    points_by_seed = {str(seed): replay["score"]["points"] for seed, replay in zip(seeds, replays)}
    counter_wins = sum(points < 7 for points in points_by_seed.values())
    return {
        "case": case_label,
        "seed": case_seed(base_seed, case_label),
        "points": sum(points_by_seed.values()),
        "result": "counter_wins_majority" if counter_wins > len(seeds) // 2 else "offense_not_countered",
        "plays": sum(len(replay["plays"]) for replay in replays),
        "film_room_headline": f"Counter wins {counter_wins}/{len(seeds)} garage seeds",
        "turning_point": replays[0]["film_room"]["turning_point"],
        "seed_pack": seeds,
        "points_by_seed": points_by_seed,
        "offense_touchdowns": sum(points >= 7 for points in points_by_seed.values()),
        "counter_wins": counter_wins,
        "offense_profile_key": offense_profile.get("profile_key"),
        "defense_profile_key": defense_profile.get("profile_key"),
    }


def garage_counter_cases(base_seed: int) -> list[dict]:
    profiles = load_agent_garage_profiles()
    offense = profile_config(profiles, "offense_archetypes", "aggressive_shot_taker")
    coverage = profile_config(profiles, "defense_archetypes", "coverage_shell_conservative")
    pressure = profile_config(profiles, "defense_archetypes", "pressure_look_defender")
    return [
        garage_pack_case(base_seed, "garage_baseline_aggressive_shot_taker_vs_coverage_shell_conservative", offense, coverage),
        garage_pack_case(base_seed, "garage_counter_pressure_look_vs_aggressive_shot_taker", offense, pressure),
    ]


def matrix_questions(results: list[dict]) -> list[dict]:
    by_case = {item["case"]: item for item in results}
    static_vs_static = by_case["A_static_offense_vs_A_static_defense"]
    adaptive_offense_vs_static_defense = by_case["B_adaptive_offense_vs_A_static_defense"]
    static_offense_vs_adaptive_defense = by_case["A_static_offense_vs_B_adaptive_defense"]
    adaptive_vs_adaptive = by_case["B_adaptive_offense_vs_B_adaptive_defense"]

    questions = [
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
    garage_baseline = by_case.get("garage_baseline_aggressive_shot_taker_vs_coverage_shell_conservative")
    garage_counter = by_case.get("garage_counter_pressure_look_vs_aggressive_shot_taker")
    if garage_baseline and garage_counter:
        questions.append({
            "id": "garage_pressure_counter_demonstration",
            "question": "Does Pressure-Look Defender counter Aggressive Shot-Taker across the fixed garage seed pack?",
            "baseline_case": garage_baseline["case"],
            "comparison_case": garage_counter["case"],
            "metric": "counter_seed_wins",
            "baseline_value": garage_baseline["counter_wins"],
            "comparison_value": garage_counter["counter_wins"],
            "answer": "yes" if garage_counter["counter_wins"] > len(garage_counter["seed_pack"]) // 2 else "no",
        })
    return questions


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
    results.extend(garage_counter_cases(args.seed))

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
