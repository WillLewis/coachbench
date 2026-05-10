from __future__ import annotations

import os

import pytest

from coachbench.locked_eval import (
    LOCKED_LLM_ENV_VARS,
    LockedEvalViolation,
    enforce_locked_or_raise,
    is_locked_env,
    restore_llm_env_vars,
    scrub_llm_env_vars,
    set_locked_env,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COACHBENCH_LOCKED_EVAL", raising=False)
    for key in LOCKED_LLM_ENV_VARS:
        monkeypatch.delenv(key, raising=False)


def test_is_locked_env_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_locked_env()
    monkeypatch.setenv("COACHBENCH_LOCKED_EVAL", "1")
    assert is_locked_env()


def test_set_locked_env_toggles() -> None:
    set_locked_env(True)
    assert os.environ["COACHBENCH_LOCKED_EVAL"] == "1"
    set_locked_env(False)
    assert "COACHBENCH_LOCKED_EVAL" not in os.environ


def test_scrub_llm_env_vars_removes_known_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    scrub_llm_env_vars()
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_scrub_llm_env_vars_returns_snapshot_for_restoration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    snapshot = scrub_llm_env_vars()
    assert snapshot == {"OPENAI_API_KEY": "secret"}


def test_restore_llm_env_vars_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "secret")
    snapshot = scrub_llm_env_vars()
    restore_llm_env_vars(snapshot)
    assert os.environ["MISTRAL_API_KEY"] == "secret"


def test_enforce_locked_raises_for_requires_network_agent_class() -> None:
    class Agent:
        requires_network = True

    set_locked_env(True)
    with pytest.raises(LockedEvalViolation, match="candidate"):
        enforce_locked_or_raise(Agent(), "candidate")


def test_enforce_locked_raises_for_requires_network_agent_instance() -> None:
    class Agent:
        pass

    agent = Agent()
    agent.requires_network = True
    set_locked_env(True)
    with pytest.raises(LockedEvalViolation, match="opponent"):
        enforce_locked_or_raise(agent, "opponent")


def test_enforce_locked_passes_for_no_network_agent() -> None:
    class Agent:
        requires_network = False

    set_locked_env(True)
    enforce_locked_or_raise(Agent(), "candidate")


def test_enforce_locked_noop_when_not_locked() -> None:
    class Agent:
        requires_network = True

    enforce_locked_or_raise(Agent(), "candidate")
