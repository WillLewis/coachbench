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
    }
    validate_match_matrix_report(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
