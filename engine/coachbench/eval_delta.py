from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .eval_metrics import canonical_report_hash


LIFT_STRENGTH_ORDER = {"none": 0, "confirmed": 1, "strong": 2}
REGRESSION_NUMERIC_CHECKS = {
    "fallback_rate_candidate": "increase",
    "fallback_rate_baseline": "increase",
    "resource_exhaustion_rate_candidate": "increase",
    "paired_seed_lift_mean": "decrease",
    "paired_seed_win_rate": "decrease",
    "touchdown_rate_candidate": "decrease",
    "points_per_drive_candidate": "decrease",
}
GARAGE_DEFENSE_PROFILES = {
    "coverage_shell_conservative",
    "pressure_look_defender",
    "disguise_specialist",
    "man_coverage_bully",
}
GARAGE_OFFENSE_PROFILES = {
    "efficiency_optimizer",
    "aggressive_shot_taker",
    "misdirection_artist",
    "run_game_builder",
}


def compute_comparability(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_stub = _report_stub(before)
    after_stub = _report_stub(after)
    same_schema_version = before.get("schema_version") == after.get("schema_version")
    same_suite_id = before_stub["suite_id"] == after_stub["suite_id"]
    same_seed_pack = before_stub["seed_pack_name"] == after_stub["seed_pack_name"]
    same_candidate = before_stub["candidate_name"] == after_stub["candidate_name"]
    same_baseline = before_stub["baseline_name"] == after_stub["baseline_name"]
    same_opponent_suite = before_stub["opponent_suite_name"] == after_stub["opponent_suite_name"]
    same_locked_mode = before_stub["locked"] == after_stub["locked"]
    warnings: list[str] = []
    errors: list[str] = []
    if not same_schema_version:
        errors.append(f"schema_version mismatch: {before.get('schema_version')} -> {after.get('schema_version')}")
    if not same_suite_id:
        errors.append(f"suite_id mismatch: {before_stub['suite_id']} -> {after_stub['suite_id']}")
    if not same_seed_pack:
        errors.append(f"seed_pack mismatch: {before_stub['seed_pack_name']} -> {after_stub['seed_pack_name']}")
    if not same_candidate:
        warnings.append(f"candidate_name changed: {before_stub['candidate_name']} -> {after_stub['candidate_name']}")
    if not same_baseline:
        warnings.append(f"baseline_name changed: {before_stub['baseline_name']} -> {after_stub['baseline_name']}")
    if not same_opponent_suite:
        warnings.append(f"opponent_suite_name changed: {before_stub['opponent_suite_name']} -> {after_stub['opponent_suite_name']}")
    if not same_locked_mode:
        warnings.append(f"locked mode changed: {before_stub['locked']} -> {after_stub['locked']}")
    return {
        "same_schema_version": same_schema_version,
        "same_suite_id": same_suite_id,
        "same_seed_pack": same_seed_pack,
        "same_candidate": same_candidate,
        "same_baseline": same_baseline,
        "same_opponent_suite": same_opponent_suite,
        "same_locked_mode": same_locked_mode,
        "warnings": warnings,
        "errors": errors,
    }


def compute_metric_deltas(before_metrics: dict[str, Any], after_metrics: dict[str, Any]) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    for key in sorted(set(before_metrics) | set(after_metrics)):
        before = before_metrics.get(key)
        after = after_metrics.get(key)
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            deltas[key] = {"before": float(before), "after": float(after), "delta": float(after) - float(before)}
        elif key == "bootstrap_ci_95" and _is_two_number_list(before) and _is_two_number_list(after):
            deltas[key] = {
                "before": [float(before[0]), float(before[1])],
                "after": [float(after[0]), float(after[1])],
                "delta_low": float(after[0]) - float(before[0]),
                "delta_high": float(after[1]) - float(before[1]),
            }
        elif key == "concept_frequency_candidate" and isinstance(before, dict) and isinstance(after, dict):
            deltas[key] = _concept_frequency_delta(before, after)
        elif key == "calibration_summary" and (before is None or after is None or isinstance(before, dict) or isinstance(after, dict)):
            deltas[key] = {"before": before, "after": after, "delta": None}
    return deltas


def compute_per_opponent_deltas(before_per_op: dict[str, Any], after_per_op: dict[str, Any]) -> dict[str, Any]:
    before_slugs = set(before_per_op)
    after_slugs = set(after_per_op)
    return {
        "added_opponents": sorted(after_slugs - before_slugs),
        "removed_opponents": sorted(before_slugs - after_slugs),
        "opponents": {
            slug: compute_metric_deltas(before_per_op[slug], after_per_op[slug])
            for slug in sorted(before_slugs & after_slugs)
        },
    }


def compute_gate_transitions(before_gates: dict[str, Any], after_gates: dict[str, Any]) -> dict[str, Any]:
    before_strength = str(before_gates.get("lift_strength", "none"))
    after_strength = str(after_gates.get("lift_strength", "none"))
    before_order = LIFT_STRENGTH_ORDER.get(before_strength, 0)
    after_order = LIFT_STRENGTH_ORDER.get(after_strength, 0)
    if after_order > before_order:
        direction = "improvement"
    elif after_order < before_order:
        direction = "regression"
    else:
        direction = "unchanged"
    before_passed = { _gate_key(item) for item in before_gates.get("passed", []) }
    before_failed = { _gate_key(item) for item in before_gates.get("failed", []) }
    after_passed = { str(item) for item in after_gates.get("passed", []) }
    after_failed = { str(item) for item in after_gates.get("failed", []) }
    before_warnings = {str(item) for item in before_gates.get("warnings", [])}
    after_warnings = {str(item) for item in after_gates.get("warnings", [])}
    return {
        "lift_strength": {"before": before_strength, "after": after_strength, "direction": direction},
        "passed_now_failed": [item for item in sorted(after_failed) if _gate_key(item) in before_passed],
        "failed_now_passed": [item for item in sorted(after_passed) if _gate_key(item) in before_failed],
        "warning_now_clear": sorted(before_warnings - after_warnings),
        "newly_warning": sorted(after_warnings - before_warnings),
    }


def classify_regression(delta_report: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    comparability_errors = delta_report.get("comparability", {}).get("errors", [])
    for error in comparability_errors:
        reasons.append(f"comparability error: {error}")
    gate_transitions = delta_report.get("gate_transitions", {})
    for gate in gate_transitions.get("passed_now_failed", []):
        reasons.append(f"gate passed_now_failed: {gate}")
    lift = gate_transitions.get("lift_strength", {})
    if lift.get("direction") == "regression":
        reasons.append(f"lift_strength weakened: {lift.get('before')} -> {lift.get('after')}")
    metric_deltas = delta_report.get("metric_deltas", {})
    for key, direction in REGRESSION_NUMERIC_CHECKS.items():
        item = metric_deltas.get(key)
        if not isinstance(item, dict) or "delta" not in item:
            continue
        delta = float(item["delta"])
        if direction == "increase" and delta > 0:
            reasons.append(_numeric_reason(key, "increased", item))
        if direction == "decrease" and delta < 0:
            reasons.append(_numeric_reason(key, "decreased", item))
    return {"is_regression": bool(reasons), "reasons": reasons}


def build_delta_report(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    report = {
        "schema_version": "eval_delta_report.v1",
        "delta_hash": "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "before": _report_stub(before),
        "after": _report_stub(after),
        "comparability": compute_comparability(before, after),
        "metric_deltas": compute_metric_deltas(before.get("metrics", {}), after.get("metrics", {})),
        "per_opponent_metric_deltas": compute_per_opponent_deltas(
            before.get("per_opponent_metrics", {}),
            after.get("per_opponent_metrics", {}),
        ),
        "gate_transitions": compute_gate_transitions(before.get("gates", {}), after.get("gates", {})),
        "regression": {"is_regression": False, "reasons": []},
    }
    report["regression"] = classify_regression(report)
    report["delta_hash"] = delta_report_hash(report)
    return report


def delta_report_hash(report: dict[str, Any]) -> str:
    return canonical_report_hash(report, volatile_fields={"delta_hash", "generated_at"})


def _is_two_number_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value)


def _concept_frequency_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_values = {str(key): float(value) for key, value in before.items()}
    after_values = {str(key): float(value) for key, value in after.items()}
    before_concepts = set(before_values)
    after_concepts = set(after_values)
    return {
        "before": before_values,
        "after": after_values,
        "added_concepts": sorted(after_concepts - before_concepts),
        "removed_concepts": sorted(before_concepts - after_concepts),
        "changed_concepts": {
            concept: {
                "before": before_values.get(concept, 0.0),
                "after": after_values.get(concept, 0.0),
                "delta": after_values.get(concept, 0.0) - before_values.get(concept, 0.0),
            }
            for concept in sorted(before_concepts & after_concepts)
            if before_values.get(concept, 0.0) != after_values.get(concept, 0.0)
        },
    }


def _report_stub(report: dict[str, Any]) -> dict[str, Any]:
    candidates = report.get("candidates") if isinstance(report.get("candidates"), list) else []
    candidate = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
    baseline = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
    seed_pack = report.get("seed_pack") if isinstance(report.get("seed_pack"), dict) else {}
    return {
        "report_hash": str(report.get("report_hash", "")),
        "suite_id": str(report.get("suite_id", "")),
        "candidate_name": str(candidate.get("name", "")),
        "baseline_name": str(baseline.get("name", "")),
        "seed_pack_name": str(seed_pack.get("name", "")),
        "opponent_suite_name": _opponent_suite_name(report),
        "locked": bool(report.get("locked", False)),
    }


def _opponent_suite_name(report: dict[str, Any]) -> str:
    explicit = report.get("opponent_suite_name") or report.get("opponent_suite")
    if isinstance(explicit, str) and explicit:
        return explicit
    opponents = report.get("opponents", [])
    if not isinstance(opponents, list):
        return ""
    profile_ids = {opponent.get("profile_id") for opponent in opponents if isinstance(opponent, dict) and opponent.get("profile_id")}
    sides = {opponent.get("side") for opponent in opponents if isinstance(opponent, dict)}
    if profile_ids == GARAGE_DEFENSE_PROFILES and sides == {"defense"}:
        return "garage_defense_v1"
    if profile_ids == GARAGE_OFFENSE_PROFILES and sides == {"offense"}:
        return "garage_offense_v1"
    if len(opponents) == 1 and isinstance(opponents[0], dict):
        path = str(opponents[0].get("agent_path", ""))
        if path.endswith("ExploitProbeDefense"):
            return "exploit_probe_v1"
        if path.endswith("ExploitProbeOffense"):
            return "exploit_probe_offense_v1"
        if path.endswith("StaticDefense"):
            return "static_defense_baseline"
        if path.endswith("StaticOffense"):
            return "static_offense_baseline"
    return "|".join(
        sorted(
            str(opponent.get("profile_id") or opponent.get("agent_path") or opponent.get("name") or "")
            for opponent in opponents
            if isinstance(opponent, dict)
        )
    )


def _gate_key(gate: Any) -> str:
    text = str(gate)
    prefix = text.split(" ", 1)[0]
    metric = prefix.split("=", 1)[0]
    suffix = ""
    if "(opponent=" in text:
        suffix = "|opponent=" + text.split("(opponent=", 1)[1].split(")", 1)[0]
    return metric + suffix


def _numeric_reason(key: str, verb: str, item: dict[str, Any]) -> str:
    before = float(item["before"])
    after = float(item["after"])
    delta = float(item["delta"])
    return f"{key} {verb}: {before} -> {after} (delta {delta:+g})"
