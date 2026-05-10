from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any

from .matchup_traits import MatchupTraits
from .scouting import belief_calibration_error


def _validate_side(side: str) -> None:
    if side not in {"offense", "defense"}:
        raise ValueError("side must be offense or defense")


def _all_plays(replays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [play for replay in replays for play in replay.get("plays", [])]


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def fallback_rate(replays: list[dict[str, Any]], side: str) -> float:
    _validate_side(side)
    plays = _all_plays(replays)
    if not plays:
        return 0.0
    fallbacks = sum(
        1
        for play in plays
        if bool(play["engine_internal"]["validation_result"][side]["fallback_used"])
    )
    return fallbacks / len(plays)


def points_per_drive(replays: list[dict[str, Any]]) -> float:
    return _mean([float(replay["score"]["points"]) for replay in replays])


def touchdown_rate(replays: list[dict[str, Any]]) -> float:
    if not replays:
        return 0.0
    return sum(1 for replay in replays if replay["score"]["result"] == "touchdown") / len(replays)


def concept_frequency(replays: list[dict[str, Any]], side: str) -> dict[str, float]:
    _validate_side(side)
    field = "concept_family" if side == "offense" else "coverage_family"
    action_key = "offense_action" if side == "offense" else "defense_action"
    counts: dict[str, int] = {}
    total = 0
    for play in _all_plays(replays):
        concept = str(play["public"][action_key][field])
        counts[concept] = counts.get(concept, 0) + 1
        total += 1
    if total == 0:
        return {}
    return {concept: count / total for concept, count in sorted(counts.items())}


def concept_entropy(frequency: dict[str, float]) -> float:
    if len(frequency) < 2:
        return 0.0
    entropy = -sum(value * math.log2(value) for value in frequency.values() if value > 0)
    return round(entropy, 4)


def _log_resource_gap(replays: list[dict[str, Any]], reason: str) -> None:
    if replays:
        replays[0].setdefault("debug", {}).setdefault("eval_metrics", []).append(reason)


def _fallback_chain_exhausted(replay: dict[str, Any], side: str) -> bool:
    plays = replay.get("plays", [])
    if not plays:
        return False
    final_public = plays[-1].get("public", {})
    if final_public.get("terminal_reason") != "max_plays_reached":
        return False
    return any(
        bool(play.get("engine_internal", {}).get("validation_result", {}).get(side, {}).get("fallback_used"))
        for play in plays
    )


def resource_exhaustion_rate(replays: list[dict[str, Any]], side: str) -> float:
    _validate_side(side)
    if not replays:
        return 0.0
    exhausted = 0
    inspected = 0
    remaining_key = f"{side}_remaining"
    for replay in replays:
        plays = replay.get("plays", [])
        if not plays:
            _log_resource_gap(replays, "resource_exhaustion_rate unavailable: replay has no plays")
            return 0.0
        snapshot = plays[-1].get("engine_internal", {}).get("resource_budget_snapshot")
        if isinstance(snapshot, dict) and isinstance(snapshot.get(remaining_key), dict):
            inspected += 1
            if any(int(value) <= 0 for value in snapshot[remaining_key].values()):
                exhausted += 1
        elif _fallback_chain_exhausted(replay, side):
            inspected += 1
            exhausted += 1
        else:
            _log_resource_gap(replays, "resource_exhaustion_rate unavailable: missing resource budget snapshot")
            return 0.0
    return exhausted / inspected if inspected else 0.0


def paired_seed_lift(paired_runs: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [float(run["candidate_points"]) - float(run["baseline_points"]) for run in paired_runs]
    wins = sum(1 for delta in deltas if delta > 0)
    losses = sum(1 for delta in deltas if delta < 0)
    ties = sum(1 for delta in deltas if delta == 0)
    n = len(deltas)
    return {
        "mean": _mean(deltas),
        "win_rate": wins / n if n else 0.0,
        "n": n,
        "wins": wins,
        "losses": losses,
        "ties": ties,
    }


def bootstrap_ci_95(deltas: list[float], iterations: int = 1000, seed: int = 0) -> tuple[float, float]:
    if len(deltas) < 2 or iterations < 1:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(deltas)
    samples = sorted(
        sum(rng.choice(deltas) for _ in range(n)) / n
        for _ in range(iterations)
    )
    low_index = min(len(samples) - 1, max(0, int(iterations * 0.025)))
    high_index = min(len(samples) - 1, max(0, int(iterations * 0.975) - 1))
    return round(samples[low_index], 4), round(samples[high_index], 4)


def _traits_from_replay(replay: dict[str, Any]) -> MatchupTraits | None:
    payload = replay.get("agent_garage_config", {}).get("matchup_traits")
    if not isinstance(payload, dict):
        return None
    values = payload.get("values")
    if not isinstance(values, dict):
        return None
    return MatchupTraits(
        matchup_id=str(payload.get("matchup_id", "")),
        label=str(payload.get("label", "")),
        values={key: float(value) for key, value in values.items()},
        notes=str(payload.get("notes", "")),
    )


def calibration_summary(replays: list[dict[str, Any]]) -> dict[str, Any] | None:
    reports: list[dict[str, dict[str, Any]]] = []
    for replay in replays:
        traits = _traits_from_replay(replay)
        plays = replay.get("plays", [])
        if traits is None or not plays:
            continue
        last = plays[-1]
        offense_belief = last.get("offense_observed", {}).get("belief_after", {})
        defense_belief = last.get("defense_observed", {}).get("belief_after", {})
        reports.append({
            "offense": belief_calibration_error(traits, offense_belief),
            "defense": belief_calibration_error(traits, defense_belief),
        })
    if not reports:
        return None
    offense_reports = [report["offense"] for report in reports]
    defense_reports = [report["defense"] for report in reports]
    traits = offense_reports[0]["calibrated_traits"] if offense_reports else []
    return {
        "offense_mae": _mean([report["mean_absolute_error"] for report in offense_reports]),
        "defense_mae": _mean([report["mean_absolute_error"] for report in defense_reports]),
        "per_trait_offense_mae": {
            trait: _mean([report["per_trait_error"][trait] for report in offense_reports if trait in report["per_trait_error"]])
            for trait in traits
        },
        "per_trait_defense_mae": {
            trait: _mean([report["per_trait_error"][trait] for report in defense_reports if trait in report["per_trait_error"]])
            for trait in traits
        },
    }


def adaptation_lift_offense(by_case: dict[str, dict[str, Any]]) -> float:
    return round(float(by_case["b_oc_vs_a_dc"]["mean_points"]) - float(by_case["a_oc_vs_a_dc"]["mean_points"]), 4)


def suppression_lift_defense(by_case: dict[str, dict[str, Any]]) -> float:
    return round(float(by_case["a_oc_vs_a_dc"]["mean_points"]) - float(by_case["a_oc_vs_b_dc"]["mean_points"]), 4)


def sequencing_diversity_b_vs_b(replays_b_vs_b: list[dict[str, Any]]) -> float:
    pairs = [
        (
            play["public"]["offense_action"]["concept_family"],
            play["public"]["defense_action"]["coverage_family"],
        )
        for replay in replays_b_vs_b
        for play in replay.get("plays", [])
    ]
    return round(len(set(pairs)) / len(pairs), 4) if pairs else 0.0


def degenerate_strategy_flags(replays: list[dict[str, Any]], threshold: float = 0.7) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for side in ("offense", "defense"):
        for concept, frequency in concept_frequency(replays, side).items():
            rounded = round(frequency, 4)
            if rounded >= threshold:
                flags.append({"side": side, "concept": concept, "frequency": rounded})
    return flags


def canonical_report_hash(report: dict[str, Any], volatile_fields: set[str] | None = None) -> str:
    fields = volatile_fields or {"report_hash", "generated_at"}
    payload = {key: value for key, value in report.items() if key not in fields}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def suite_config_hash(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
