from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, OffenseAction


class StaticOffense:
    name = "Team A Static Offense"

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction:
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        if down >= 3 and distance >= 6:
            return legal.build_offense_action("quick_game", "balanced")
        if down == 1:
            return legal.build_offense_action("inside_zone", "conservative")
        return legal.build_offense_action("bunch_mesh", "balanced")
