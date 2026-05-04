from __future__ import annotations

import os
import subprocess
import sys


def test_showcase_script_replay_bytes_are_deterministic_across_subprocesses(tmp_path) -> None:
    if os.name != "posix":
        import pytest

        pytest.skip("subprocess byte determinism check is locked for POSIX runners")

    first = tmp_path / "showcase_a.json"
    second = tmp_path / "showcase_b.json"
    base_cmd = [sys.executable, "scripts/run_showcase.py", "--seed", "42"]

    subprocess.run([*base_cmd, "--out", str(first)], check=True, timeout=30)
    subprocess.run([*base_cmd, "--out", str(second)], check=True, timeout=30)

    assert first.read_bytes() == second.read_bytes()
