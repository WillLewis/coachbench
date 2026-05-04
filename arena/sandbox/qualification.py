from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from coachbench.contracts import validate_qualification_report

from .runner import run_drive_in_sandbox
from .static_validation import validate_agent_source


def _issue_dict(issue) -> dict[str, Any]:
    return {
        "severity": issue.severity,
        "lineno": issue.lineno,
        "col": issue.col,
        "code": issue.code,
        "message": issue.message,
    }


def qualify_agent_source(
    *,
    source: str,
    agent_path: str,
    side: str,
    opponent_path: str,
    seeds: list[int] | None = None,
    max_plays: int = 8,
) -> dict[str, Any]:
    seeds = seeds or [42, 99, 202]
    issues = validate_agent_source(source)
    errors = [_issue_dict(issue) for issue in issues if issue.severity == "error"]
    warnings = [_issue_dict(issue) for issue in issues if issue.severity == "warning"]
    gauntlet = {"seeds": seeds, "runs": [], "failures": []}
    reasons = [item["code"] for item in errors]
    if not errors:
        for seed in seeds:
            with TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                result = run_drive_in_sandbox(agent_path, opponent_path, side, seed, max_plays, cwd)
                run = {"seed_hash": hashlib.sha256(str(seed).encode()).hexdigest()[:12], "ok": result.ok, "reason": result.reason}
                if result.ok:
                    replay = json.loads((cwd / "replay.json").read_text(encoding="utf-8"))
                    side_result = [play["public"]["validation_result"][side] for play in replay["plays"]]
                    fallback = any(item["fallback_used"] for item in side_result)
                    run.update({"points": replay["score"]["points"], "result": replay["score"]["result"], "fallback_used": fallback})
                    if fallback:
                        gauntlet["failures"].append({"seed_hash": run["seed_hash"], "check": "V2", "detail": "fallback used"})
                        reasons.append("V2")
                else:
                    gauntlet["failures"].append({"seed_hash": run["seed_hash"], "check": "sandbox", "detail": result.reason or "failed"})
                    reasons.append(result.reason or "sandbox")
                gauntlet["runs"].append(run)
    report = {
        "qualification_id": hashlib.sha256(f"{agent_path}:{side}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16],
        "agent_path": agent_path,
        "side": side,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "static_validation": {"errors": errors, "warnings": warnings},
        "gauntlet": gauntlet,
        "passed": not reasons,
        "reasons": sorted(set(reasons)),
    }
    validate_qualification_report(report)
    return report
