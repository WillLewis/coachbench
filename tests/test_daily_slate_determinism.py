from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_daily_slate(out_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/run_daily_slate.py",
            "--slate",
            "data/daily_slate/sample_slate.json",
            "--out",
            str(out_path),
        ],
        check=True,
        timeout=30,
    )


def _replay_bytes() -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(Path("data/daily_slate/replays").glob("daily-slate-local-v0_*.json"))
    }


def test_daily_slate_subprocess_output_is_byte_deterministic(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    _run_daily_slate(first)
    first_replays = _replay_bytes()
    _run_daily_slate(second)
    second_replays = _replay_bytes()

    assert first.read_bytes() == second.read_bytes()
    assert first_replays
    assert first_replays == second_replays
