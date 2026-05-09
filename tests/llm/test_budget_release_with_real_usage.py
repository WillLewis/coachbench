from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from arena.api.app import app
from arena.assistant.templates import propose_from_prompt
from arena.llm.usage import LLMUsage, ZERO_USAGE


def _env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_GLOBAL_KILL_SWITCH", "off")
    monkeypatch.setenv("LLM_MAX_CALLS_PER_SESSION", "50")
    monkeypatch.setenv("LLM_MAX_CALLS_PER_IP_WINDOW", "50")
    monkeypatch.setenv("LLM_IP_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("LLM_MAX_CONCURRENT_SESSIONS", "4")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "500")


class FakeBudget:
    released: list[tuple[int, int, float]] = []

    def __init__(self, conn=None) -> None:
        self.ceiling_usd = 500.0

    def is_killed(self) -> bool:
        return False

    def acquire(self, session_id: str, ip: str):
        return SimpleNamespace(session_id=session_id, ip=ip)

    def release(self, grant, *, tokens_in: int = 0, tokens_out: int = 0, cost_usd_est: float = 0.0) -> None:
        self.released.append((tokens_in, tokens_out, cost_usd_est))


def test_route_release_records_real_usage(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    FakeBudget.released = []
    monkeypatch.setattr("arena.api.routes_assistant.LLMBudget", FakeBudget)

    def fake_select(prompt, context, *, session_id, ip, budget, current_draft):
        proposal = propose_from_prompt(prompt, context, session_id=session_id, ip=ip)
        return proposal, LLMUsage(tokens_in=111, tokens_out=22, cost_usd_est=0.0123)

    monkeypatch.setattr("arena.api.routes_assistant.select_proposer", fake_select)
    response = TestClient(app).post(
        "/v1/assistant/propose",
        json={"prompt": "Build an offense that punishes pressure without throwing picks.", "context": {"session_id": "usage"}},
    )
    assert response.status_code == 200, response.text
    assert FakeBudget.released == [(111, 22, 0.0123)]


def test_route_release_records_zero_for_stub_usage(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _env(monkeypatch)
    FakeBudget.released = []
    monkeypatch.setattr("arena.api.routes_assistant.LLMBudget", FakeBudget)

    def fake_select(prompt, context, *, session_id, ip, budget, current_draft):
        proposal = propose_from_prompt(prompt, context, session_id=session_id, ip=ip)
        return proposal, ZERO_USAGE

    monkeypatch.setattr("arena.api.routes_assistant.select_proposer", fake_select)
    response = TestClient(app).post(
        "/v1/assistant/propose",
        json={"prompt": "Build a run-first coordinator that unlocks play-action.", "context": {"session_id": "stub"}},
    )
    assert response.status_code == 200, response.text
    assert FakeBudget.released == [(0, 0, 0.0)]
