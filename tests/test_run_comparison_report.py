from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_comparison_report


def test_run_comparison_report_outputs_valid_deterministic_report(tmp_path) -> None:
    first = tmp_path / "comparison_a.json"
    second = tmp_path / "comparison_b.json"
    command = [
        sys.executable,
        "scripts/run_comparison_report.py",
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
    validate_comparison_report(report)
    assert set(report["answers"]) == {
        "adaptive_offense_outperforms_static_offense",
        "adaptive_defense_suppresses_static_offense",
        "adaptive_vs_adaptive_has_nontrivial_sequencing",
        "graph_creates_no_obvious_degeneracies",
    }
    assert first.read_bytes() == second.read_bytes()
