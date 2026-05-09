from __future__ import annotations

import pytest

from arena.assistant import router as assistant_router
from arena.assistant.proposal import ProposalRejected
from arena.assistant.router import select_proposer
from arena.llm.client import LLMHttpError, LLMSchemaInvalid, LLMTimeout, LLMUnavailable
from arena.llm.usage import LLMUsage


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


def test_provider_bad_request_falls_back_to_stub(monkeypatch) -> None:
    class FakeBadRequestError(Exception):
        status_code = 400

    monkeypatch.setattr(assistant_router, "call_llm_real", lambda *args, **kwargs: (_ for _ in ()).throw(FakeBadRequestError("bad request")))
    proposal, usage = _select()
    assert proposal["intent"] == "create"
    assert usage.tokens_in == 0


def _clarify_proposal() -> dict:
    return {
        "summary": "Need more context before drafting.",
        "intent": "clarify",
        "target_draft_id": None,
        "target_tier": "declarative",
        "target_side": "offense",
        "target_identity_id": None,
        "proposed_changes": [],
        "evidence_refs": [],
        "requires_confirmation": False,
    }


def test_canonical_prompt_clarify_retries_then_falls_back_to_stub(monkeypatch) -> None:
    calls = {"count": 0}

    def clarify_real(*args, **kwargs):
        calls["count"] += 1
        return _clarify_proposal(), LLMUsage(tokens_in=10, tokens_out=10, cost_usd_est=0.01)

    monkeypatch.setattr(assistant_router, "call_llm_real", clarify_real)
    proposal, usage = _select()
    assert calls["count"] == 2
    assert proposal["intent"] == "create"
    assert usage.tokens_in == 0


def test_canonical_prompt_clarify_can_recover_on_retry(monkeypatch) -> None:
    calls = {"count": 0}

    def real_then_valid(prompt, context, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _clarify_proposal(), LLMUsage(tokens_in=10, tokens_out=10, cost_usd_est=0.01)
        from arena.assistant.templates import propose_from_prompt

        return propose_from_prompt("Build an offense that punishes pressure without throwing picks.", {}, session_id="s", ip="127.0.0.1"), LLMUsage(
            tokens_in=20,
            tokens_out=20,
            cost_usd_est=0.02,
        )

    monkeypatch.setattr(assistant_router, "call_llm_real", real_then_valid)
    proposal, usage = _select()
    assert calls["count"] == 2
    assert proposal["intent"] == "create"
    assert usage.tokens_in == 20


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
