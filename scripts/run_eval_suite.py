from __future__ import annotations

import argparse
import importlib
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
from coachbench.eval_gates import evaluate_gates
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
from coachbench.graph_loader import StrategyGraph
from coachbench.locked_eval import enforce_locked_or_raise, scrub_llm_env_vars, set_locked_env


DEFAULT_CANDIDATE_OFFENSE = "agents.adaptive_offense.AdaptiveOffense"
DEFAULT_CANDIDATE_DEFENSE = "agents.adaptive_defense.AdaptiveDefense"
DEFAULT_BASELINE_OFFENSE = "agents.static_offense.StaticOffense"
DEFAULT_BASELINE_DEFENSE = "agents.static_defense.StaticDefense"
SUITE_DIR = Path("data/eval/suites")
SEED_PACK_DIR = Path("data/eval/seed_packs")
OPPONENT_SUITE_DIR = Path("data/eval/opponent_suites")
PROFILES_PATH = Path("agent_garage/profiles.json")
GRAPH = StrategyGraph()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _agent_class(dotted_path: str) -> Any:
    module_name, class_name = dotted_path.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), class_name)


def _agent_display_name(agent_path: str) -> str:
    cls = _agent_class(agent_path)
    return str(getattr(cls, "name", cls.__name__))


def _snake_name(value: str) -> str:
    result = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def _slug(opponent: dict[str, Any]) -> str:
    profile_id = opponent.get("profile_id")
    if profile_id:
        return str(profile_id)
    return f"{_snake_name(opponent['agent_path'].rsplit('.', 1)[-1])}_baseline"


def _profile_config(side: str, profile_id: str) -> dict[str, Any]:
    profiles = _read_json(PROFILES_PATH)
    profile = dict(profiles[f"{side}_archetypes"][profile_id])
    profile["profile_key"] = profile_id
    return profile


def _instantiate_agent(spec: dict[str, Any], label: str) -> Any:
    profile_id = spec.get("profile_id")
    if profile_id:
        agent = _agent_class(spec["agent_path"])(_profile_config(spec["side"], profile_id))
    else:
        agent = load_agent(spec["agent_path"])
    enforce_locked_or_raise(agent, label)
    return agent


def _within_budget(costs: dict[str, int], budget: dict[str, int]) -> bool:
    return all(int(costs.get(key, 0)) <= int(budget.get(key, 0)) for key in budget)


class ResourceGuard:
    def __init__(self, agent: Any, side: str, strict: bool = False) -> None:
        self.agent = agent
        self.side = side
        self.strict = strict
        self.name = getattr(agent, "name", agent.__class__.__name__)

    def _items(self, observation: dict[str, Any]) -> list[str]:
        key = "legal_concepts" if self.side == "offense" else "legal_calls"
        return [str(item) for item in observation.get(key, [])]

    def _costs(self) -> dict[str, dict[str, int]]:
        key = "offense_costs" if self.side == "offense" else "defense_costs"
        return GRAPH.constraints[key]

    def _future_exists(self, remaining: dict[str, int]) -> bool:
        return any(_within_budget(cost, remaining) for cost in self._costs().values())

    def _leaves_future(self, item: str, observation: dict[str, Any]) -> bool:
        state = observation["game_state"]
        if int(state["play_index"]) >= int(state["max_plays"]) - 1:
            return True
        remaining = observation["own_resource_remaining"]
        after = {
            key: int(remaining[key]) - int(self._costs()[item].get(key, 0))
            for key in remaining
        }
        return self._future_exists(after)

    def _safe_item(self, observation: dict[str, Any]) -> str:
        items = self._items(observation)
        if not items:
            raise IndexError(f"no legal {self.side} opponent action available")
        costs = self._costs()
        return min(
            items,
            key=lambda item: (
                not self._leaves_future(item, observation),
                sum(int(value) for value in costs[item].values()),
                item,
            ),
        )

    def _build(self, item: str, legal: Any) -> Any:
        if self.side == "offense":
            return legal.build_offense_action(item, "conservative")
        return legal.build_defense_action(item, "conservative")

    def _selected_item(self, action: Any) -> str:
        if self.side == "offense":
            return str(action.concept_family)
        return str(action.coverage_family)

    def choose_action(self, observation: dict[str, Any], memory: Any, legal: Any) -> Any:
        if self.strict:
            return self._build(self._safe_item(observation), legal)
        try:
            action = self.agent.choose_action(observation, memory, legal)
        except IndexError:
            return self._build(self._safe_item(observation), legal)
        item = self._selected_item(action)
        if item in self._items(observation) and not self._leaves_future(item, observation):
            safe = self._safe_item(observation)
            if self._leaves_future(safe, observation):
                return self._build(safe, legal)
        return action


def _agent_meta(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": spec.get("name") or _agent_display_name(spec["agent_path"]),
        "agent_path": spec["agent_path"],
        "side": spec["side"],
        "locked": bool(spec.get("locked", False)),
    }


def _opponent_meta(opponent: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": opponent["name"],
        "agent_path": opponent["agent_path"],
        "side": opponent["side"],
        "profile_id": opponent.get("profile_id"),
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


def _failure_messages(label: str, seed: int, opponent: str, failures: list[dict[str, str]]) -> list[str]:
    return [
        f"{label} seed {seed} opponent {opponent} {failure['check']}: {failure['detail']}"
        for failure in failures
        if failure["check"] != "V2"
    ]


def _load_seed_pack(name: str) -> dict[str, Any]:
    return _read_json(SEED_PACK_DIR / f"{name}.json")


def _synthesized_opponent(side: str) -> dict[str, Any]:
    if side == "offense":
        return {
            "name": "Static Defense (baseline opponent)",
            "agent_path": DEFAULT_BASELINE_DEFENSE,
            "side": "defense",
            "profile_id": None,
        }
    return {
        "name": "Static Offense (baseline opponent)",
        "agent_path": DEFAULT_BASELINE_OFFENSE,
        "side": "offense",
        "profile_id": None,
    }


def _load_opponents(suite_config: dict[str, Any], side: str) -> list[dict[str, Any]]:
    opponent_suite = suite_config.get("opponent_suite")
    if opponent_suite is None:
        return [_synthesized_opponent(side)]
    if side == "defense" and opponent_suite == "garage_defense_v1":
        opponent_suite = "garage_offense_v1"
    if side == "defense" and opponent_suite == "exploit_probe_v1":
        opponent_suite = "exploit_probe_offense_v1"
    payload = _read_json(OPPONENT_SUITE_DIR / f"{opponent_suite}.json")
    return [dict(opponent) for opponent in payload["opponents"]]


def _effective_config(args: argparse.Namespace) -> dict[str, Any]:
    suite_config = _read_json(SUITE_DIR / f"{args.suite}.json")
    config = json.loads(json.dumps(suite_config))
    config["selected_side"] = args.side
    if args.side == "defense":
        # Defense eval flips the candidate side and loads offense opponents.
        config["candidate"] = {
            "name": "AdaptiveDefense",
            "agent_path": DEFAULT_CANDIDATE_DEFENSE,
            "side": "defense",
            "locked": False,
        }
        config["baseline"] = {
            "name": "StaticDefense",
            "agent_path": DEFAULT_BASELINE_DEFENSE,
            "side": "defense",
            "locked": True,
        }
        if config.get("opponent_suite") == "garage_defense_v1":
            config["opponent_suite"] = "garage_offense_v1"
        if config.get("opponent_suite") == "exploit_probe_v1":
            config["opponent_suite"] = "exploit_probe_offense_v1"
    if args.candidate:
        config["candidate"]["agent_path"] = args.candidate
        config["candidate"]["name"] = _agent_display_name(args.candidate)
    if args.baseline:
        config["baseline"]["agent_path"] = args.baseline
        config["baseline"]["name"] = _agent_display_name(args.baseline)
    config["opponents"] = [_opponent_meta(opponent) for opponent in _load_opponents(config, args.side)]
    return config


def _eval_score(side: str, replay: dict[str, Any]) -> int:
    points = int(replay["score"]["points"])
    return points if side == "offense" else -points


def _metrics(candidate_replays: list[dict[str, Any]], baseline_replays: list[dict[str, Any]], paired_records: list[dict[str, Any]], side: str) -> dict[str, Any]:
    lift_summary = paired_seed_lift(paired_records)
    deltas = [float(record["candidate_points"] - record["baseline_points"]) for record in paired_records]
    candidate_frequency = concept_frequency(candidate_replays, side)
    return {
        "fallback_rate_candidate": fallback_rate(candidate_replays, side),
        "fallback_rate_baseline": fallback_rate(baseline_replays, side),
        "points_per_drive_candidate": points_per_drive(candidate_replays),
        "points_per_drive_baseline": points_per_drive(baseline_replays),
        "touchdown_rate_candidate": touchdown_rate(candidate_replays),
        "touchdown_rate_baseline": touchdown_rate(baseline_replays),
        "paired_seed_lift_mean": lift_summary["mean"],
        "paired_seed_win_rate": lift_summary["win_rate"],
        "bootstrap_ci_95": list(bootstrap_ci_95(deltas)),
        "concept_frequency_candidate": candidate_frequency,
        "concept_entropy_candidate": concept_entropy(candidate_frequency),
        "resource_exhaustion_rate_candidate": resource_exhaustion_rate(candidate_replays, side),
        "calibration_summary": calibration_summary(candidate_replays),
    }


def _per_opponent_metrics(
    opponent_name: str,
    candidate_replays: list[dict[str, Any]],
    baseline_replays: list[dict[str, Any]],
    paired_records: list[dict[str, Any]],
    side: str,
) -> dict[str, Any]:
    metrics = _metrics(candidate_replays, baseline_replays, paired_records, side)
    return {
        "opponent_name": opponent_name,
        "n_replays_candidate": len(candidate_replays),
        "n_replays_baseline": len(baseline_replays),
        "fallback_rate_candidate": metrics["fallback_rate_candidate"],
        "fallback_rate_baseline": metrics["fallback_rate_baseline"],
        "points_per_drive_candidate": metrics["points_per_drive_candidate"],
        "points_per_drive_baseline": metrics["points_per_drive_baseline"],
        "touchdown_rate_candidate": metrics["touchdown_rate_candidate"],
        "touchdown_rate_baseline": metrics["touchdown_rate_baseline"],
        "paired_seed_lift_mean": metrics["paired_seed_lift_mean"],
        "paired_seed_win_rate": metrics["paired_seed_win_rate"],
        "bootstrap_ci_95": metrics["bootstrap_ci_95"],
        "concept_frequency_candidate": metrics["concept_frequency_candidate"],
        "concept_entropy_candidate": metrics["concept_entropy_candidate"],
    }


def _agent_for_run(spec: dict[str, Any], guard: bool, label: str, strict: bool = False) -> Any:
    agent = _instantiate_agent(spec, label)
    return ResourceGuard(agent, spec["side"], strict=strict) if guard else agent


def _prepare_locked_mode(locked: bool) -> None:
    if locked:
        set_locked_env(True)
        removed = scrub_llm_env_vars()
        print(f"locked mode: scrubbed {len(removed)} LLM env vars")
        return
    set_locked_env(False)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    _prepare_locked_mode(args.locked)
    config = _effective_config(args)
    side = config["candidate"]["side"]
    seed_pack = _load_seed_pack(config["seed_pack"])
    opponents = config["opponents"]
    candidate_meta = _agent_meta(config["candidate"])
    baseline_meta = _agent_meta(config["baseline"])

    candidate_replays: list[dict[str, Any]] = []
    baseline_replays: list[dict[str, Any]] = []
    paired_runs: list[dict[str, Any]] = []
    paired_records: list[dict[str, Any]] = []
    per_opponent_metrics: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for opponent in opponents:
        slug = _slug(opponent)
        opponent_candidate_replays: list[dict[str, Any]] = []
        opponent_baseline_replays: list[dict[str, Any]] = []
        opponent_paired_records: list[dict[str, Any]] = []
        for seed in seed_pack["seeds"]:
            candidate_replay, candidate_failures = run_validated_drive(
                agent=_agent_for_run(config["candidate"], args.candidate is None, "candidate"),
                side=side,
                opponent=ResourceGuard(_instantiate_agent(opponent, f"opponent {slug}"), opponent["side"]),
                seed=int(seed),
                max_plays=int(config["max_plays"]),
            )
            baseline_replay, baseline_failures = run_validated_drive(
                agent=_agent_for_run(config["baseline"], args.baseline is None, "baseline", strict=True),
                side=side,
                opponent=ResourceGuard(_instantiate_agent(opponent, f"opponent {slug}"), opponent["side"]),
                seed=int(seed),
                max_plays=int(config["max_plays"]),
            )
            candidate_replay["eval_opponent"] = slug
            baseline_replay["eval_opponent"] = slug
            candidate_replays.append(candidate_replay)
            baseline_replays.append(baseline_replay)
            opponent_candidate_replays.append(candidate_replay)
            opponent_baseline_replays.append(baseline_replay)
            record = {
                "seed": int(seed),
                "candidate_points": _eval_score(side, candidate_replay),
                "baseline_points": _eval_score(side, baseline_replay),
            }
            paired_records.append(record)
            opponent_paired_records.append(record)
            paired_runs.append({
                "seed": int(seed),
                "opponent": slug,
                "candidate_replay_summary": _summary(candidate_replay, candidate_failures, side),
                "baseline_replay_summary": _summary(baseline_replay, baseline_failures, side),
                "lift": record["candidate_points"] - record["baseline_points"],
            })
            errors.extend(_failure_messages("candidate", int(seed), slug, candidate_failures))
            errors.extend(_failure_messages("baseline", int(seed), slug, baseline_failures))
        per_opponent_metrics[slug] = _per_opponent_metrics(
            opponent["name"],
            opponent_candidate_replays,
            opponent_baseline_replays,
            opponent_paired_records,
            side,
        )

    report = {
        "schema_version": "eval_suite_report.v3",
        "suite_id": args.suite,
        "suite_config_hash": suite_config_hash(config),
        "report_hash": "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locked": bool(args.locked),
        "candidates": [candidate_meta],
        "baseline": baseline_meta,
        "opponents": opponents,
        "seed_pack": seed_pack,
        "paired_runs": paired_runs,
        "metrics": _metrics(candidate_replays, baseline_replays, paired_records, side),
        "per_opponent_metrics": per_opponent_metrics,
        "gates": {"passed": [], "failed": [], "warnings": [], "lift_strength": "none"},
        "warnings": [],
        "errors": errors,
    }
    gate_suite_id = "smoke" if args.suite == "exploit" else args.suite
    report["gates"] = evaluate_gates(report, gate_suite_id, thresholds=config.get("gates"))
    report["report_hash"] = canonical_report_hash(report)
    validate_eval_suite_report(report)
    return report


def _exit_for_fail_on(report: dict[str, Any], mode: str) -> int:
    if mode == "never":
        return 0
    gates = report["gates"]
    if gates["failed"] or report["errors"]:
        return 1
    if mode == "warning" and gates["warnings"]:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CoachBench eval suite.")
    parser.add_argument("--suite", choices=("smoke", "standard", "extended", "exploit"), required=True)
    parser.add_argument("--side", choices=("offense", "defense"), default="offense")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--candidate")
    parser.add_argument("--baseline")
    parser.add_argument("--fail-on", choices=("never", "warning", "error"), default="error")
    parser.add_argument("--locked", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    try:
        report = build_report(args)
    except ContractValidationError as exc:
        raise SystemExit(str(exc)) from None
    write_json(args.out, report)
    gates = report["gates"]
    print(
        f"{args.suite} ok report_hash={report['report_hash'][:12]} "
        f"lift={gates['lift_strength']} locked={report['locked']} passed={len(gates['passed'])} "
        f"warnings={len(gates['warnings'])} failed={len(gates['failed'])}"
    )
    raise SystemExit(_exit_for_fail_on(report, args.fail_on))


if __name__ == "__main__":
    main()
