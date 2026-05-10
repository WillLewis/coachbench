from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _evaluation import load_agent, run_validated_drive, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_agent, run_validated_drive, write_json

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from coachbench.contracts import ContractValidationError, validate_eval_suite_report
from coachbench.eval_metrics import (
    bootstrap_ci_95,
    calibration_summary,
    canonical_report_hash,
    concept_entropy,
    concept_frequency,
    fallback_rate,
    paired_seed_lift,
    points_per_drive,
    resource_exhaustion_rate,
    suite_config_hash,
    touchdown_rate,
)


DEFAULT_CANDIDATE_OFFENSE = "agents.adaptive_offense.AdaptiveOffense"
DEFAULT_CANDIDATE_DEFENSE = "agents.adaptive_defense.AdaptiveDefense"
DEFAULT_BASELINE_OFFENSE = "agents.static_offense.StaticOffense"
DEFAULT_BASELINE_DEFENSE = "agents.static_defense.StaticDefense"
SMOKE_SEED_PACK = Path("tests/fixtures/garage_knob_seeds.json")


def _load_seed_pack() -> dict[str, Any]:
    payload = json.loads(SMOKE_SEED_PACK.read_text(encoding="utf-8"))
    return {"name": "smoke", "seeds": [int(seed) for seed in payload["seeds"]]}


def _agent_meta(agent_path: str, side: str, locked: bool) -> dict[str, Any]:
    agent = load_agent(agent_path)
    return {
        "name": getattr(agent, "name", agent.__class__.__name__),
        "agent_path": agent_path,
        "side": side,
        "locked": locked,
    }


def _summary(replay: dict[str, Any], failures: list[dict[str, str]], inspected_side: str) -> dict[str, Any]:
    validation_failures = {"offense": 0, "defense": 0}
    validation_failures[inspected_side] = len(failures)
    return {
        "points": replay["score"]["points"],
        "result": replay["score"]["result"],
        "plays": len(replay["plays"]),
        "validation_failures": validation_failures,
    }


def _failure_messages(label: str, seed: int, failures: list[dict[str, str]]) -> list[str]:
    return [
        f"{label} seed {seed} {failure['check']}: {failure['detail']}"
        for failure in failures
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.suite != "smoke":
        raise NotImplementedError(f"{args.suite} suite is Phase 2")
    if args.side != "offense":
        raise NotImplementedError("defense evaluation is Phase 2")

    seed_pack = _load_seed_pack()
    candidate_meta = _agent_meta(args.candidate_offense, "offense", False)
    baseline_meta = _agent_meta(args.baseline_offense, "offense", True)
    config = {
        "suite_id": args.suite,
        "side": args.side,
        "candidates": [candidate_meta],
        "baseline": baseline_meta,
        "opponents": [],
        "seed_pack": seed_pack,
        "locked": False,
        "fixed_defense_agent_path": args.baseline_defense,
    }

    candidate_replays: list[dict[str, Any]] = []
    baseline_replays: list[dict[str, Any]] = []
    paired_runs: list[dict[str, Any]] = []
    paired_records: list[dict[str, Any]] = []
    errors: list[str] = []

    for seed in seed_pack["seeds"]:
        candidate_replay, candidate_failures = run_validated_drive(
            agent=load_agent(args.candidate_offense),
            side="offense",
            opponent=load_agent(args.baseline_defense),
            seed=seed,
            max_plays=8,
        )
        baseline_replay, baseline_failures = run_validated_drive(
            agent=load_agent(args.baseline_offense),
            side="offense",
            opponent=load_agent(args.baseline_defense),
            seed=seed,
            max_plays=8,
        )
        candidate_replays.append(candidate_replay)
        baseline_replays.append(baseline_replay)
        candidate_points = int(candidate_replay["score"]["points"])
        baseline_points = int(baseline_replay["score"]["points"])
        paired_records.append({
            "seed": seed,
            "candidate_points": candidate_points,
            "baseline_points": baseline_points,
        })
        paired_runs.append({
            "seed": seed,
            "candidate_replay_summary": _summary(candidate_replay, candidate_failures, "offense"),
            "baseline_replay_summary": _summary(baseline_replay, baseline_failures, "offense"),
            "lift": candidate_points - baseline_points,
        })
        errors.extend(_failure_messages("candidate", seed, candidate_failures))
        errors.extend(_failure_messages("baseline", seed, baseline_failures))

    lift_summary = paired_seed_lift(paired_records)
    deltas = [float(record["candidate_points"] - record["baseline_points"]) for record in paired_records]
    candidate_frequency = concept_frequency(candidate_replays, "offense")
    metrics = {
        "fallback_rate_candidate": fallback_rate(candidate_replays, "offense"),
        "fallback_rate_baseline": fallback_rate(baseline_replays, "offense"),
        "points_per_drive_candidate": points_per_drive(candidate_replays),
        "points_per_drive_baseline": points_per_drive(baseline_replays),
        "touchdown_rate_candidate": touchdown_rate(candidate_replays),
        "touchdown_rate_baseline": touchdown_rate(baseline_replays),
        "paired_seed_lift_mean": lift_summary["mean"],
        "paired_seed_win_rate": lift_summary["win_rate"],
        "bootstrap_ci_95": list(bootstrap_ci_95(deltas)),
        "concept_frequency_candidate": candidate_frequency,
        "concept_entropy_candidate": concept_entropy(candidate_frequency),
        "resource_exhaustion_rate_candidate": resource_exhaustion_rate(candidate_replays, "offense"),
        "calibration_summary": calibration_summary(candidate_replays),
    }
    report = {
        "schema_version": "eval_suite_report.v1",
        "suite_id": args.suite,
        "suite_config_hash": suite_config_hash(config),
        "report_hash": "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [candidate_meta],
        "baseline": baseline_meta,
        "opponents": [],
        "seed_pack": seed_pack,
        "paired_runs": paired_runs,
        "metrics": metrics,
        "warnings": [],
        "errors": errors,
    }
    report["report_hash"] = canonical_report_hash(report)
    validate_eval_suite_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CoachBench eval suite.")
    parser.add_argument("--suite", choices=("smoke", "standard", "extended"), required=True)
    parser.add_argument("--side", choices=("offense", "defense"), default="offense")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--candidate-offense", default=DEFAULT_CANDIDATE_OFFENSE)
    parser.add_argument("--candidate-defense", default=DEFAULT_CANDIDATE_DEFENSE)
    parser.add_argument("--baseline-offense", default=DEFAULT_BASELINE_OFFENSE)
    parser.add_argument("--baseline-defense", default=DEFAULT_BASELINE_DEFENSE)
    args = parser.parse_args()

    try:
        report = build_report(args)
    except ContractValidationError as exc:
        raise SystemExit(str(exc)) from None
    write_json(args.out, report)
    metrics = report["metrics"]
    print(
        f"smoke suite ok: report_hash={report['report_hash'][:12]} "
        f"fallback_rate_candidate={metrics['fallback_rate_candidate']} "
        f"paired_seed_lift_mean={metrics['paired_seed_lift_mean']}"
    )


if __name__ == "__main__":
    main()
