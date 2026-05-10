from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from agents.model_defense import ModelDefense
from agents.model_offense import ModelOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.action_legality import ActionValidationError, LegalActionEnumerator
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine
from coachbench.graph_loader import StrategyGraph
from coachbench.locked_eval import LockedEvalViolation, enforce_locked_or_raise, set_locked_env
from coachbench.providers import ProviderResponse
from coachbench.schema import AgentMemory


GRAPH = StrategyGraph()
LEGAL = LegalActionEnumerator(GRAPH).restricted_api()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("COACHBENCH_LOCKED_EVAL", raising=False)


def _stub_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    class Client:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=Client))


def _response(payload: dict[str, Any]) -> ProviderResponse:
    return ProviderResponse(raw_text=str(payload), parsed_json=payload)


def _offense_observation() -> dict[str, Any]:
    return {
        "side": "offense",
        "game_state": {"down": 1, "distance": 10, "yardline": 22, "play_index": 0, "max_plays": 8, "points": 0, "terminal": False, "terminal_reason": None},
        "legal_concepts": ["inside_zone", "quick_game"],
        "own_resource_remaining": dict(GRAPH.constraints["drive_budgets"]["offense"]),
    }


def _defense_observation() -> dict[str, Any]:
    return {
        "side": "defense",
        "game_state": {"down": 1, "distance": 10, "yardline": 22, "play_index": 0, "max_plays": 8, "points": 0, "terminal": False, "terminal_reason": None},
        "legal_calls": ["base_cover3", "two_high_shell"],
        "own_resource_remaining": dict(GRAPH.constraints["drive_budgets"]["defense"]),
    }


def _offense_agent(*responses: ProviderResponse, default: dict[str, Any] | None = None) -> ModelOffense:
    return ModelOffense(config={"provider": "fake", "provider_config": {"canned_responses": list(responses), "default_payload": default}})


def _defense_agent(*responses: ProviderResponse, default: dict[str, Any] | None = None) -> ModelDefense:
    return ModelDefense(config={"provider": "fake", "provider_config": {"canned_responses": list(responses), "default_payload": default}})


def test_model_offense_with_fake_provider_picks_valid_concept() -> None:
    agent = _offense_agent(_response({"concept_family": "quick_game"}))
    action = agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)
    assert action.concept_family == "quick_game"


def test_model_offense_raises_action_validation_error_on_invalid_json() -> None:
    agent = _offense_agent(ProviderResponse(raw_text="not json", parsed_json=None))
    with pytest.raises(ActionValidationError, match="no valid JSON"):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)


def test_model_offense_raises_action_validation_error_on_missing_concept_family() -> None:
    agent = _offense_agent(_response({"foo": "bar"}))
    with pytest.raises(ActionValidationError, match="concept_family"):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)


def test_model_offense_raises_action_validation_error_on_unknown_concept() -> None:
    agent = _offense_agent(_response({"concept_family": "totally_made_up"}))
    with pytest.raises(ActionValidationError, match="not in legal set"):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)


def test_model_offense_increments_internal_fallback_count_on_each_failure() -> None:
    agent = _offense_agent(
        ProviderResponse(raw_text="not json", parsed_json=None),
        _response({"concept_family": "totally_made_up"}),
    )
    for _ in range(2):
        with pytest.raises(ActionValidationError):
            agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)
    assert agent._internal_fallback_count == 2


def test_model_offense_requires_network_false_with_fake_provider() -> None:
    assert _offense_agent(default={"concept_family": "inside_zone"}).requires_network is False


def test_model_offense_runs_full_drive_with_fake_provider() -> None:
    agent = _offense_agent(default={"concept_family": "inside_zone"})
    replay = CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), max_plays=4)
    validate_replay_contract(replay)
    assert all(not play["engine_internal"]["validation_result"]["offense"]["fallback_used"] for play in replay["plays"])
    assert all(play["public"]["offense_action"]["concept_family"] == "inside_zone" for play in replay["plays"])


def test_model_offense_engine_fallback_triggers_on_invalid_model_output() -> None:
    agent = _offense_agent(
        _response({"concept_family": "inside_zone"}),
        _response({"concept_family": "inside_zone"}),
        ProviderResponse(raw_text="not json", parsed_json=None),
        default={"concept_family": "inside_zone"},
    )
    replay = CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), max_plays=4)
    assert len(replay["plays"]) >= 3
    assert replay["plays"][2]["engine_internal"]["validation_result"]["offense"]["fallback_used"] is True


def test_model_offense_locked_run_rejects_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_anthropic(monkeypatch)
    set_locked_env(True)
    agent = ModelOffense(config={"provider": "anthropic", "provider_config": {"api_key": "test"}})
    with pytest.raises(LockedEvalViolation):
        enforce_locked_or_raise(agent, "candidate")


def test_model_offense_locked_run_accepts_fake_provider() -> None:
    set_locked_env(True)
    enforce_locked_or_raise(_offense_agent(default={"concept_family": "inside_zone"}), "candidate")


def test_model_defense_with_fake_provider_picks_valid_coverage() -> None:
    agent = _defense_agent(_response({"coverage_family": "two_high_shell"}))
    action = agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)
    assert action.coverage_family == "two_high_shell"


def test_model_defense_raises_action_validation_error_on_invalid_json() -> None:
    agent = _defense_agent(ProviderResponse(raw_text="not json", parsed_json=None))
    with pytest.raises(ActionValidationError, match="no valid JSON"):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)


def test_model_defense_raises_action_validation_error_on_missing_coverage_family() -> None:
    agent = _defense_agent(_response({"foo": "bar"}))
    with pytest.raises(ActionValidationError, match="coverage_family"):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)


def test_model_defense_raises_action_validation_error_on_unknown_coverage() -> None:
    agent = _defense_agent(_response({"coverage_family": "totally_made_up"}))
    with pytest.raises(ActionValidationError, match="not in legal set"):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)


def test_model_defense_increments_internal_fallback_count_on_each_failure() -> None:
    agent = _defense_agent(
        ProviderResponse(raw_text="not json", parsed_json=None),
        _response({"coverage_family": "totally_made_up"}),
    )
    for _ in range(2):
        with pytest.raises(ActionValidationError):
            agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)
    assert agent._internal_fallback_count == 2


def test_model_defense_requires_network_false_with_fake_provider() -> None:
    assert _defense_agent(default={"coverage_family": "base_cover3"}).requires_network is False


def test_model_defense_runs_full_drive_with_fake_provider() -> None:
    agent = _defense_agent(default={"coverage_family": "base_cover3"})
    replay = CoachBenchEngine(seed=42).run_drive(StaticOffense(), agent, max_plays=4)
    validate_replay_contract(replay)
    assert all(not play["engine_internal"]["validation_result"]["defense"]["fallback_used"] for play in replay["plays"])
    assert all(play["public"]["defense_action"]["coverage_family"] == "base_cover3" for play in replay["plays"])


def test_model_defense_engine_fallback_triggers_on_invalid_model_output() -> None:
    agent = _defense_agent(
        _response({"coverage_family": "base_cover3"}),
        _response({"coverage_family": "base_cover3"}),
        ProviderResponse(raw_text="not json", parsed_json=None),
        default={"coverage_family": "base_cover3"},
    )
    replay = CoachBenchEngine(seed=42).run_drive(StaticOffense(), agent, max_plays=4)
    assert len(replay["plays"]) >= 3
    assert replay["plays"][2]["engine_internal"]["validation_result"]["defense"]["fallback_used"] is True


def test_model_defense_locked_run_rejects_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_anthropic(monkeypatch)
    set_locked_env(True)
    agent = ModelDefense(config={"provider": "anthropic", "provider_config": {"api_key": "test"}})
    with pytest.raises(LockedEvalViolation):
        enforce_locked_or_raise(agent, "candidate")


def test_model_defense_locked_run_accepts_fake_provider() -> None:
    set_locked_env(True)
    enforce_locked_or_raise(_defense_agent(default={"coverage_family": "base_cover3"}), "candidate")
