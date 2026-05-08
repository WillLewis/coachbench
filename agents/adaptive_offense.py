from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, OffenseAction


class AdaptiveOffense:
    name = "Team B Adaptive Offense"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        params = self.config.get("parameters", self.config)
        self.risk_tolerance = str(params.get("risk_tolerance", "medium"))
        self.adaptation_speed = float(params.get("adaptation_speed", 0.7))
        self.screen_trigger_confidence = float(params.get("screen_trigger_confidence", 0.62))
        self.explosive_shot_tolerance = float(params.get("explosive_shot_tolerance", 0.45))
        self.run_pass_tendency = str(params.get("run_pass_tendency", "balanced_pass"))

    def _risk_level(self, concept: str, base: str = "balanced") -> str:
        if self.risk_tolerance in {"high", "medium_high"} and concept in {
            "bunch_mesh",
            "play_action_flood",
            "quick_game",
            "rpo_glance",
            "screen",
            "vertical_shot",
        }:
            return "aggressive"
        if self.risk_tolerance in {"low", "medium_low"}:
            return "conservative"
        return base

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction:
        legal_concepts = set(observation["legal_concepts"])
        beliefs = memory.beliefs
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        stress_threshold = max(0.3, 0.62 - (self.adaptation_speed * 0.28))
        screen_trap_ceiling = max(0.25, 0.75 - (self.screen_trigger_confidence * 0.48))
        pressure_threshold = max(0.25, 0.64 - (self.screen_trigger_confidence * 0.35))
        adaptation_count = 1 if self.adaptation_speed >= 0.5 else 2
        shot_ready = (
            "vertical_shot" in legal_concepts
            and self.explosive_shot_tolerance >= 0.65
            and down >= 3
            and distance >= 6
        )

        def build(concept: str, base_risk: str = "balanced") -> OffenseAction:
            if concept in legal_concepts:
                return legal.build_offense_action(concept, self._risk_level(concept, base_risk))
            fallback = sorted(legal_concepts)[0]
            return legal.build_offense_action(fallback, self._risk_level(fallback, "conservative"))

        if self.explosive_shot_tolerance >= 0.85 and shot_ready:
            return build("vertical_shot", "aggressive")
        if memory.own_recent_calls.count("play_action_flood") >= 2:
            return build("quick_game")
        if self.run_pass_tendency == "constraint_heavy" and tendencies.get("wide_zone_constrained", 0) >= adaptation_count:
            if memory.own_recent_calls and memory.own_recent_calls[-1] in {"inside_zone", "outside_zone", "power_counter"}:
                return build("bootleg")
            if down >= 3 and distance >= 4 and beliefs.screen_trap_risk < 0.55:
                return build("screen")
        if (
            beliefs.match_coverage_stress > stress_threshold
            and tendencies.get("coverage_switch_stress", 0) >= adaptation_count
        ):
            return build("bunch_mesh")
        eager_screen = (
            self.screen_trigger_confidence <= 0.35
            and down >= 3
            and distance >= 4
            and beliefs.screen_trap_risk < 0.55
        )
        if (
            "screen" in legal_concepts
            and (
                (beliefs.screen_trap_risk < screen_trap_ceiling and beliefs.true_pressure_confidence > pressure_threshold)
                or eager_screen
            )
        ):
            return build("screen")
        if (
            beliefs.run_fit_aggression > stress_threshold
            and tendencies.get("wide_zone_constrained", 0) >= adaptation_count
        ):
            return build("play_action_flood")
        if tendencies.get("wide_zone_constrained", 0) >= adaptation_count:
            return build("quick_game")
        if self.run_pass_tendency == "pass_heavy":
            if down == 1:
                return build("quick_game")
            if down >= 3 and distance >= 6:
                return build("bunch_mesh")
        if self.run_pass_tendency == "run_to_play_action":
            if memory.own_recent_calls and memory.own_recent_calls[-1] in {"inside_zone", "outside_zone", "power_counter"}:
                return build("play_action_flood")
            if down == 1:
                return build("inside_zone", "conservative")
        if down == 1:
            return build("outside_zone", "conservative")
        if shot_ready:
            return build("vertical_shot", "aggressive")
        if down >= 3 and distance >= 6:
            return build("bunch_mesh")
        return build("rpo_glance")
