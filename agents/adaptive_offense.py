from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, OffenseAction


class AdaptiveOffense:
    name = "Team B Adaptive Offense"

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction:
        beliefs = memory.beliefs
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])

        if memory.own_recent_calls.count("play_action_flood") >= 2:
            return legal.build_offense_action("quick_game", "balanced")
        if beliefs.match_coverage_stress > 0.42:
            return legal.build_offense_action("bunch_mesh", "balanced")
        if beliefs.screen_trap_risk < 0.45 and beliefs.true_pressure_confidence > 0.42:
            return legal.build_offense_action("screen", "balanced")
        if beliefs.run_fit_aggression > 0.42:
            return legal.build_offense_action("play_action_flood", "balanced")
        if tendencies.get("wide_zone_constrained", 0) >= 1:
            return legal.build_offense_action("quick_game", "balanced")
        if down == 1:
            return legal.build_offense_action("outside_zone", "conservative")
        if down >= 3 and distance >= 6:
            return legal.build_offense_action("bunch_mesh", "balanced")
        return legal.build_offense_action("rpo_glance", "balanced")
