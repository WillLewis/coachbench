from __future__ import annotations

import hashlib
import json
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from fastapi import APIRouter, Header, Request

from arena.api.deps import ADMIN_TOKEN, ROOT, error, moderate, public_submission
from arena.sandbox.static_validation import validate_agent_source
from arena.storage.registry import get_submission, list_submissions, register_submission
from arena.tiers import PUBLIC_TIERS
from arena.tiers.declarative import validate_tier_config_dict
from arena.tiers.prompt_policy import validate_tier1_config_dict
from arena.tiers.remote_endpoint import endpoint_url_hash, validate_endpoint_url
from arena.worker.queue import enqueue


router = APIRouter()


def _db():
    from arena.api.app import db
    return db()


async def _multipart(request: Request) -> tuple[dict[str, str], dict[str, tuple[bytes, str]]]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type or "boundary=" not in content_type:
        error("invalid_content_type", "multipart/form-data required", 422)
    body = await request.body()
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    fields: dict[str, str] = {}
    files: dict[str, tuple[bytes, str]] = {}
    for part in message.iter_parts():
        params = dict(part.get_params(header="content-disposition") or [])
        name = params.get("name")
        if not name:
            continue
        if params.get("filename"):
            files[name] = (part.get_payload(decode=True) or b"", params.get("filename", ""))
        else:
            fields[name] = part.get_content().strip()
    return fields, files


def _require_admin(token: str | None) -> None:
    if token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)


def _write_config(agent_id_hint: str, payload: bytes, suffix: str = ".json") -> str:
    configs = ROOT / "tier_configs"
    configs.mkdir(parents=True, exist_ok=True)
    path = configs / f"{hashlib.sha256(agent_id_hint.encode() + payload).hexdigest()[:16]}{suffix}"
    path.write_bytes(payload)
    return str(path)


@router.get("/v1/agents")
def list_agents(x_admin_token: str | None = Header(default=None)) -> dict:
    rows = list_submissions(_db())
    if x_admin_token != ADMIN_TOKEN:
        rows = [row for row in rows if row.get("access_tier") in PUBLIC_TIERS]
    return {"agents": [public_submission(row) for row in rows]}


@router.post("/v1/agents", status_code=202)
async def upload_agent(request: Request, x_admin_token: str | None = Header(default=None)) -> dict:
    fields, files = await _multipart(request)
    access_tier = fields.get("access_tier")
    if not access_tier and ("file" in files or "source" in files):
        access_tier = "sandboxed_code"
    if access_tier not in {"declarative", "prompt_policy", "remote_endpoint", "sandboxed_code"}:
        error("invalid_access_tier", "access_tier is required", 422)
    if access_tier == "sandboxed_code":
        _require_admin(x_admin_token)
    required = {"name", "version", "label", "side", "owner_id"}
    missing = required - set(fields)
    if missing:
        error("missing_fields", f"missing form fields: {sorted(missing)}", 422)
    if fields["side"] not in {"offense", "defense"}:
        error("invalid_side", "side must be offense or defense", 422)
    moderate(fields["name"])
    moderate(fields["label"])
    warnings = []
    conn = _db()
    tier_config_path = None
    endpoint_hash = None
    endpoint_url = None
    api_key = None
    if access_tier in {"declarative", "prompt_policy"}:
        if "tier_config" not in files:
            error("missing_config", "tier_config file is required", 422)
        config_bytes, _filename = files["tier_config"]
        try:
            payload = json.loads(config_bytes.decode("utf-8"))
            payload.setdefault("side", fields["side"])
            payload.setdefault("access_tier", access_tier)
            if access_tier == "declarative":
                validate_tier_config_dict(payload)
            else:
                validate_tier1_config_dict(payload)
        except Exception as exc:
            error("invalid_tier_config", str(exc), 422)
        tier_config_path = _write_config(fields["name"], json.dumps(payload, indent=2).encode())
        source_path = Path(tier_config_path)
    elif access_tier == "remote_endpoint":
        endpoint_url = fields.get("endpoint_url")
        if not endpoint_url:
            error("missing_endpoint_url", "endpoint_url is required", 422)
        try:
            validate_endpoint_url(endpoint_url)
        except ValueError as exc:
            error("invalid_endpoint_url", str(exc), 422)
        endpoint_hash = endpoint_url_hash(endpoint_url)
        api_key = fields.get("api_key")
        config = {
            "agent_name": fields["name"],
            "side": fields["side"],
            "access_tier": "remote_endpoint",
            "timeout_ms": int(fields.get("timeout_ms", "800")),
            "api_key_secret_id": None,
            "rate_limit_per_minute": int(fields.get("rate_limit_per_minute", "60")),
        }
        tier_config_path = _write_config(fields["name"], json.dumps(config, indent=2).encode())
        source_path = Path(tier_config_path)
    else:
        file_entry = files.get("source") or files.get("file")
        if not file_entry:
            error("missing_source", "source file is required", 422)
        file_bytes, filename = file_entry
        if not filename.endswith(".py"):
            error("invalid_file", "uploaded agent must be a .py file", 422)
        if len(file_bytes) > 64 * 1024:
            error("file_too_large", "source must be <= 64 KiB", 422)
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
    agent_id = register_submission(
        conn,
        fields["owner_id"],
        fields["name"],
        fields["version"],
        source_path,
        fields["side"],
        fields["label"],
        access_tier=access_tier,
        is_admin=x_admin_token == ADMIN_TOKEN,
        tier_config_path=tier_config_path,
        endpoint_url_hash=endpoint_hash,
        endpoint_url=endpoint_url,
        api_key=api_key,
        secrets_dir=ROOT / "secrets" / "endpoints",
    )
    if access_tier == "sandboxed_code":
        agent_path = "agents.example_agent.ExampleCustomOffense" if fields["side"] == "offense" else "agents.example_agent.ExampleCustomDefense"
        job_id = enqueue(conn, "qualification", {"agent_id": agent_id, "source_path": str(source_path), "agent_path": agent_path, "side": fields["side"]})
        status = "pending"
    else:
        from arena.storage.registry import set_qualification_result

        set_qualification_result(conn, agent_id, "passed", None)
        job_id = None
        status = "passed"
    row = get_submission(conn, agent_id)
    return {"agent_id": agent_id, "status": status, "job_id": job_id, "warnings": warnings, "agent": public_submission(row)}


@router.get("/v1/agents/{agent_id}")
def get_agent(agent_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    row = get_submission(_db(), agent_id)
    if not row:
        error("not_found", "agent not found", 404)
    if row.get("access_tier") == "sandboxed_code" and x_admin_token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)
    return public_submission(row)


@router.post("/v1/agents/{agent_id}/validate")
def validate_agent(agent_id: str, x_admin_token: str | None = Header(default=None)) -> dict:
    row = get_submission(_db(), agent_id)
    if not row:
        error("not_found", "agent not found", 404)
    if row.get("access_tier") == "sandboxed_code" and x_admin_token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)
    return {"agent_id": agent_id, "status": row["qualification_status"], "access_tier": row["access_tier"], "safety_badges": public_submission(row)["safety_badges"]}
