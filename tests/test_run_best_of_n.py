from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_best_of_n_report


def test_run_best_of_n_outputs_valid_deterministic_report(tmp_path) -> None:
    first = tmp_path / "best_a.json"
    second = tmp_path / "best_b.json"
    command = [
        sys.executable,
        "scripts/run_best_of_n.py",
        "--team-a",
        "data/teams/team_a_static_baseline.json",
        "--team-b",
        "data/teams/team_b_adaptive_counter.json",
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    validate_best_of_n_report(report)
    assert report["report_id"] == "best_of_n_v0"
    assert report["team_a"]["games_played"] == 3
    assert report["team_b"]["games_played"] == 3
    assert first.read_bytes() == second.read_bytes()
