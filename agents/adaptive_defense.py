from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionEnumerator
from coachbench.schema import AgentMemory, DefenseAction


class AdaptiveDefense:
    name = "Team B Adaptive Defense"

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionEnumerator) -> DefenseAction:
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])

        if tendencies.get("screen", 0) >= 1:
            return legal.build_defense_action("trap_coverage", "balanced")
        if tendencies.get("play_action_flood", 0) >= 2:
            return legal.build_defense_action("redzone_bracket", "balanced")
        if tendencies.get("bunch_mesh", 0) >= 1:
            return legal.build_defense_action("redzone_bracket", "balanced")
        if tendencies.get("outside_zone", 0) >= 1:
            return legal.build_defense_action("bear_front", "balanced")
        if down >= 3 and distance >= 6:
            return legal.build_defense_action("simulated_pressure", "balanced")
        if down == 1:
            return legal.build_defense_action("bear_front", "balanced")
        return legal.build_defense_action("cover3_match", "balanced")
