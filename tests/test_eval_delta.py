from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from coachbench.contracts import ContractValidationError, validate_eval_delta_report
from coachbench.eval_delta import (
    build_delta_report,
    classify_regression,
    compute_comparability,
    compute_gate_transitions,
    compute_metric_deltas,
    compute_per_opponent_deltas,
    delta_report_hash,
)


ROOT = Path(__file__).resolve().parents[1]


def _hex(char: str = "0") -> str:
    return char * 64


def _metrics(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "fallback_rate_candidate": 0.0,
        "fallback_rate_baseline": 0.0,
        "points_per_drive_candidate": 1.0,
        "points_per_drive_baseline": 1.0,
        "touchdown_rate_candidate": 0.2,
        "touchdown_rate_baseline": 0.2,
        "paired_seed_lift_mean": 0.0,
        "paired_seed_win_rate": 0.5,
        "bootstrap_ci_95": [-1.0, 1.0],
        "concept_frequency_candidate": {"quick_game": 1.0},
        "concept_entropy_candidate": 0.0,
        "resource_exhaustion_rate_candidate": 0.0,
        "calibration_summary": None,
    }
    values.update(overrides)
    return values


def _report(**overrides: Any) -> dict[str, Any]:
    report = {
        "schema_version": "eval_suite_report.v3",
        "suite_id": "smoke",
        "suite_config_hash": _hex("1"),
        "report_hash": _hex("2"),
        "locked": True,
        "candidates": [{"name": "AdaptiveOffense", "agent_path": "agents.adaptive_offense.AdaptiveOffense", "side": "offense", "locked": False}],
        "baseline": {"name": "StaticOffense", "agent_path": "agents.static_offense.StaticOffense", "side": "offense", "locked": True},
        "opponents": [{"name": "Static Defense", "agent_path": "agents.static_defense.StaticDefense", "side": "defense", "profile_id": None}],
        "seed_pack": {"name": "smoke", "seeds": [6]},
        "paired_runs": [{
            "seed": 6,
            "opponent": "static_defense_baseline",
            "candidate_replay_summary": {"points": 0, "result": "stopped", "plays": 1, "validation_failures": {"offense": 0, "defense": 0}},
            "baseline_replay_summary": {"points": 0, "result": "stopped", "plays": 1, "validation_failures": {"offense": 0, "defense": 0}},
            "lift": 0,
        }],
        "metrics": _metrics(),
        "per_opponent_metrics": {
            "static_defense_baseline": {
                "opponent_name": "Static Defense",
                "n_replays_candidate": 1,
                "n_replays_baseline": 1,
                **_metrics(),
            }
        },
        "gates": {
            "passed": ["fallback_rate_candidate=0.0 <= 0.0"],
            "failed": [],
            "warnings": [],
            "lift_strength": "none",
        },
        "warnings": [],
        "errors": [],
    }
    for key, value in overrides.items():
        if key == "metrics":
            report["metrics"] = _metrics(**value)
        else:
            report[key] = value
    return report


def _delta_report(**overrides: Any) -> dict[str, Any]:
    report = build_delta_report(_report(), _report())
    report.update(overrides)
    if "delta_hash" not in overrides:
        report["delta_hash"] = delta_report_hash(report)
    return report


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_delta(before: Path, after: Path, out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_eval_delta.py", "--before", str(before), "--after", str(after), "--out", str(out), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_compute_comparability_identical_reports_has_no_errors_or_warnings() -> None:
    comp = compute_comparability(_report(), _report())
    assert comp["errors"] == []
    assert comp["warnings"] == []


def test_compute_comparability_schema_version_mismatch_errors() -> None:
    before = _report()
    after = _report(schema_version="eval_suite_report.v2")
    assert compute_comparability(before, after)["errors"]


def test_compute_comparability_suite_id_mismatch_errors() -> None:
    assert compute_comparability(_report(), _report(suite_id="exploit"))["errors"]


def test_compute_comparability_seed_pack_mismatch_errors() -> None:
    after = _report(seed_pack={"name": "standard", "seeds": [6]})
    assert compute_comparability(_report(), after)["errors"]


def test_compute_comparability_candidate_name_change_warns_not_errors() -> None:
    after = _report(candidates=[{"name": "Other", "agent_path": "x", "side": "offense", "locked": False}])
    comp = compute_comparability(_report(), after)
    assert comp["errors"] == []
    assert comp["warnings"]


def test_compute_comparability_locked_mode_change_warns() -> None:
    comp = compute_comparability(_report(), _report(locked=False))
    assert comp["errors"] == []
    assert comp["warnings"]


def test_compute_metric_deltas_simple_floats() -> None:
    deltas = compute_metric_deltas({"a": 1.0}, {"a": 2.5})
    assert deltas["a"] == {"before": 1.0, "after": 2.5, "delta": 1.5}


def test_compute_metric_deltas_bootstrap_ci_two_components() -> None:
    deltas = compute_metric_deltas({"bootstrap_ci_95": [0.0, 1.0]}, {"bootstrap_ci_95": [0.5, 2.0]})
    assert deltas["bootstrap_ci_95"]["delta_low"] == 0.5
    assert deltas["bootstrap_ci_95"]["delta_high"] == 1.0


def test_compute_metric_deltas_concept_frequency_added_and_removed() -> None:
    deltas = compute_metric_deltas(
        {"concept_frequency_candidate": {"quick_game": 0.7, "screen": 0.3}},
        {"concept_frequency_candidate": {"quick_game": 0.4, "rpo_glance": 0.6}},
    )
    freq = deltas["concept_frequency_candidate"]
    assert freq["added_concepts"] == ["rpo_glance"]
    assert freq["removed_concepts"] == ["screen"]
    assert freq["changed_concepts"]["quick_game"]["delta"] == -0.29999999999999993


def test_compute_metric_deltas_calibration_summary_null_pass_through() -> None:
    delta = compute_metric_deltas({"calibration_summary": None}, {"calibration_summary": {"offense_mae": 0.1}})
    assert delta["calibration_summary"]["delta"] is None


def test_compute_per_opponent_deltas_added_opponent_listed() -> None:
    delta = compute_per_opponent_deltas({}, {"new": _metrics()})
    assert delta["added_opponents"] == ["new"]


def test_compute_per_opponent_deltas_removed_opponent_listed() -> None:
    delta = compute_per_opponent_deltas({"old": _metrics()}, {})
    assert delta["removed_opponents"] == ["old"]


def test_compute_per_opponent_deltas_per_opponent_metric_drilldown() -> None:
    delta = compute_per_opponent_deltas({"x": _metrics(points_per_drive_candidate=1.0)}, {"x": _metrics(points_per_drive_candidate=2.0)})
    assert delta["opponents"]["x"]["points_per_drive_candidate"]["delta"] == 1.0


def test_compute_gate_transitions_lift_strength_improvement() -> None:
    delta = compute_gate_transitions({"lift_strength": "none"}, {"lift_strength": "confirmed"})
    assert delta["lift_strength"]["direction"] == "improvement"


def test_compute_gate_transitions_lift_strength_regression() -> None:
    delta = compute_gate_transitions({"lift_strength": "strong"}, {"lift_strength": "confirmed"})
    assert delta["lift_strength"]["direction"] == "regression"


def test_compute_gate_transitions_passed_now_failed() -> None:
    delta = compute_gate_transitions(
        {"passed": ["fallback_rate_candidate=0.0 <= 0.01"], "failed": [], "warnings": [], "lift_strength": "none"},
        {"passed": [], "failed": ["fallback_rate_candidate=0.1 > 0.01"], "warnings": [], "lift_strength": "none"},
    )
    assert delta["passed_now_failed"] == ["fallback_rate_candidate=0.1 > 0.01"]


def test_compute_gate_transitions_warning_now_clear() -> None:
    delta = compute_gate_transitions(
        {"passed": [], "failed": [], "warnings": ["concept_top1 high"], "lift_strength": "none"},
        {"passed": [], "failed": [], "warnings": [], "lift_strength": "none"},
    )
    assert delta["warning_now_clear"] == ["concept_top1 high"]


def test_classify_regression_no_changes_returns_false() -> None:
    assert classify_regression(build_delta_report(_report(), _report()))["is_regression"] is False


def test_classify_regression_fallback_rate_increase_triggers() -> None:
    report = build_delta_report(_report(), _report(metrics={"fallback_rate_candidate": 0.02}))
    assert report["regression"]["is_regression"] is True
    assert any("fallback_rate_candidate increased" in reason for reason in report["regression"]["reasons"])


def test_classify_regression_lift_weakened_triggers() -> None:
    before = _report(gates={"passed": [], "failed": [], "warnings": [], "lift_strength": "confirmed"})
    after = _report(gates={"passed": [], "failed": [], "warnings": [], "lift_strength": "none"})
    report = build_delta_report(before, after)
    assert any("lift_strength weakened" in reason for reason in report["regression"]["reasons"])


def test_classify_regression_passed_now_failed_triggers() -> None:
    after = _report(gates={"passed": [], "failed": ["fallback_rate_candidate=0.1 > 0.01"], "warnings": [], "lift_strength": "none"})
    report = build_delta_report(_report(), after)
    assert any("gate passed_now_failed" in reason for reason in report["regression"]["reasons"])


def test_classify_regression_comparability_error_triggers() -> None:
    report = build_delta_report(_report(), _report(suite_id="exploit"))
    assert any("comparability error" in reason for reason in report["regression"]["reasons"])


def test_classify_regression_paired_lift_mean_decrease_triggers() -> None:
    report = build_delta_report(_report(metrics={"paired_seed_lift_mean": 1.0}), _report(metrics={"paired_seed_lift_mean": 0.0}))
    assert any("paired_seed_lift_mean decreased" in reason for reason in report["regression"]["reasons"])


def test_build_delta_report_round_trip() -> None:
    validate_eval_delta_report(build_delta_report(_report(), _report()))


def test_delta_report_hash_excludes_volatile_fields() -> None:
    first = build_delta_report(_report(), _report())
    second = dict(first)
    second["generated_at"] = "different"
    second["delta_hash"] = _hex("f")
    assert delta_report_hash(first) == delta_report_hash(second)


def test_validate_eval_delta_report_rejects_wrong_schema_version() -> None:
    report = _delta_report(schema_version="bad")
    with pytest.raises(ContractValidationError, match="schema_version"):
        validate_eval_delta_report(report)


def test_validate_eval_delta_report_rejects_invalid_hash() -> None:
    report = _delta_report(delta_hash="bad")
    with pytest.raises(ContractValidationError, match="delta_hash"):
        validate_eval_delta_report(report)


def test_validate_eval_delta_report_rejects_missing_regression_field() -> None:
    report = _delta_report()
    del report["regression"]
    with pytest.raises(ContractValidationError, match="missing fields"):
        validate_eval_delta_report(report)


def test_validate_eval_delta_report_accepts_well_formed() -> None:
    validate_eval_delta_report(_delta_report())


def test_runner_writes_valid_delta_report(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    out = tmp_path / "delta.json"
    _write(before, _report())
    _write(after, _report())
    result = _run_delta(before, after, out)
    assert result.returncode == 0, result.stderr
    validate_eval_delta_report(json.loads(out.read_text(encoding="utf-8")))


def test_runner_self_diff_is_no_regression(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    out = tmp_path / "delta.json"
    payload = _report()
    _write(before, payload)
    _write(after, payload)
    result = _run_delta(before, after, out)
    assert result.returncode == 0
    assert json.loads(out.read_text(encoding="utf-8"))["regression"]["is_regression"] is False


def test_runner_fail_on_regression_exits_nonzero_on_regression(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    out = tmp_path / "delta.json"
    _write(before, _report(metrics={"paired_seed_lift_mean": 1.0}))
    _write(after, _report(metrics={"paired_seed_lift_mean": 0.0}))
    result = _run_delta(before, after, out, "--fail-on", "regression")
    assert result.returncode == 1
    assert "paired_seed_lift_mean" in result.stderr


def test_runner_fail_on_never_exits_zero_even_on_regression(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    out = tmp_path / "delta.json"
    _write(before, _report(metrics={"paired_seed_lift_mean": 1.0}))
    _write(after, _report(metrics={"paired_seed_lift_mean": 0.0}))
    assert _run_delta(before, after, out, "--fail-on", "never").returncode == 0


def test_runner_rejects_invalid_before_report(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    out = tmp_path / "delta.json"
    before.write_text("{not-json", encoding="utf-8")
    _write(after, _report())
    result = _run_delta(before, after, out)
    assert result.returncode != 0
    assert "could not load report" in result.stderr


def test_runner_delta_hash_deterministic(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    first = tmp_path / "delta_a.json"
    second = tmp_path / "delta_b.json"
    _write(before, _report())
    _write(after, _report())
    assert _run_delta(before, after, first).returncode == 0
    assert _run_delta(before, after, second).returncode == 0
    assert json.loads(first.read_text(encoding="utf-8"))["delta_hash"] == json.loads(second.read_text(encoding="utf-8"))["delta_hash"]
