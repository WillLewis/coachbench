from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_budget_leaderboard_report


def test_run_budget_leaderboard_outputs_sorted_deterministic_report(tmp_path) -> None:
    first = tmp_path / "leaderboard_a.json"
    second = tmp_path / "leaderboard_b.json"
    command = [
        sys.executable,
        "scripts/run_budget_leaderboard.py",
        "--teams",
        "data/teams/team_a_static_baseline.json,data/teams/team_b_adaptive_counter.json",
        "--rosters",
        "data/rosters/balanced_v0.json,data/rosters/pass_heavy_v0.json",
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    validate_budget_leaderboard_report(report)
    means = [row["mean_points_per_drive"] for row in report["standings"]]
    assert report["report_id"] == "budget_leaderboard_v0"
    assert len(report["entries"]) == 4
    assert means == sorted(means, reverse=True)
    assert first.read_bytes() == second.read_bytes()
