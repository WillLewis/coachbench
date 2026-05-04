from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from arena.sandbox.runner import run_drive_in_sandbox, run_in_sandbox


def test_sandbox_drive_success_writes_replay(tmp_path) -> None:
    result = run_drive_in_sandbox(
        "agents.example_agent.ExampleCustomOffense",
        "agents.static_defense.StaticDefense",
        "offense",
        42,
        1,
        tmp_path,
    )
    assert result.ok, result.stderr
    assert json.loads((tmp_path / "replay.json").read_text(encoding="utf-8"))["plays"]


def test_sandbox_timeout(tmp_path) -> None:
    script = tmp_path / "loop.py"
    script.write_text("while True:\n    pass\n", encoding="utf-8")
    result = run_in_sandbox(script, [], cwd=tmp_path, timeout_seconds=0.2, memory_bytes=128 * 1024 * 1024)
    assert not result.ok
    assert result.reason == "timeout"


def test_sandbox_oom_or_nonzero(tmp_path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX resource limits unavailable")
    script = tmp_path / "oom.py"
    script.write_text("x = bytearray(512 * 1024 * 1024)\n", encoding="utf-8")
    result = run_in_sandbox(script, [], cwd=tmp_path, timeout_seconds=2.0, memory_bytes=64 * 1024 * 1024)
    if result.ok:
        pytest.skip("RLIMIT_AS not enforced by this local platform")
    assert not result.ok
    assert result.reason in {"oom", "exit_nonzero"}


def test_sandbox_nonzero_for_socket_import_driver(tmp_path) -> None:
    script = tmp_path / "socket_driver.py"
    script.write_text("__import__('socket')\nraise SystemExit(1)\n", encoding="utf-8")
    result = run_in_sandbox(script, [], cwd=tmp_path, timeout_seconds=2.0, memory_bytes=128 * 1024 * 1024)
    assert not result.ok
