from __future__ import annotations

from fastapi import APIRouter

from arena.llm.budget import LLMBudget
from arena.storage import llm_budget


router = APIRouter()


def _db():
    from arena.api.app import db

    return db()


@router.get("/v1/llm/status")
def llm_status() -> dict:
    conn = _db()
    budget = LLMBudget(conn)
    return {
        "kill_switch": budget.is_killed(),
        "concurrent_sessions": llm_budget.count_concurrent_sessions(conn),
        "calls_last_hour": llm_budget.calls_since(conn, 3600),
        "ceiling_usd": budget.ceiling_usd,
    }
