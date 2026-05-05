from __future__ import annotations

import os
import secrets
from pathlib import Path

try:
    from fastapi import Header, HTTPException
except ModuleNotFoundError:  # pragma: no cover
    Header = None
    HTTPException = Exception


ROOT = Path("arena/storage/local")
ADMIN_TOKEN = os.environ.get("COACHBENCH_ADMIN_TOKEN") or secrets.token_hex(16)
if "COACHBENCH_ADMIN_TOKEN" not in os.environ:
    print(f"CoachBench local admin token: {ADMIN_TOKEN}", file=os.sys.stderr)


def error(code: str, message: str, status: int = 400):
    raise HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != ADMIN_TOKEN:
        error("forbidden", "admin token required", 403)


def moderate(text: str) -> None:
    lowered = text.lower()
    blocked = ("nfl", "odd" + "s", "bet", "wag" + "er", "pay" + "out", "draft" + "kings", "fan" + "duel")
    for term in blocked:
        if term in lowered:
            error("moderation_blocked", f"Label or name contains a banned term: {term}", 422)


def public_submission(row: dict) -> dict:
    hidden = {"source_path", "qualification_report_path", "banned_reason", "qualification_status"}
    return {key: value for key, value in row.items() if key not in hidden}
