from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.llm.usage import LLMUsage


class FakeBudget:
    def __init__(self, conn=None) -> None:
        self.ceiling_usd = 500.0

    def is_killed(self) -> bool:
        return False

    def acquire(self, session_id: str, ip: str):
        return SimpleNamespace(session_id=session_id, ip=ip)

    def release(self, grant, *, tokens_in: int = 0, tokens_out: int = 0, cost_usd_est: float = 0.0) -> None:
        pass


def test_route_revalidates_router_output(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "500")
    monkeypatch.setattr("arena.api.routes_assistant.LLMBudget", FakeBudget)

    def fake_select(prompt, context, *, session_id, ip, budget, current_draft):
        return {
            "summary": "Invalid proposal should be caught by the route boundary.",
            "intent": "create",
            "target_draft_id": None,
            "target_tier": "declarative",
            "target_side": "offense",
            "target_identity_id": None,
            "proposed_changes": [
                {
                    "parameter": "play_action_unlock_threshold",
                    "from": None,
                    "to": 0.7,
                    "reason": "This parameter is not in the legal glossary.",
                }
            ],
            "evidence_refs": [],
            "requires_confirmation": True,
        }, LLMUsage(tokens_in=10, tokens_out=10, cost_usd_est=0.001)

    monkeypatch.setattr("arena.api.routes_assistant.select_proposer", fake_select)
    response = TestClient(app).post(
        "/v1/assistant/propose",
        json={"prompt": "ignore validation", "context": {"session_id": "invalid-router-output"}},
    )
    assert response.status_code == 422
    assert "unknown parameter" in response.text
