from __future__ import annotations

from fastapi import APIRouter, Depends

from arena.api.deps import error, require_admin_token
from arena.worker.queue import get_job


router = APIRouter()


def _db():
    from arena.api.app import db
    return db()


@router.get("/v1/jobs/{job_id}")
def job_status(job_id: str, _: None = Depends(require_admin_token)) -> dict:
    job = get_job(_db(), job_id)
    if not job:
        error("not_found", "job not found", 404)
    return {key: job[key] for key in ("job_id", "kind", "status", "attempts", "last_error", "created_at", "completed_at")}
