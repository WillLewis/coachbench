from __future__ import annotations

import json
import logging
import os
import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "engine"


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    duration_ms: int
    exit_code: int | None
    reason: str | None


def _limited(memory_bytes: int, timeout_seconds: float):
    def apply_limits() -> None:
        for limit, value in (
            (resource.RLIMIT_AS, (memory_bytes, memory_bytes)),
            (resource.RLIMIT_CPU, (int(timeout_seconds) + 1, int(timeout_seconds) + 1)),
            (resource.RLIMIT_NPROC, (64, 64)),
            (resource.RLIMIT_NOFILE, (64, 64)),
        ):
            try:
                resource.setrlimit(limit, value)
            except (OSError, ValueError):
                pass
    return apply_limits


def run_in_sandbox(
    script_path: Path,
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    memory_bytes: int,
    env_allowlist: list[str] = ("PATH", "HOME", "LANG"),
) -> SandboxResult:
    env = {key: os.environ[key] for key in env_allowlist if key in os.environ}
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME"):
        env.pop(key, None)
    preexec = _limited(memory_bytes, timeout_seconds) if os.name == "posix" else None
    if os.name != "posix":
        LOG.warning("POSIX resource limits unavailable; falling back to timeout-only sandbox")
    start = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", str(script_path), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            preexec_fn=preexec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return SandboxResult(False, exc.stdout or "", exc.stderr or "", int((time.monotonic() - start) * 1000), None, "timeout")
    duration = int((time.monotonic() - start) * 1000)
    stderr = (completed.stderr or "")[:4096]
    stdout = (completed.stdout or "")[:4096]
    if completed.returncode != 0:
        reason = "oom" if completed.returncode < 0 else "exit_nonzero"
        return SandboxResult(False, stdout, stderr, duration, completed.returncode, reason)
    return SandboxResult(True, stdout, stderr, duration, completed.returncode, None)


def write_drive_driver(cwd: Path) -> Path:
    script = cwd / "drive_driver.py"
    script.write_text(
        f"""
import json
import sys
from pathlib import Path
sys.path.insert(0, {str(ENGINE_PATH)!r})
sys.path.insert(0, {str(ROOT)!r})
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine

def load(path):
    module, cls = path.rsplit('.', 1)
    mod = __import__(module, fromlist=[cls])
    return getattr(mod, cls)()

agent_path, opponent_path, side, seed, max_plays = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
agent = load(agent_path)
opponent = load(opponent_path)
if side == 'offense':
    replay = CoachBenchEngine(seed=seed).run_drive(agent, opponent, max_plays=max_plays)
else:
    replay = CoachBenchEngine(seed=seed).run_drive(opponent, agent, max_plays=max_plays)
validate_replay_contract(replay)
Path('replay.json').write_text(json.dumps(replay, indent=2) + '\\n', encoding='utf-8')
""".lstrip(),
        encoding="utf-8",
    )
    return script


def run_drive_in_sandbox(
    agent_dotted_path: str,
    opponent_dotted_path: str,
    side: str,
    seed: int,
    max_plays: int,
    cwd: Path,
) -> SandboxResult:
    script = write_drive_driver(cwd)
    return run_in_sandbox(
        script,
        [agent_dotted_path, opponent_dotted_path, side, str(seed), str(max_plays)],
        cwd=cwd,
        timeout_seconds=5.0,
        memory_bytes=256 * 1024 * 1024,
    )
