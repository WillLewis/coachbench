from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agents.model_defense import ModelDefense
from agents.model_offense import ModelOffense
from coachbench.action_legality import ActionValidationError, LegalActionEnumerator
from coachbench.graph_loader import StrategyGraph
from coachbench.model_debug import DEBUG_PATH_ENV_VAR, log_model_decision
from coachbench.providers import ProviderResponse
from coachbench.schema import AgentMemory


GRAPH = StrategyGraph()
LEGAL = LegalActionEnumerator(GRAPH).restricted_api()


def _debug_tree() -> set[str]:
    root = Path("data/eval/debug")
    if not root.exists():
        return set()
    return {str(path) for path in root.rglob("*")}


def _call_log(
    *,
    parsed_json: dict[str, Any] | None = {"concept_family": "quick_game"},
    outcome: str = "picked:quick_game",
    turn_count: int = 1,
) -> None:
    log_model_decision(
        agent_name="ModelOffense",
        side="offense",
        turn_count=turn_count,
        user_prompt="rendered observation",
        raw_text='{"concept_family":"quick_game"}',
        parsed_json=parsed_json,
        error=None,
        outcome=outcome,
        legal_set=["inside_zone", "quick_game"],
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _offense_observation() -> dict[str, Any]:
    return {
        "side": "offense",
        "game_state": {
            "down": 1,
            "distance": 10,
            "yardline": 22,
            "play_index": 0,
            "max_plays": 8,
            "points": 0,
            "terminal": False,
            "terminal_reason": None,
        },
        "legal_concepts": ["inside_zone", "quick_game"],
        "own_resource_remaining": dict(GRAPH.constraints["drive_budgets"]["offense"]),
    }


def _defense_observation() -> dict[str, Any]:
    return {
        "side": "defense",
        "game_state": {
            "down": 1,
            "distance": 10,
            "yardline": 22,
            "play_index": 0,
            "max_plays": 8,
            "points": 0,
            "terminal": False,
            "terminal_reason": None,
        },
        "legal_calls": ["base_cover3", "two_high_shell"],
        "own_resource_remaining": dict(GRAPH.constraints["drive_budgets"]["defense"]),
    }


def _offense_agent(*responses: ProviderResponse) -> ModelOffense:
    return ModelOffense(config={"provider": "fake", "provider_config": {"canned_responses": list(responses)}})


def _defense_agent(*responses: ProviderResponse) -> ModelDefense:
    return ModelDefense(config={"provider": "fake", "provider_config": {"canned_responses": list(responses)}})


def test_log_no_op_when_env_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COACHBENCH_MODEL_DEBUG", raising=False)
    monkeypatch.delenv(DEBUG_PATH_ENV_VAR, raising=False)
    before = _debug_tree()

    _call_log()

    assert list(tmp_path.rglob("*")) == []
    assert _debug_tree() == before


def test_log_no_op_when_env_set_to_other_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "true")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(tmp_path / "test.jsonl"))
    before = _debug_tree()

    _call_log()

    assert list(tmp_path.rglob("*")) == []
    assert _debug_tree() == before


def test_log_writes_when_env_set_to_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "test.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    _call_log()

    rows = _read_jsonl(log_path)
    assert len(rows) == 1
    assert set(rows[0]) == {
        "agent_name",
        "error",
        "legal_set",
        "outcome",
        "parsed_json",
        "raw_text",
        "side",
        "timestamp",
        "turn_count",
        "user_prompt",
    }


def test_log_appends_multiple_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "test.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    for turn_count in (1, 2, 3):
        _call_log(turn_count=turn_count)

    rows = _read_jsonl(log_path)
    assert [row["turn_count"] for row in rows] == [1, 2, 3]


def test_log_writes_creates_parent_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "deep" / "nested" / "dir" / "log.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    _call_log()

    assert log_path.exists()


def test_log_outcome_picked_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "test.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    _call_log(outcome="picked:quick_game")

    assert _read_jsonl(log_path)[0]["outcome"] == "picked:quick_game"


def test_log_outcome_fallback_concept_not_legal_includes_rejected_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "test.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    _call_log(outcome="fallback:concept_not_legal:made_up_concept")

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:concept_not_legal:made_up_concept"


def test_log_handles_null_parsed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "test.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))

    _call_log(parsed_json=None)

    assert _read_jsonl(log_path)[0]["parsed_json"] is None


def test_model_offense_logs_picked_outcome_when_debug_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "offense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    response = ProviderResponse(
        raw_text='{"concept_family": "inside_zone"}',
        parsed_json={"concept_family": "inside_zone"},
    )
    agent = _offense_agent(response)

    action = agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)

    row = _read_jsonl(log_path)[0]
    assert action.concept_family == "inside_zone"
    assert row["outcome"] == "picked:inside_zone"
    assert row["raw_text"] == '{"concept_family": "inside_zone"}'
    assert row["parsed_json"] == {"concept_family": "inside_zone"}


def test_model_offense_logs_fallback_no_valid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "offense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _offense_agent(ProviderResponse(raw_text="not json", parsed_json=None, error=None))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:no_valid_json"


def test_model_offense_logs_fallback_missing_concept_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "offense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _offense_agent(ProviderResponse(raw_text='{"play": "inside_zone"}', parsed_json={"play": "inside_zone"}))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:missing_concept_family"


def test_model_offense_logs_fallback_concept_not_legal_includes_rejected_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "offense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _offense_agent(ProviderResponse(raw_text='{"concept_family": "made_up"}', parsed_json={"concept_family": "made_up"}))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:concept_not_legal:made_up"


def test_model_offense_does_not_log_when_debug_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "offense.jsonl"
    monkeypatch.delenv("COACHBENCH_MODEL_DEBUG", raising=False)
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _offense_agent(
        ProviderResponse(raw_text='{"concept_family": "inside_zone"}', parsed_json={"concept_family": "inside_zone"}),
        ProviderResponse(raw_text="not json", parsed_json=None),
    )

    agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)
    with pytest.raises(ActionValidationError):
        agent.choose_action(_offense_observation(), AgentMemory(), LEGAL)

    assert not log_path.exists()


def test_model_defense_logs_picked_outcome_when_debug_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "defense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    response = ProviderResponse(
        raw_text='{"coverage_family": "base_cover3"}',
        parsed_json={"coverage_family": "base_cover3"},
    )
    agent = _defense_agent(response)

    action = agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)

    row = _read_jsonl(log_path)[0]
    assert action.coverage_family == "base_cover3"
    assert row["outcome"] == "picked:base_cover3"
    assert row["raw_text"] == '{"coverage_family": "base_cover3"}'
    assert row["parsed_json"] == {"coverage_family": "base_cover3"}


def test_model_defense_logs_fallback_no_valid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "defense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _defense_agent(ProviderResponse(raw_text="not json", parsed_json=None, error=None))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:no_valid_json"


def test_model_defense_logs_fallback_missing_coverage_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "defense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _defense_agent(ProviderResponse(raw_text='{"call": "base_cover3"}', parsed_json={"call": "base_cover3"}))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:missing_coverage_family"


def test_model_defense_logs_fallback_coverage_not_legal_includes_rejected_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "defense.jsonl"
    monkeypatch.setenv("COACHBENCH_MODEL_DEBUG", "1")
    monkeypatch.setenv(DEBUG_PATH_ENV_VAR, str(log_path))
    agent = _defense_agent(ProviderResponse(raw_text='{"coverage_family": "made_up"}', parsed_json={"coverage_family": "made_up"}))

    with pytest.raises(ActionValidationError):
        agent.choose_action(_defense_observation(), AgentMemory(), LEGAL)

    assert _read_jsonl(log_path)[0]["outcome"] == "fallback:coverage_not_legal:made_up"
