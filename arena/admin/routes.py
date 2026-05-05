from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from arena.api.deps import ADMIN_TOKEN, error
from arena.storage.registry import ban_submission, get_submission, list_submissions, set_qualification_result


AUDIT_DIR = Path("arena/storage/audit")


def _audit(route: str, token: str, agent_id: str) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": route,
        "admin_token_hash": hashlib.sha256(token.encode()).hexdigest()[:12],
        "agent_id": agent_id,
    }
    path = AUDIT_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.log"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def require_admin_token(token: str | None) -> None:
    if token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)


def register_admin_routes(app) -> None:
    from fastapi import Header
    from arena.api.app import db

    @app.post("/v1/admin/agents/{agent_id}/approve")
    def approve(agent_id: str, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        set_qualification_result(db(), agent_id, "passed", None)
        _audit("approve", x_admin_token or "", agent_id)
        return {"agent_id": agent_id, "status": "passed"}

    @app.post("/v1/admin/agents/{agent_id}/reject")
    def reject(agent_id: str, body: dict, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        set_qualification_result(db(), agent_id, "failed", None, body.get("reason"))
        _audit("reject", x_admin_token or "", agent_id)
        return {"agent_id": agent_id, "status": "failed"}

    @app.post("/v1/admin/agents/{agent_id}/ban")
    def ban(agent_id: str, body: dict, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        ban_submission(db(), agent_id, body.get("reason", "banned"))
        _audit("ban", x_admin_token or "", agent_id)
        return {"agent_id": agent_id, "status": "banned"}

    @app.get("/v1/admin/agents/{agent_id}/source")
    def source(agent_id: str, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        row = get_submission(db(), agent_id)
        if not row:
            error("not_found", "agent not found", 404)
        _audit("source", x_admin_token or "", agent_id)
        return {"agent_id": agent_id, "source": Path(row["source_path"]).read_text(encoding="utf-8")}

    @app.get("/v1/admin/jobs")
    def jobs(status: str | None = None, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        from arena.worker.queue import list_jobs
        return {"jobs": list_jobs(db(), status)}

    @app.get("/v1/admin/agents")
    def agents(x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        return {"agents": list_submissions(db())}

    @app.post("/v1/admin/agents/{agent_id}/promote_to_league")
    def promote_to_league(agent_id: str, body: dict, x_admin_token: str | None = Header(default=None)):
        require_admin_token(x_admin_token)
        row = get_submission(db(), agent_id)
        if not row:
            error("not_found", "agent not found", 404)
        from arena.tiers.league import is_eligible

        league = body.get("league")
        if not is_eligible(league, row["access_tier"]):
            error("ineligible_league", "agent tier is not eligible for this league", 422)
        _audit("promote_to_league", x_admin_token or "", agent_id)
        return {"agent_id": agent_id, "league": league, "eligible": True}
