from __future__ import annotations

import pytest

from arena.assistant import router as assistant_router
from arena.assistant.proposal import ProposalRejected
from arena.assistant.router import select_proposer
from arena.llm.client import LLMHttpError, LLMSchemaInvalid, LLMTimeout, LLMUnavailable


class FakeBudget:
    def __init__(self, killed: bool = False) -> None:
        self.conn = None
        self.max_calls_per_session = 8
        self._killed = killed

    def is_killed(self) -> bool:
        return self._killed


def _select(prompt: str = "Build an offense that punishes pressure without throwing picks.", budget: FakeBudget | None = None):
    return select_proposer(
        prompt,
        {},
        session_id="s",
        ip="127.0.0.1",
        budget=budget or FakeBudget(),
        current_draft=None,
    )


def test_kill_switch_routes_to_stub(monkeypatch) -> None:
    called = False

    def fail_real(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(assistant_router, "call_llm_real", fail_real)
    proposal, usage = _select(budget=FakeBudget(killed=True))
    assert proposal["intent"] == "create"
    assert usage.cost_usd_est == 0
    assert called is False


@pytest.mark.parametrize("exc", [LLMUnavailable("off"), LLMTimeout("slow"), LLMHttpError("down")])
def test_transport_errors_fall_back_to_stub(monkeypatch, exc) -> None:
    monkeypatch.setattr(assistant_router, "call_llm_real", lambda *args, **kwargs: (_ for _ in ()).throw(exc))
    proposal, usage = _select()
    assert proposal["intent"] == "create"
    assert usage.tokens_in == 0


@pytest.mark.parametrize("exc", [LLMSchemaInvalid("bad json"), ProposalRejected("bad proposal")])
def test_schema_and_validation_errors_retry_once_then_stub(monkeypatch, exc) -> None:
    calls = {"count": 0}

    def fail_twice(*args, **kwargs):
        calls["count"] += 1
        raise exc

    monkeypatch.setattr(assistant_router, "call_llm_real", fail_twice)
    proposal, usage = _select()
    assert calls["count"] == 2
    assert proposal["intent"] == "create"
    assert usage.tokens_out == 0
