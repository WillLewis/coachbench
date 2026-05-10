from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from coachbench.contracts import ContractValidationError, validate_eval_suite_report


ROOT = Path(__file__).resolve().parents[1]


def _run_suite(*args: str, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_eval_suite.py", *args, "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _run_ok(*args: str, out: Path) -> dict:
    result = _run_suite(*args, out=out)
    assert result.returncode == 0, result.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def _hex() -> str:
    return "0" * 64


def _well_formed_report() -> dict:
    return {
        "schema_version": "eval_suite_report.v3",
        "suite_id": "smoke",
        "suite_config_hash": _hex(),
        "report_hash": _hex(),
        "locked": True,
        "candidates": [{"name": "Candidate", "agent_path": "agents.adaptive_offense.AdaptiveOffense", "side": "offense", "locked": False}],
        "baseline": {"name": "Baseline", "agent_path": "agents.static_offense.StaticOffense", "side": "offense", "locked": True},
        "opponents": [{"name": "Opponent", "agent_path": "agents.static_defense.StaticDefense", "side": "defense", "profile_id": None}],
        "seed_pack": {"name": "smoke", "seeds": [6]},
        "paired_runs": [{
            "seed": 6,
            "opponent": "static_defense_baseline",
            "candidate_replay_summary": {"points": 0, "result": "stopped", "plays": 1, "validation_failures": {"offense": 0, "defense": 0}},
            "baseline_replay_summary": {"points": 7, "result": "touchdown", "plays": 1, "validation_failures": {"offense": 0, "defense": 0}},
            "lift": -7,
        }],
        "metrics": {
            "fallback_rate_candidate": 0.0,
            "fallback_rate_baseline": 0.0,
            "points_per_drive_candidate": 0.0,
            "points_per_drive_baseline": 7.0,
            "touchdown_rate_candidate": 0.0,
            "touchdown_rate_baseline": 1.0,
            "paired_seed_lift_mean": -7.0,
            "paired_seed_win_rate": 0.0,
            "bootstrap_ci_95": [0.0, 0.0],
            "concept_frequency_candidate": {"quick_game": 1.0},
            "concept_entropy_candidate": 0.0,
            "resource_exhaustion_rate_candidate": 0.0,
            "calibration_summary": None,
        },
        "per_opponent_metrics": {
            "static_defense_baseline": {
                "opponent_name": "Opponent",
                "n_replays_candidate": 1,
                "n_replays_baseline": 1,
                "fallback_rate_candidate": 0.0,
                "fallback_rate_baseline": 0.0,
                "points_per_drive_candidate": 0.0,
                "points_per_drive_baseline": 7.0,
                "touchdown_rate_candidate": 0.0,
                "touchdown_rate_baseline": 1.0,
                "paired_seed_lift_mean": -7.0,
                "paired_seed_win_rate": 0.0,
                "bootstrap_ci_95": [0.0, 0.0],
                "concept_frequency_candidate": {"quick_game": 1.0},
                "concept_entropy_candidate": 0.0,
            }
        },
        "gates": {"passed": [], "failed": [], "warnings": [], "lift_strength": "none"},
        "warnings": [],
        "errors": [],
    }


def test_smoke_suite_locked_by_default_runs(tmp_path: Path) -> None:
    report = _run_ok("--suite", "smoke", out=tmp_path / "smoke.json")
    assert report["locked"] is True
    validate_eval_suite_report(report)


def test_smoke_suite_no_locked_runs(tmp_path: Path) -> None:
    report = _run_ok("--suite", "smoke", "--no-locked", out=tmp_path / "smoke_unlocked.json")
    assert report["locked"] is False
    validate_eval_suite_report(report)


def test_locked_suite_rejects_network_agent(tmp_path: Path) -> None:
    result = _run_suite(
        "--suite",
        "smoke",
        "--candidate",
        "tests.fixtures.agents.network_agent.NetworkAgent",
        out=tmp_path / "locked_reject.json",
    )
    assert result.returncode != 0
    assert "LockedEvalViolation" in result.stderr


def test_no_locked_run_accepts_network_agent(tmp_path: Path) -> None:
    report = _run_ok(
        "--suite",
        "smoke",
        "--candidate",
        "tests.fixtures.agents.network_agent.NetworkAgent",
        "--no-locked",
        out=tmp_path / "unlocked_accept.json",
    )
    assert report["locked"] is False


def test_exploit_suite_runs_end_to_end(tmp_path: Path) -> None:
    report = _run_ok("--suite", "exploit", out=tmp_path / "exploit.json")
    assert report["schema_version"] == "eval_suite_report.v3"
    assert "exploit_probe_defense_baseline" in report["per_opponent_metrics"]
    validate_eval_suite_report(report)


def test_exploit_suite_report_hash_deterministic(tmp_path: Path) -> None:
    first = _run_ok("--suite", "exploit", out=tmp_path / "exploit_a.json")
    second = _run_ok("--suite", "exploit", out=tmp_path / "exploit_b.json")
    assert first["report_hash"] == second["report_hash"]


def test_v3_validator_rejects_v2_schema_version() -> None:
    report = _well_formed_report()
    report["schema_version"] = "eval_suite_report.v2"
    with pytest.raises(ContractValidationError, match="Phase 2 reports are no longer accepted"):
        validate_eval_suite_report(report)


def test_v3_validator_rejects_missing_locked_field() -> None:
    report = _well_formed_report()
    del report["locked"]
    with pytest.raises(ContractValidationError, match="missing fields"):
        validate_eval_suite_report(report)


def test_v3_validator_accepts_well_formed_v3() -> None:
    validate_eval_suite_report(_well_formed_report())


def test_v3_validator_accepts_exploit_suite_id() -> None:
    report = _well_formed_report()
    report["suite_id"] = "exploit"
    validate_eval_suite_report(report)
