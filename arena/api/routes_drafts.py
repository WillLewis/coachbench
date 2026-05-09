from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from arena.api.deps import error, moderate
from arena.storage import drafts


router = APIRouter()


def _db():
    from arena.api.app import db

    return db()


class DraftCreateRequest(BaseModel):
    name: str
    side_eligibility: str
    tier: str
    config_json: Any
    identity_id: str | None = None


class DraftUpdateRequest(BaseModel):
    name: str | None = None
    side_eligibility: str | None = None
    tier: str | None = None
    config_json: Any | None = None
    identity_id: str | None = None


def _public_draft(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["config_json"] = json.loads(row["config_json"])
    return result


@router.post("/v1/drafts", status_code=201)
def create_draft(payload: DraftCreateRequest) -> dict:
    try:
        moderate(payload.name)
        row = drafts.create_draft(
            _db(),
            name=payload.name,
            side_eligibility=payload.side_eligibility,
            tier=payload.tier,
            config_json=payload.config_json,
            identity_id=payload.identity_id,
        )
    except ValueError as exc:
        error("invalid_draft_config", str(exc), 422)
    return {"draft": _public_draft(row)}


@router.get("/v1/drafts")
def list_drafts() -> dict:
    return {"drafts": [_public_draft(row) for row in drafts.list_drafts(_db())]}


@router.get("/v1/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict:
    row = drafts.get_draft(_db(), draft_id)
    if not row:
        error("not_found", "draft not found", 404)
    return {"draft": _public_draft(row)}


@router.patch("/v1/drafts/{draft_id}")
def update_draft(draft_id: str, payload: DraftUpdateRequest) -> dict:
    try:
        if payload.name is not None:
            moderate(payload.name)
        row = drafts.update_draft(
            _db(),
            draft_id,
            name=payload.name,
            side_eligibility=payload.side_eligibility,
            tier=payload.tier,
            config_json=payload.config_json,
            identity_id=payload.identity_id,
        )
    except ValueError as exc:
        error("invalid_draft_config", str(exc), 422)
    if not row:
        error("not_found", "draft not found", 404)
    return {"draft": _public_draft(row)}


@router.delete("/v1/drafts/{draft_id}")
def delete_draft(draft_id: str) -> dict:
    deleted = drafts.delete_draft(_db(), draft_id)
    if not deleted:
        error("not_found", "draft not found", 404)
    return {"deleted": True}
