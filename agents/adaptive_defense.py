from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, DefenseAction


class AdaptiveDefense:
    name = "Team B Adaptive Defense"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.disguise_sensitivity = float(self.config.get("disguise_sensitivity", 0.85))
        self.pressure_frequency = float(self.config.get("pressure_frequency", 0.4))
        self.counter_repeat_tolerance = float(self.config.get("counter_repeat_tolerance", 0.55))

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> DefenseAction:
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        counter_threshold = 1 if self.counter_repeat_tolerance <= 0.6 else 2

        if tendencies.get("screen_baited", 0) >= 1 or tendencies.get("pressure_punished", 0) >= 1:
            return legal.build_defense_action("trap_coverage", "balanced")
        if tendencies.get("run_tendency_exploited", 0) >= 2:
            return legal.build_defense_action("redzone_bracket", "balanced")
        if tendencies.get("coverage_switch_stress", 0) >= counter_threshold:
            return legal.build_defense_action("redzone_bracket", "balanced")
        if tendencies.get("wide_zone_constrained", 0) >= 1:
            return legal.build_defense_action("bear_front", "balanced")
        if down >= 3 and distance >= 6 and self.disguise_sensitivity >= 0.5:
            return legal.build_defense_action("simulated_pressure", "balanced")
        if down == 1 and self.pressure_frequency < 0.5:
            return legal.build_defense_action("bear_front", "balanced")
        if down == 1:
            return legal.build_defense_action("simulated_pressure", "balanced")
        return legal.build_defense_action("cover3_match", "balanced")
