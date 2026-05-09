from __future__ import annotations

from typing import Any

from arena.llm.budget import LLMBudget


def call_llm_stub(
    prompt: str,
    context: dict[str, Any],
    *,
    session_id: str = "stub",
    ip: str = "127.0.0.1",
    budget: LLMBudget | None = None,
) -> dict[str, Any]:
    gate = budget or LLMBudget()
    grant = gate.acquire(session_id, ip)
    try:
        return {"ok": False, "reason": "stub_only"}
    finally:
        gate.release(grant)
