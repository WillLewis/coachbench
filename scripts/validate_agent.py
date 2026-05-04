from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_agent, parse_seeds, run_validated_drive, static_counterpart, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_agent, parse_seeds, run_validated_drive, static_counterpart, write_json


VALIDATOR_ID = "coachbench_agent_validator_v0"


def _opponent(path: str | None, side: str) -> Any:
    return load_agent(path) if path else static_counterpart(side)


def validate_agent(agent_path: str, side: str, opponent_path: str | None, seeds: list[int], max_plays: int) -> dict[str, Any]:
    results = []
    failures = []
    for seed in seeds:
        try:
            replay, run_failures = run_validated_drive(
                agent=load_agent(agent_path),
                side=side,
                opponent=_opponent(opponent_path, side),
                seed=seed,
                max_plays=max_plays,
            )
            replay_again, repeat_failures = run_validated_drive(
                agent=load_agent(agent_path),
                side=side,
                opponent=_opponent(opponent_path, side),
                seed=seed,
                max_plays=max_plays,
            )
            if replay != replay_again:
                run_failures.append({"check": "V4", "detail": "same seed produced different replay"})
            run_failures.extend(repeat_failures)
            results.append({
                "seed": seed,
                "points": replay["score"]["points"],
                "result": replay["score"]["result"],
                "plays": len(replay["plays"]),
                "failures": run_failures,
            })
            failures.extend({"seed": seed, **failure} for failure in run_failures)
        except Exception as exc:
            failure = {"seed": seed, "check": "V5", "detail": str(exc)}
            failures.append(failure)
            results.append({"seed": seed, "failures": [failure]})

    return {
        "validator_id": VALIDATOR_ID,
        "agent": agent_path,
        "side": side,
        "seeds": seeds,
        "results": results,
        "passed": not failures,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a local CoachBench agent.")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--side", required=True, choices=["offense", "defense"])
    parser.add_argument("--opponent")
    parser.add_argument("--seeds", default="42,99,202")
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = validate_agent(args.agent, args.side, args.opponent, parse_seeds(args.seeds), args.max_plays)
    if args.report:
        write_json(args.report, report)
    if report["passed"]:
        print(f"Validation passed for {args.agent} on {len(report['seeds'])} seeds.")
        return
    for failure in report["failures"]:
        print(
            f"seed={failure['seed']} {failure['check']} failure: {failure['detail']}",
            file=sys.stderr,
        )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
