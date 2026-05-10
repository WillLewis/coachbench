from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from coachbench.contracts import validate_eval_suite_report


ROOT = Path(__file__).resolve().parents[1]


def _run_suite(out: Path) -> dict:
    subprocess.run(
        [sys.executable, "scripts/run_eval_suite.py", "--suite", "smoke", "--out", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_smoke_suite_writes_valid_report(tmp_path: Path) -> None:
    report = _run_suite(tmp_path / "smoke.json")
    validate_eval_suite_report(report)


def test_smoke_suite_report_hash_deterministic(tmp_path: Path) -> None:
    first = _run_suite(tmp_path / "smoke_a.json")
    second = _run_suite(tmp_path / "smoke_b.json")
    assert first["report_hash"] == second["report_hash"]


def test_smoke_suite_fallback_rate_for_default_baseline_is_zero(tmp_path: Path) -> None:
    report = _run_suite(tmp_path / "smoke.json")
    assert report["metrics"]["fallback_rate_candidate"] == 0.0
    assert report["metrics"]["fallback_rate_baseline"] == 0.0


def test_smoke_suite_validates_against_contract(tmp_path: Path) -> None:
    report = _run_suite(tmp_path / "smoke.json")
    validate_eval_suite_report(report)
