from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.llm.budget import BudgetExceeded, LLMBudget
from arena.llm.stub import call_llm_stub
from arena.storage.registry import connect


def _budget(monkeypatch, **env: str) -> LLMBudget:
    defaults = {
        "LLM_GLOBAL_KILL_SWITCH": "off",
        "LLM_MAX_CALLS_PER_SESSION": "10",
        "LLM_MAX_CALLS_PER_IP_WINDOW": "10",
        "LLM_IP_WINDOW_SECONDS": "3600",
        "LLM_MAX_CONCURRENT_SESSIONS": "10",
        "LLM_VIRAL_SPIKE_COST_CEILING_USD": "100",
    }
    defaults.update(env)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    return LLMBudget(connect(":memory:"))


def test_kill_switch_blocks_acquire(monkeypatch) -> None:
    budget = _budget(monkeypatch, LLM_GLOBAL_KILL_SWITCH="on")
    with pytest.raises(BudgetExceeded):
        budget.acquire("s1", "127.0.0.1")


def test_per_session_cap_blocks(monkeypatch) -> None:
    budget = _budget(monkeypatch, LLM_MAX_CALLS_PER_SESSION="1")
    grant = budget.acquire("s1", "127.0.0.1")
    budget.release(grant)
    with pytest.raises(BudgetExceeded):
        budget.acquire("s1", "127.0.0.1")


def test_ip_window_cap_blocks(monkeypatch) -> None:
    budget = _budget(monkeypatch, LLM_MAX_CALLS_PER_IP_WINDOW="1")
    grant = budget.acquire("s1", "127.0.0.1")
    budget.release(grant)
    with pytest.raises(BudgetExceeded):
        budget.acquire("s2", "127.0.0.1")


def test_concurrent_cap_blocks_and_release_frees_slot(monkeypatch) -> None:
    budget = _budget(monkeypatch, LLM_MAX_CONCURRENT_SESSIONS="1")
    grant = budget.acquire("s1", "127.0.0.1")
    with pytest.raises(BudgetExceeded):
        budget.acquire("s2", "127.0.0.2")
    budget.release(grant)
    second = budget.acquire("s2", "127.0.0.2")
    budget.release(second)


def test_llm_stub_uses_budget_gate(monkeypatch) -> None:
    budget = _budget(monkeypatch, LLM_MAX_CALLS_PER_SESSION="1")
    response = call_llm_stub("prompt", {"context": True}, session_id="s1", ip="127.0.0.1", budget=budget)
    assert response == {"ok": False, "reason": "stub_only"}
    with pytest.raises(BudgetExceeded):
        call_llm_stub("prompt", {}, session_id="s1", ip="127.0.0.1", budget=budget)


def test_llm_status_route(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "25")
    response = TestClient(app).get("/v1/llm/status")
    assert response.status_code == 200
    assert response.json()["kill_switch"] is False
    assert response.json()["ceiling_usd"] == 25.0
