from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.exploit_probe_defense import ExploitProbeDefense
from agents.exploit_probe_offense import ExploitProbeOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.action_legality import LegalActionFacade
from coachbench.contracts import validate_action_schema, validate_observation_safety
from coachbench.graph_loader import StrategyGraph
from coachbench.schema import AgentMemory
from scripts._evaluation import InspectingAgent


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "eval" / "adversarial"
GRAPH = StrategyGraph()
AGENTS = [
    ("static_offense", "offense", StaticOffense),
    ("adaptive_offense", "offense", AdaptiveOffense),
    ("exploit_probe_offense", "offense", ExploitProbeOffense),
    ("static_defense", "defense", StaticDefense),
    ("adaptive_defense", "defense", AdaptiveDefense),
    ("exploit_probe_defense", "defense", ExploitProbeDefense),
]


def _fixtures() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(FIXTURE_DIR.glob("*.json"))
    ]


CASES = [
    pytest.param(agent_name, agent_cls, fixture, id=f"{agent_name}__{fixture['name']}")
    for agent_name, side, agent_cls in AGENTS
    for fixture in _fixtures()
    if fixture["side"] == side
]


def _legal(observation: dict[str, Any]) -> LegalActionFacade:
    offense_concepts = [str(item) for item in observation.get("legal_concepts", [])]
    defense_calls = [str(item) for item in observation.get("legal_calls", [])]
    return LegalActionFacade(
        offense_concepts=offense_concepts,
        defense_calls=defense_calls,
        offense_action_fields={
            concept: GRAPH.offense_concept(concept)["action_fields"]
            for concept in offense_concepts
        },
        defense_action_fields={
            call: GRAPH.defense_call(call)["action_fields"]
            for call in defense_calls
        },
        risk_levels=list(GRAPH.resolution_model["risk_levels"]),
    )


def _assert_legal_action(action: Any, observation: dict[str, Any], side: str) -> None:
    action_dict = action.to_dict()
    validate_action_schema(action_dict, side)
    if side == "offense":
        assert action.concept_family in observation.get("legal_concepts", [])
    else:
        assert action.coverage_family in observation.get("legal_calls", [])


@pytest.mark.parametrize(("agent_name", "agent_class", "fixture"), CASES)
def test_adversarial_observations(agent_name: str, agent_class: type, fixture: dict[str, Any]) -> None:
    observation = dict(fixture["observation"])
    side = fixture["side"]
    validate_observation_safety(observation, side)
    agent = agent_class()
    if hasattr(agent, "observe"):
        agent.observe(observation)
    inspected = InspectingAgent(agent, side)

    try:
        action = inspected.choose_action(observation, AgentMemory(), _legal(observation))
    except Exception:
        assert fixture["expected_behavior"] in {"legal_or_documented_error", "documented_error"}
        assert not [failure for failure in inspected.failures if failure["check"] == "V3"]
        return

    assert fixture["expected_behavior"] in {"legal", "legal_or_documented_error"}
    _assert_legal_action(action, observation, side)
    assert not inspected.failures, f"{agent_name} failed adversarial fixture {fixture['name']}: {inspected.failures}"
