from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_mirrored_seed_report


def test_run_mirrored_seeds_outputs_valid_deterministic_report(tmp_path) -> None:
    first = tmp_path / "mirrored_a.json"
    second = tmp_path / "mirrored_b.json"
    command = [
        sys.executable,
        "scripts/run_mirrored_seeds.py",
        "--team-a",
        "data/teams/team_a_static_baseline.json",
        "--team-b",
        "data/teams/team_b_adaptive_counter.json",
        "--offense-roster",
        "data/rosters/balanced_v0.json",
        "--defense-roster",
        "data/rosters/balanced_v0.json",
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    validate_mirrored_seed_report(report)
    assert report["report_id"] == "mirrored_seed_v0"
    assert "roster_lift_offense" in report
    assert first.read_bytes() == second.read_bytes()
