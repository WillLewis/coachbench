from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionEnumerator
from coachbench.schema import AgentMemory, DefenseAction


class StaticDefense:
    name = "Team A Static Defense"

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionEnumerator) -> DefenseAction:
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        if down >= 3 and distance >= 6:
            return legal.build_defense_action("two_high_shell", "conservative")
        if down == 1:
            return legal.build_defense_action("base_cover3", "balanced")
        return legal.build_defense_action("cover3_match", "balanced")
