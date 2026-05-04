from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from coachbench.contracts import validate_tournament_report


def test_run_tournament_outputs_sorted_deterministic_standings(tmp_path) -> None:
    team_copy = tmp_path / "team_a_copy.json"
    payload = json.loads(Path("data/teams/team_a_static_baseline.json").read_text(encoding="utf-8"))
    payload["team_id"] = "team_a_static_copy"
    payload["label"] = "Team A Static Copy"
    team_copy.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    first = tmp_path / "tournament_a.json"
    second = tmp_path / "tournament_b.json"
    teams = ",".join([
        "data/teams/team_a_static_baseline.json",
        str(team_copy),
        "data/teams/team_b_adaptive_counter.json",
    ])
    command = [
        sys.executable,
        "scripts/run_tournament.py",
        "--teams",
        teams,
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    validate_tournament_report(report)
    means = [row["mean_points_per_drive"] for row in report["standings"]]
    assert report["report_id"] == "tournament_v0"
    assert means == sorted(means, reverse=True)
    assert first.read_bytes() == second.read_bytes()
