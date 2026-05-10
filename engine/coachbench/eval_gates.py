from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "smoke": {"fallback_rate_max": 0.0, "concept_top1_warn_above": 0.40, "concept_entropy_warn_below": 1.5, "resource_exhaustion_warn_above": 0.20},
    "standard": {"fallback_rate_max": 0.01, "concept_top1_warn_above": 0.40, "concept_entropy_warn_below": 1.5, "resource_exhaustion_warn_above": 0.10},
    "extended": {"fallback_rate_max": 0.001, "concept_top1_warn_above": 0.40, "concept_entropy_warn_below": 1.5, "resource_exhaustion_warn_above": 0.05},
}


def lift_strength(metrics: dict[str, Any]) -> str:
    win_rate = float(metrics.get("paired_seed_win_rate", 0.0))
    ci = metrics.get("bootstrap_ci_95", [0.0, 0.0])
    ci_low = float(ci[0]) if isinstance(ci, list) and ci else 0.0
    if win_rate >= 0.8 and ci_low > 0:
        return "strong"
    if win_rate >= 0.8:
        return "confirmed"
    return "none"


def _thresholds(suite_id: str, thresholds: dict[str, float] | None) -> dict[str, float]:
    values = dict(DEFAULT_THRESHOLDS[suite_id])
    if thresholds:
        values.update({key: float(value) for key, value in thresholds.items()})
    return values


def _check_fallback(
    *,
    label: str,
    value: float,
    threshold: float,
    passed: list[str],
    failed: list[str],
    suffix: str = "",
) -> None:
    message = f"{label}={value} {'<=' if value <= threshold else '>'} {threshold}{suffix}"
    if value > threshold:
        failed.append(message)
    else:
        passed.append(message)


def evaluate_gates(
    report: dict[str, Any],
    suite_id: str,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    active = _thresholds(suite_id, thresholds)
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    metrics = report.get("metrics", {})

    for key in ("fallback_rate_candidate", "fallback_rate_baseline"):
        _check_fallback(
            label=key,
            value=float(metrics.get(key, 0.0)),
            threshold=active["fallback_rate_max"],
            passed=passed,
            failed=failed,
        )

    for slug, opponent_metrics in sorted(report.get("per_opponent_metrics", {}).items()):
        suffix = f" (opponent={slug})"
        for key in ("fallback_rate_candidate", "fallback_rate_baseline"):
            _check_fallback(
                label=key,
                value=float(opponent_metrics.get(key, 0.0)),
                threshold=active["fallback_rate_max"],
                passed=passed,
                failed=failed,
                suffix=suffix,
            )

        frequency = opponent_metrics.get("concept_frequency_candidate", {})
        if frequency:
            concept, top_frequency = sorted(
                ((str(concept), float(value)) for concept, value in frequency.items()),
                key=lambda item: (-item[1], item[0]),
            )[0]
            if top_frequency > active["concept_top1_warn_above"]:
                warnings.append(
                    f"concept_top1={round(top_frequency, 4)} > {active['concept_top1_warn_above']} "
                    f"({concept}, candidate, opponent={slug})"
                )
            else:
                passed.append(
                    f"concept_top1={round(top_frequency, 4)} <= {active['concept_top1_warn_above']} "
                    f"(candidate, opponent={slug})"
                )

        entropy = float(opponent_metrics.get("concept_entropy_candidate", 0.0))
        if entropy < active["concept_entropy_warn_below"]:
            warnings.append(
                f"concept_entropy_candidate={entropy} < {active['concept_entropy_warn_below']} "
                f"(candidate, opponent={slug})"
            )
        else:
            passed.append(
                f"concept_entropy_candidate={entropy} >= {active['concept_entropy_warn_below']} "
                f"(candidate, opponent={slug})"
            )

    resource_rate = float(metrics.get("resource_exhaustion_rate_candidate", 0.0))
    if resource_rate > active["resource_exhaustion_warn_above"]:
        warnings.append(f"resource_exhaustion_rate_candidate={resource_rate} > {active['resource_exhaustion_warn_above']}")
    else:
        passed.append(f"resource_exhaustion_rate_candidate={resource_rate} <= {active['resource_exhaustion_warn_above']}")

    errors = report.get("errors", [])
    if errors:
        failed.append(f"errors={len(errors)} > 0")
    else:
        passed.append("errors=0")

    return {
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "lift_strength": lift_strength(metrics),
    }
