from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from coachbench.contracts import (
    validate_daily_slate_report,
    validate_match_matrix_report,
    validate_replay_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def _run_script(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True, capture_output=True, text=True)


def _assert_same_json(left: Path, right: Path) -> dict:
    assert left.read_text(encoding="utf-8") == right.read_text(encoding="utf-8")
    return json.loads(left.read_text(encoding="utf-8"))


def test_showcase_script_output_is_deterministic_and_contract_valid(tmp_path: Path) -> None:
    first = tmp_path / "showcase_a.json"
    second = tmp_path / "showcase_b.json"

    _run_script("scripts/run_showcase.py", "--seed", "42", "--out", str(first))
    _run_script("scripts/run_showcase.py", "--seed", "42", "--out", str(second))

    replay = _assert_same_json(first, second)
    validate_replay_contract(replay)


def test_match_matrix_script_output_is_deterministic_and_contract_valid(tmp_path: Path) -> None:
    first = tmp_path / "matrix_a.json"
    second = tmp_path / "matrix_b.json"

    _run_script("scripts/run_match_matrix.py", "--out", str(first))
    _run_script("scripts/run_match_matrix.py", "--out", str(second))

    report = _assert_same_json(first, second)
    validate_match_matrix_report(report)


def test_daily_slate_script_output_is_deterministic_and_contract_valid(tmp_path: Path) -> None:
    first = tmp_path / "slate_a.json"
    second = tmp_path / "slate_b.json"
    slate = ROOT / "data" / "daily_slate" / "sample_slate.json"

    _run_script("scripts/run_daily_slate.py", "--slate", str(slate), "--out", str(first))
    _run_script("scripts/run_daily_slate.py", "--slate", str(slate), "--out", str(second))

    report = _assert_same_json(first, second)
    validate_daily_slate_report(report)
