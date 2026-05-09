from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.api.deps import ADMIN_TOKEN
from arena.llm.budget import LLMBudget, set_kill_switch_override


def test_admin_kill_switch_controls_status_and_propose_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "500")
    set_kill_switch_override(None)
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/admin/llm/kill_switch",
            json={"state": "on"},
            headers={"x-admin-token": ADMIN_TOKEN},
        )
        assert response.status_code == 200, response.text
        assert response.json()["kill_switch"] is True
        assert LLMBudget().is_killed() is True

        status = client.get("/v1/llm/status")
        assert status.status_code == 200
        assert status.json()["kill_switch"] is True

        proposal = client.post(
            "/v1/assistant/propose",
            json={"prompt": "Build an offense that punishes pressure without throwing picks.", "context": {"session_id": "killed"}},
        )
        assert proposal.status_code == 200, proposal.text
        assert proposal.json()["proposal"]["proposed_changes"]
    finally:
        set_kill_switch_override(None)
