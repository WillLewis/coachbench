from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, OffenseAction


class AdaptiveOffense:
    name = "Team B Adaptive Offense"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.adaptation_speed = float(self.config.get("adaptation_speed", 0.7))
        self.screen_trigger_confidence = float(self.config.get("screen_trigger_confidence", 0.62))
        self.explosive_shot_tolerance = float(self.config.get("explosive_shot_tolerance", 0.45))

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction:
        beliefs = memory.beliefs
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        stress_threshold = max(0.3, 0.62 - (self.adaptation_speed * 0.28))
        screen_trap_ceiling = max(0.25, 0.75 - (self.screen_trigger_confidence * 0.48))
        pressure_threshold = max(0.25, 0.64 - (self.screen_trigger_confidence * 0.35))

        if memory.own_recent_calls.count("play_action_flood") >= 2:
            return legal.build_offense_action("quick_game", "balanced")
        if beliefs.match_coverage_stress > stress_threshold:
            return legal.build_offense_action("bunch_mesh", "balanced")
        if beliefs.screen_trap_risk < screen_trap_ceiling and beliefs.true_pressure_confidence > pressure_threshold:
            return legal.build_offense_action("screen", "balanced")
        if beliefs.run_fit_aggression > stress_threshold:
            return legal.build_offense_action("play_action_flood", "balanced")
        if tendencies.get("wide_zone_constrained", 0) >= 1:
            return legal.build_offense_action("quick_game", "balanced")
        if down == 1:
            return legal.build_offense_action("outside_zone", "conservative")
        if down >= 3 and distance >= 6:
            return legal.build_offense_action("bunch_mesh", "balanced")
        return legal.build_offense_action("rpo_glance", "balanced")
