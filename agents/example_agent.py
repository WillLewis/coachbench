from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionEnumerator
from coachbench.schema import AgentMemory, OffenseAction


class ExampleCustomOffense:
    """Minimal custom offense example.

    Copy this pattern when building local third-party agents.
    The agent only receives observations and legal actions exposed by the engine.
    """

    name = "Example Custom Offense"

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionEnumerator) -> OffenseAction:
        if memory.beliefs.screen_trap_risk > 0.45:
            return legal.build_offense_action("quick_game", "balanced")
        return legal.build_offense_action("screen", "balanced")
