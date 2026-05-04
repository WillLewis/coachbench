from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_baseline_comparison_report_has_not_drifted(tmp_path) -> None:
    """Re-run the baseline comparison command and compare with the committed artifact."""

    actual = tmp_path / "comparison_report.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_comparison_report.py",
            "--team-a",
            "data/teams/team_a_static_baseline.json",
            "--team-b",
            "data/teams/team_b_adaptive_counter.json",
            "--seeds",
            "42,99,202,311,404,515,628,733,841,956,1063",
            "--out",
            str(actual),
        ],
        check=True,
        timeout=30,
    )

    expected = json.loads(Path("data/baseline/comparison_report.json").read_text(encoding="utf-8"))
    generated = json.loads(actual.read_text(encoding="utf-8"))
    assert generated == expected, (
        "Baseline comparison report drift. Re-run the command in the docstring; "
        "if the change is intentional, commit the new baseline."
    )
