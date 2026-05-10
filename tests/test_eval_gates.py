from __future__ import annotations

import json

from coachbench.eval_gates import evaluate_gates, lift_strength


def _report(
    *,
    candidate_fallback: float = 0.0,
    baseline_fallback: float = 0.0,
    per_candidate_fallback: float = 0.0,
    per_baseline_fallback: float = 0.0,
    concept_frequency: dict[str, float] | None = None,
    entropy: float = 2.0,
    resource_exhaustion: float = 0.0,
    errors: list[str] | None = None,
) -> dict:
    return {
        "metrics": {
            "fallback_rate_candidate": candidate_fallback,
            "fallback_rate_baseline": baseline_fallback,
            "paired_seed_win_rate": 0.0,
            "bootstrap_ci_95": [-1.0, 1.0],
            "resource_exhaustion_rate_candidate": resource_exhaustion,
        },
        "per_opponent_metrics": {
            "coverage_shell_conservative": {
                "fallback_rate_candidate": per_candidate_fallback,
                "fallback_rate_baseline": per_baseline_fallback,
                "concept_frequency_candidate": concept_frequency or {"x": 0.34, "y": 0.33, "z": 0.33},
                "concept_entropy_candidate": entropy,
            }
        },
        "errors": errors or [],
    }


def test_lift_strength_none_when_win_rate_below_0_8() -> None:
    assert lift_strength({"paired_seed_win_rate": 0.79, "bootstrap_ci_95": [1.0, 2.0]}) == "none"


def test_lift_strength_confirmed_when_win_rate_at_0_8() -> None:
    assert lift_strength({"paired_seed_win_rate": 0.8, "bootstrap_ci_95": [-0.1, 2.0]}) == "confirmed"


def test_lift_strength_strong_requires_ci_above_zero() -> None:
    assert lift_strength({"paired_seed_win_rate": 0.85, "bootstrap_ci_95": [-0.1, 5.0]}) == "confirmed"


def test_lift_strength_strong_when_win_rate_high_and_ci_positive() -> None:
    assert lift_strength({"paired_seed_win_rate": 0.85, "bootstrap_ci_95": [0.1, 5.0]}) == "strong"


def test_evaluate_gates_smoke_zero_fallback_passes() -> None:
    result = evaluate_gates(_report(), "smoke")
    assert result["failed"] == []
    assert any("fallback_rate_candidate=0.0 <= 0.0" in item for item in result["passed"])


def test_evaluate_gates_smoke_any_fallback_fails() -> None:
    result = evaluate_gates(_report(candidate_fallback=0.001), "smoke")
    assert any("fallback_rate_candidate=0.001 > 0.0" in item for item in result["failed"])


def test_evaluate_gates_standard_below_threshold_passes() -> None:
    result = evaluate_gates(_report(candidate_fallback=0.009, per_candidate_fallback=0.009), "standard")
    assert result["failed"] == []


def test_evaluate_gates_standard_above_threshold_fails() -> None:
    result = evaluate_gates(_report(candidate_fallback=0.011), "standard")
    assert any("fallback_rate_candidate=0.011 > 0.01" in item for item in result["failed"])


def test_evaluate_gates_concept_top1_warning() -> None:
    result = evaluate_gates(_report(concept_frequency={"x": 0.45, "y": 0.30, "z": 0.25}), "standard")
    assert any("x" in item and "opponent=coverage_shell_conservative" in item for item in result["warnings"])


def test_evaluate_gates_entropy_warning() -> None:
    result = evaluate_gates(_report(entropy=1.0), "standard")
    assert any("concept_entropy_candidate=1.0 < 1.5" in item for item in result["warnings"])


def test_evaluate_gates_resource_exhaustion_warning() -> None:
    result = evaluate_gates(_report(resource_exhaustion=0.11), "standard")
    assert any("resource_exhaustion_rate_candidate=0.11 > 0.1" in item for item in result["warnings"])


def test_evaluate_gates_propagates_existing_errors() -> None:
    result = evaluate_gates(_report(errors=["bad action"]), "standard")
    assert "errors=1 > 0" in result["failed"]


def test_evaluate_gates_returns_dict_does_not_mutate_input() -> None:
    report = _report()
    before = json.dumps(report, sort_keys=True)
    result = evaluate_gates(report, "standard")
    after = json.dumps(report, sort_keys=True)
    assert set(result) == {"passed", "failed", "warnings", "lift_strength"}
    assert before == after
