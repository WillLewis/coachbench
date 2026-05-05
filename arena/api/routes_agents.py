from __future__ import annotations

import hashlib
from email.parser import BytesParser
from email.policy import default

from fastapi import APIRouter, Depends, Request

from arena.api.deps import ROOT, error, moderate, public_submission, require_admin_token
from arena.sandbox.static_validation import validate_agent_source
from arena.storage.registry import get_submission, list_submissions, register_submission
from arena.worker.queue import enqueue


router = APIRouter()


def _db():
    from arena.api.app import db
    return db()


async def _multipart(request: Request) -> tuple[dict[str, str], bytes, str]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type or "boundary=" not in content_type:
        error("invalid_content_type", "multipart/form-data required", 422)
    body = await request.body()
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    fields: dict[str, str] = {}
    file_bytes = b""
    filename = ""
    for part in message.iter_parts():
        params = dict(part.get_params(header="content-disposition") or [])
        name = params.get("name")
        if not name:
            continue
        if name == "file":
            filename = params.get("filename", "")
            file_bytes = part.get_payload(decode=True) or b""
        else:
            fields[name] = part.get_content().strip()
    return fields, file_bytes, filename


@router.get("/v1/agents")
def list_agents(_: None = Depends(require_admin_token)) -> dict:
    return {"agents": [public_submission(row) for row in list_submissions(_db()) if row.get("access_tier") == "sandboxed_code"]}


@router.post("/v1/agents", status_code=202)
async def upload_agent(request: Request, _: None = Depends(require_admin_token)) -> dict:
    fields, file_bytes, filename = await _multipart(request)
    if not filename.endswith(".py"):
        error("invalid_file", "uploaded agent must be a .py file", 422)
    if len(file_bytes) > 64 * 1024:
        error("file_too_large", "source must be <= 64 KiB", 422)
    required = {"name", "version", "label", "side", "owner_id"}
    missing = required - set(fields)
    if missing:
        error("missing_fields", f"missing form fields: {sorted(missing)}", 422)
    if fields["side"] not in {"offense", "defense"}:
        error("invalid_side", "side must be offense or defense", 422)
    moderate(fields["name"])
    moderate(fields["label"])
    source = file_bytes.decode("utf-8")
    issues = validate_agent_source(source)
    errors = [issue.__dict__ for issue in issues if issue.severity == "error"]
    warnings = [issue.__dict__ for issue in issues if issue.severity == "warning"]
    if errors:
        error("static_validation_failed", "agent source failed static validation", 422)
    submissions = ROOT / "submissions"
    submissions.mkdir(parents=True, exist_ok=True)
    source_path = submissions / f"{hashlib.sha256(file_bytes).hexdigest()[:16]}.py"
    source_path.write_bytes(file_bytes)
    conn = _db()
    agent_id = register_submission(
        conn,
        fields["owner_id"],
        fields["name"],
        fields["version"],
        source_path,
        fields["side"],
        fields["label"],
        access_tier="sandboxed_code",
        is_admin=True,
    )
    agent_path = "agents.example_agent.ExampleCustomOffense" if fields["side"] == "offense" else "agents.example_agent.ExampleCustomDefense"
    job_id = enqueue(conn, "qualification", {"agent_id": agent_id, "source_path": str(source_path), "agent_path": agent_path, "side": fields["side"]})
    return {"agent_id": agent_id, "status": "pending", "job_id": job_id, "warnings": warnings}


@router.get("/v1/agents/{agent_id}")
def get_agent(agent_id: str, _: None = Depends(require_admin_token)) -> dict:
    row = get_submission(_db(), agent_id)
    if not row:
        error("not_found", "agent not found", 404)
    return public_submission(row)
