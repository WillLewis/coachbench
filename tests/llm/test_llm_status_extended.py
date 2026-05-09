from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.api.app import db
from arena.storage import llm_budget


def test_llm_status_exposes_cost_and_model_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "500")
    monkeypatch.setenv("COACHBENCH_LLM_MODEL", "claude-opus-4-7")
    conn = db()
    llm_budget.record_call(conn, session_id="session-a", ip="127.0.0.1", tokens_in=100, tokens_out=20, cost_usd_est=0.02)
    llm_budget.record_call(conn, session_id="session-b", ip="127.0.0.2", tokens_in=200, tokens_out=40, cost_usd_est=0.04)

    response = TestClient(app).get("/v1/llm/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model"] == "claude-opus-4-7"
    assert body["cost_usd_today"] >= 0.06
    assert body["cost_usd_session_p99"] is not None
    assert body["cost_usd_session_p99"] >= 0.04
    assert body["ceiling_usd"] == 500.0
