from __future__ import annotations

from typing import Any

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, DefenseAction, OffenseAction


class ExampleCustomOffense:
    """Illustrative local offense using only public observations and memory."""

    name = "Example Custom Offense"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        params = self.config.get("parameters", self.config)
        self.screen_trigger_confidence = float(params.get("screen_trigger_confidence", 0.6))
        self.explosive_shot_tolerance = float(params.get("explosive_shot_tolerance", 0.45))

    def choose_action(
        self,
        observation: dict[str, Any],
        memory: AgentMemory,
        legal: LegalActionFacade,
    ) -> OffenseAction:
        concepts = set(observation["legal_concepts"])
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        beliefs = memory.beliefs
        tendencies = memory.opponent_visible_tendencies

        if "screen" in concepts and beliefs.true_pressure_confidence >= self.screen_trigger_confidence:
            return legal.build_offense_action("screen", "balanced")
        if "quick_game" in concepts and beliefs.screen_trap_risk > 0.45:
            return legal.build_offense_action("quick_game", "balanced")
        if "play_action_flood" in concepts and tendencies.get("wide_zone_constrained", 0) >= 1:
            return legal.build_offense_action("play_action_flood", "balanced")
        if "bunch_mesh" in concepts and beliefs.match_coverage_stress > 0.5:
            return legal.build_offense_action("bunch_mesh", "balanced")
        if "vertical_shot" in concepts and down >= 3 and distance >= 6 and self.explosive_shot_tolerance > 0.6:
            return legal.build_offense_action("vertical_shot", "aggressive")
        if "outside_zone" in concepts and down == 1:
            return legal.build_offense_action("outside_zone", "conservative")
        return legal.build_offense_action(sorted(concepts)[0], "conservative")


class ExampleCustomDefense:
    """Illustrative local defense using event-derived tendencies and beliefs."""

    name = "Example Custom Defense"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        params = self.config.get("parameters", self.config)
        self.disguise_sensitivity = float(params.get("disguise_sensitivity", 0.55))
        self.counter_repeat_tolerance = float(params.get("counter_repeat_tolerance", 0.5))

    def choose_action(
        self,
        observation: dict[str, Any],
        memory: AgentMemory,
        legal: LegalActionFacade,
    ) -> DefenseAction:
        calls = set(observation["legal_calls"])
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        tendencies = memory.opponent_visible_tendencies
        beliefs = memory.beliefs

        if "trap_coverage" in calls and tendencies.get("screen_baited", 0) >= 1:
            return legal.build_defense_action("trap_coverage", "balanced")
        if "redzone_bracket" in calls and beliefs.match_coverage_stress > self.counter_repeat_tolerance:
            return legal.build_defense_action("redzone_bracket", "balanced")
        if "simulated_pressure" in calls and down >= 3 and distance >= 6 and self.disguise_sensitivity >= 0.5:
            return legal.build_defense_action("simulated_pressure", "balanced")
        if "bear_front" in calls and down == 1:
            return legal.build_defense_action("bear_front", "balanced")
        if "two_high_shell" in calls and distance >= 7:
            return legal.build_defense_action("two_high_shell", "conservative")
        return legal.build_defense_action(sorted(calls)[0], "conservative")
