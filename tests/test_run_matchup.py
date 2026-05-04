from __future__ import annotations

import json
import subprocess
import sys

from coachbench.contracts import validate_replay_contract


def test_run_matchup_outputs_valid_deterministic_replay(tmp_path) -> None:
    first = tmp_path / "matchup_a.json"
    second = tmp_path / "matchup_b.json"
    command = [
        sys.executable,
        "scripts/run_matchup.py",
        "--team-a",
        "data/teams/team_a_static_baseline.json",
        "--team-b",
        "data/teams/team_b_adaptive_counter.json",
        "--seed",
        "42",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    replay = json.loads(first.read_text(encoding="utf-8"))
    validate_replay_contract(replay)
    assert replay["agent_garage_config"]["team_a_id"] == "team_a_static_baseline"
    assert replay["agent_garage_config"]["team_b_id"] == "team_b_adaptive_counter"
    assert first.read_bytes() == second.read_bytes()
