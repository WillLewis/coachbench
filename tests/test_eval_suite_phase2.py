from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from coachbench.contracts import ContractValidationError, validate_eval_suite_report


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


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
        "locked": False,
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


def test_seed_pack_files_exist_and_are_valid() -> None:
    expected = {"smoke": 5, "standard": 64, "extended": 256}
    names = []
    for name, count in expected.items():
        payload = _load(f"data/eval/seed_packs/{name}.json")
        names.append(payload["name"])
        assert len(payload["seeds"]) == count
        assert all(isinstance(seed, int) for seed in payload["seeds"])
        assert len(set(payload["seeds"])) == count
    assert len(set(names)) == len(expected)


def test_opponent_suite_files_exist_and_are_valid() -> None:
    for path, side in (
        ("data/eval/opponent_suites/garage_defense_v1.json", "defense"),
        ("data/eval/opponent_suites/garage_offense_v1.json", "offense"),
    ):
        payload = _load(path)
        assert payload["schema_version"] == "eval_opponent_suite.v1"
        assert payload["side"] == side
        assert len(payload["opponents"]) == 5


def test_opponent_suite_profile_ids_resolve() -> None:
    profiles = _load("agent_garage/profiles.json")
    for path in ("data/eval/opponent_suites/garage_defense_v1.json", "data/eval/opponent_suites/garage_offense_v1.json"):
        payload = _load(path)
        archetypes = profiles[f"{payload['side']}_archetypes"]
        for opponent in payload["opponents"]:
            if opponent["profile_id"] is not None:
                assert opponent["profile_id"] in archetypes


def test_suite_config_files_exist_and_are_valid() -> None:
    for name in ("smoke", "standard", "extended"):
        payload = _load(f"data/eval/suites/{name}.json")
        assert payload["schema_version"] == "eval_suite_config.v1"
        assert payload["name"] == name
        assert payload["candidate"]["side"] == "offense"
        assert payload["baseline"]["side"] == "offense"
        assert set(payload["gates"]) == {
            "fallback_rate_max",
            "concept_top1_warn_above",
            "concept_entropy_warn_below",
            "resource_exhaustion_warn_above",
        }


def test_smoke_suite_runs_via_new_path(tmp_path: Path) -> None:
    report = _run_ok("--suite", "smoke", out=tmp_path / "smoke.json")
    assert report["schema_version"] == "eval_suite_report.v3"
    assert "gates" in report
    validate_eval_suite_report(report)


def test_smoke_suite_report_hash_deterministic_v2(tmp_path: Path) -> None:
    first = _run_ok("--suite", "smoke", out=tmp_path / "smoke_a.json")
    second = _run_ok("--suite", "smoke", out=tmp_path / "smoke_b.json")
    assert first["report_hash"] == second["report_hash"]


def test_standard_suite_runs_end_to_end(tmp_path: Path) -> None:
    report = _run_ok("--suite", "standard", out=tmp_path / "standard.json")
    assert len(report["per_opponent_metrics"]) == 5
    validate_eval_suite_report(report)


def test_standard_suite_paired_runs_length(tmp_path: Path) -> None:
    report = _run_ok("--suite", "standard", out=tmp_path / "standard.json")
    assert len(report["paired_runs"]) == 64 * 5


def test_standard_suite_report_hash_deterministic(tmp_path: Path) -> None:
    first = _run_ok("--suite", "standard", out=tmp_path / "standard_a.json")
    second = _run_ok("--suite", "standard", out=tmp_path / "standard_b.json")
    assert first["report_hash"] == second["report_hash"]


def test_extended_suite_runs_end_to_end(tmp_path: Path) -> None:
    report = _run_ok("--suite", "extended", out=tmp_path / "extended.json")
    assert len(report["paired_runs"]) == 256 * 5
    validate_eval_suite_report(report)


def test_defense_side_evaluation_runs(tmp_path: Path) -> None:
    report = _run_ok("--suite", "standard", "--side", "defense", out=tmp_path / "standard_defense.json")
    assert report["candidates"][0]["side"] == "defense"
    assert len(report["per_opponent_metrics"]) == 5


def test_v2_validator_rejects_v1_schema_version() -> None:
    report = _well_formed_report()
    report["schema_version"] = "eval_suite_report.v2"
    with pytest.raises(ContractValidationError, match="Phase 2 reports are no longer accepted"):
        validate_eval_suite_report(report)


def test_v2_validator_rejects_missing_gates_field() -> None:
    report = _well_formed_report()
    del report["gates"]
    with pytest.raises(ContractValidationError, match="missing fields"):
        validate_eval_suite_report(report)


def test_v2_validator_accepts_well_formed_v2() -> None:
    validate_eval_suite_report(_well_formed_report())


def test_fail_on_error_exits_nonzero_when_gates_failed(tmp_path: Path) -> None:
    out = tmp_path / "bad.json"
    result = _run_suite(
        "--suite",
        "smoke",
        "--candidate",
        "tests.fixtures.phase3_agents.IllegalConceptOffense",
        "--fail-on",
        "error",
        out=out,
    )
    assert result.returncode != 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["gates"]["failed"]


def test_fail_on_warning_exits_nonzero_when_warnings_present(tmp_path: Path) -> None:
    out = tmp_path / "warning.json"
    result = _run_suite("--suite", "smoke", "--fail-on", "warning", out=out)
    assert result.returncode != 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["gates"]["warnings"]


def test_fail_on_never_exits_zero_even_with_failures(tmp_path: Path) -> None:
    out = tmp_path / "bad_never.json"
    result = _run_suite(
        "--suite",
        "smoke",
        "--candidate",
        "tests.fixtures.phase3_agents.IllegalConceptOffense",
        "--fail-on",
        "never",
        out=out,
    )
    assert result.returncode == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["gates"]["failed"]


def test_smoke_suite_skips_opponent_suite(tmp_path: Path) -> None:
    report = _run_ok("--suite", "smoke", out=tmp_path / "smoke.json")
    assert list(report["per_opponent_metrics"]) == ["static_defense_baseline"]
