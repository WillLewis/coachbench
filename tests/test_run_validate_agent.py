from __future__ import annotations

import json
import subprocess
import sys


def test_validate_agent_accepts_example_offense(tmp_path) -> None:
    report = tmp_path / "validator.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_agent.py",
            "--agent",
            "agents.example_agent.ExampleCustomOffense",
            "--side",
            "offense",
            "--seeds",
            "42,99,202",
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "Validation passed" in result.stdout


def test_validate_agent_rejects_illegal_concept() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_agent.py",
            "--agent",
            "tests.fixtures.phase3_agents.IllegalConceptOffense",
            "--side",
            "offense",
            "--seeds",
            "42",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "V1 failure" in result.stderr
    assert "illegal offense concept" in result.stderr


def test_validate_agent_detects_observation_mutation_hidden_field() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_agent.py",
            "--agent",
            "tests.fixtures.phase3_agents.MutatingLeakyOffense",
            "--side",
            "offense",
            "--seeds",
            "42",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "V3 failure" in result.stderr
    assert "hidden fields" in result.stderr
