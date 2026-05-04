from __future__ import annotations

import json
import subprocess
import sys


def test_run_gauntlet_validates_example_offense_deterministically(tmp_path) -> None:
    first = tmp_path / "gauntlet_a.json"
    second = tmp_path / "gauntlet_b.json"
    command = [
        sys.executable,
        "scripts/run_gauntlet.py",
        "--agent",
        "agents.example_agent.ExampleCustomOffense",
        "--side",
        "offense",
        "--seeds",
        "42,99,202",
        "--out",
    ]

    subprocess.run([*command, str(first)], check=True, timeout=30)
    subprocess.run([*command, str(second)], check=True, timeout=30)

    report = json.loads(first.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert len(report["opponents"]) == 3
    assert first.read_bytes() == second.read_bytes()
