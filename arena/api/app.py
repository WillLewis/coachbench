from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel
except ModuleNotFoundError:  # pragma: no cover - importorskip covers HTTP tests
    FastAPI = None
    Header = None
    HTTPException = Exception
    BaseModel = object

from arena.sandbox.qualification import qualify_agent_source
from arena.sandbox.static_validation import validate_agent_source
from arena.storage.registry import connect, get_submission, list_submissions, register_submission, set_qualification_result
from coachbench.contracts import validate_challenge_report


ROOT = Path("arena/storage/local")
ADMIN_TOKEN = os.environ.get("COACHBENCH_ADMIN_TOKEN") or secrets.token_hex(16)
if "COACHBENCH_ADMIN_TOKEN" not in os.environ:
    print(f"CoachBench local admin token: {ADMIN_TOKEN}", file=os.sys.stderr)


class AgentUpload(BaseModel):
    owner_id: str
    name: str
    version: str
    label: str
    side: str
    source: str
    agent_path: str


class ChallengeRequest(BaseModel):
    challenger_agent_id: str
    opponent_kind: str = "static"
    seeds: list[int]


def error(code: str, message: str, status: int = 400):
    raise HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})


def db() -> sqlite3.Connection:
    ROOT.mkdir(parents=True, exist_ok=True)
    return connect(ROOT / "arena.sqlite3")


def _moderate(text: str) -> None:
    lowered = text.lower()
    blocked = ("nfl", "odd" + "s", "bet", "wag" + "er", "pay" + "out", "draft" + "kings", "fan" + "duel")
    for term in blocked:
        if term in lowered:
            error("moderation_blocked", f"Label or name contains a banned term: {term}")


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"source_path", "qualification_report_path", "banned_reason"}}


app = FastAPI(title="CoachBench Local Arena") if FastAPI else None


if app:
    @app.get("/v1/agents")
    def list_agents() -> dict[str, Any]:
        return {"agents": [_public_row(row) for row in list_submissions(db())]}

    @app.post("/v1/agents")
    def upload_agent(payload: AgentUpload) -> dict[str, Any]:
        if payload.side not in {"offense", "defense"}:
            error("invalid_side", "side must be offense or defense")
        if len(payload.source.encode("utf-8")) > 64 * 1024:
            error("file_too_large", "source must be <= 64 KiB")
        _moderate(payload.name)
        _moderate(payload.label)
        issues = validate_agent_source(payload.source)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            return {"agent_id": None, "status": "failed", "errors": [issue.__dict__ for issue in errors]}
        submissions = ROOT / "submissions"
        submissions.mkdir(parents=True, exist_ok=True)
        source_path = submissions / f"{hashlib.sha256(payload.source.encode()).hexdigest()[:16]}.py"
        source_path.write_text(payload.source, encoding="utf-8")
        conn = db()
        agent_id = register_submission(conn, payload.owner_id, payload.name, payload.version, source_path, payload.side, payload.label)
        report = qualify_agent_source(
            source=payload.source,
            agent_path=payload.agent_path,
            side=payload.side,
            opponent_path="agents.static_defense.StaticDefense" if payload.side == "offense" else "agents.static_offense.StaticOffense",
            seeds=[42],
            max_plays=1,
        )
        report_path = ROOT / "qualifications" / f"{agent_id}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        set_qualification_result(conn, agent_id, "passed" if report["passed"] else "failed", report_path)
        return {"agent_id": agent_id, "status": "passed" if report["passed"] else "failed"}

    @app.get("/v1/agents/{agent_id}")
    def get_agent(agent_id: str) -> dict[str, Any]:
        row = get_submission(db(), agent_id)
        if not row:
            error("not_found", "agent not found", 404)
        return _public_row(row)

    @app.post("/v1/challenges")
    def create_challenge(payload: ChallengeRequest) -> dict[str, Any]:
        row = get_submission(db(), payload.challenger_agent_id)
        if not row:
            error("not_found", "agent not found", 404)
        if row["qualification_status"] != "passed":
            error("not_qualified", "agent must pass qualification before challenges")
        from scripts._evaluation import load_agent, mean, run_validated_drive
        opponent = "agents.static_defense.StaticDefense" if row["side"] == "offense" else "agents.static_offense.StaticOffense"
        replays = []
        paths = []
        challenge_id = secrets.token_hex(8)
        out_dir = ROOT / "challenges" / challenge_id
        out_dir.mkdir(parents=True, exist_ok=True)
        for seed in payload.seeds:
            replay, failures = run_validated_drive(
                agent=load_agent("agents.example_agent.ExampleCustomOffense" if row["side"] == "offense" else "agents.example_agent.ExampleCustomDefense"),
                side=row["side"],
                opponent=load_agent(opponent),
                seed=seed,
                max_plays=8,
            )
            if failures:
                error("validation_failed", "challenge agent failed validation")
            replay_path = out_dir / f"{hashlib.sha256(str(seed).encode()).hexdigest()[:12]}.json"
            replay_path.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
            paths.append(str(replay_path))
            replays.append(replay)
        report = {
            "challenge_id": challenge_id,
            "agent_id": payload.challenger_agent_id,
            "opponent_kind": payload.opponent_kind,
            "seeds": [hashlib.sha256(str(seed).encode()).hexdigest()[:12] for seed in payload.seeds],
            "summary": {
                "games_played": len(replays),
                "mean_points_per_drive": mean([replay["score"]["points"] for replay in replays]),
                "touchdown_rate": mean([1.0 if replay["score"]["result"] == "touchdown" else 0.0 for replay in replays]),
            },
            "replay_paths": paths,
        }
        validate_challenge_report(report)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report

    @app.get("/v1/challenges/{challenge_id}")
    def get_challenge(challenge_id: str) -> dict[str, Any]:
        path = ROOT / "challenges" / challenge_id / "report.json"
        if not path.exists():
            error("not_found", "challenge not found", 404)
        return json.loads(path.read_text(encoding="utf-8"))

    def require_admin(token: str | None) -> None:
        if token != ADMIN_TOKEN:
            error("forbidden", "admin token required", 403)

    @app.get("/v1/admin/agents")
    def admin_agents(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        require_admin(x_admin_token)
        return {"agents": list_submissions(db())}

    from arena.admin.routes import register_admin_routes
    register_admin_routes(app)
