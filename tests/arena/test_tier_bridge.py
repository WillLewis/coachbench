from __future__ import annotations

import time

from arena.tiers.bridge import TieredAgent
from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory


class FakeLegal:
    def legal_offense_concepts(self):
        return ["quick_game", "vertical_shot"]

    def build_offense_action(self, concept, risk_level="balanced"):
        return LegalActionFacade(["quick_game", "vertical_shot"], [], {
            "quick_game": {
                "personnel_family": "11p",
                "formation_family": "spread",
                "motion_family": "none",
                "protection_family": "quick",
            },
            "vertical_shot": {
                "personnel_family": "11p",
                "formation_family": "spread",
                "motion_family": "none",
                "protection_family": "max",
            },
        }, {}, ["balanced"]).build_offense_action(concept, risk_level)


class IllegalAdapter:
    access_tier = "declarative"
    name = "Illegal"

    def choose_action(self, obs):
        return "not_legal"


class SlowAdapter:
    access_tier = "declarative"
    name = "Slow"

    def choose_action(self, obs):
        time.sleep(0.1)
        return "quick_game"


def test_illegal_action_and_timeout_trigger_fallback() -> None:
    observation = {"game_state": {"down": 1, "distance": 10, "yardline": 12, "play_index": 0, "points": 0, "max_plays": 8}, "own_resource_remaining": {"spacing": 10}, "seed": 42}
    illegal = TieredAgent(IllegalAdapter(), "offense")
    action = illegal.choose_action(observation, AgentMemory(), FakeLegal())
    assert action.concept_family == "quick_game"
    assert illegal.fallback_count == 1

    slow = TieredAgent(SlowAdapter(), "offense", per_call_timeout_ms=10)
    action = slow.choose_action(observation, AgentMemory(), FakeLegal())
    assert action.concept_family == "quick_game"
    assert slow.fallback_count == 1
    assert "seed" not in repr(slow.observations_seen[-1])
