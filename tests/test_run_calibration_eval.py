from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_calibration_eval_report


def test_run_calibration_eval_outputs_valid_deterministic_report(tmp_path) -> None:
    first = tmp_path / "cal_a.json"
    second = tmp_path / "cal_b.json"
    command = [
        sys.executable,
        "scripts/run_calibration_eval.py",
        "--team-a",
        "data/teams/team_a_static_baseline.json",
        "--team-b",
        "data/teams/team_b_adaptive_counter.json",
        "--matchup-traits",
        "data/matchup_traits/neutral_v0.json",
        "--offense-scouting",
        "data/scouting_reports/neutral_fresh_complete.json",
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    validate_calibration_eval_report(report)
    assert report["with_scouting"]["offense_mae"] >= 0
    assert report["with_scouting"]["defense_mae"] >= 0
    assert report["with_scouting"]["offense_mae"] == report["without_scouting"]["offense_mae"]
    assert report["with_scouting"]["defense_mae"] == report["without_scouting"]["defense_mae"]
    assert first.read_bytes() == second.read_bytes()
