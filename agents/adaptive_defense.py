from __future__ import annotations

from typing import Any, Dict

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, DefenseAction


class AdaptiveDefense:
    name = "Team B Adaptive Defense"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        params = self.config.get("parameters", self.config)
        self.risk_tolerance = str(params.get("risk_tolerance", "medium"))
        self.disguise_sensitivity = float(params.get("disguise_sensitivity", 0.85))
        self.pressure_frequency = float(params.get("pressure_frequency", 0.4))
        self.counter_repeat_tolerance = float(params.get("counter_repeat_tolerance", 0.55))

    def _risk_level(self, call: str, base: str = "balanced") -> str:
        if self.risk_tolerance in {"high", "medium_high"} and call in {
            "simulated_pressure",
            "trap_coverage",
            "zero_pressure",
        }:
            return "aggressive"
        if self.risk_tolerance in {"low", "medium_low"}:
            return "conservative"
        return base

    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> DefenseAction:
        legal_calls = set(observation["legal_calls"])
        tendencies = memory.opponent_visible_tendencies
        down = int(observation["game_state"]["down"])
        distance = int(observation["game_state"]["distance"])
        counter_threshold = 1 if self.counter_repeat_tolerance <= 0.6 else 3

        def build(call: str, base_risk: str = "balanced") -> DefenseAction:
            if call in legal_calls:
                return legal.build_defense_action(call, self._risk_level(call, base_risk))
            fallback = sorted(legal_calls)[0]
            return legal.build_defense_action(fallback, self._risk_level(fallback, "conservative"))

        if tendencies.get("screen_baited", 0) >= 1 or tendencies.get("pressure_punished", 0) >= 1:
            return build("trap_coverage")
        if (
            down >= 3
            and distance >= 6
            and self.risk_tolerance in {"high", "medium_high"}
            and self.disguise_sensitivity <= 0.45
            and self.pressure_frequency < 0.75
        ):
            return build("cover1_man", "aggressive")
        if tendencies.get("run_tendency_exploited", 0) >= 2:
            return build("redzone_bracket")
        if tendencies.get("coverage_switch_stress", 0) >= counter_threshold:
            return build("redzone_bracket")
        if tendencies.get("wide_zone_constrained", 0) >= 1:
            return build("bear_front")
        if down >= 3 and distance >= 6 and self.risk_tolerance in {"low", "medium_low"}:
            return build("two_high_shell", "conservative")
        if down >= 3 and distance >= 6 and self.pressure_frequency >= 0.75 and self.risk_tolerance in {"high", "medium_high"}:
            return build("zero_pressure", "aggressive")
        if down >= 3 and distance >= 6 and self.disguise_sensitivity >= 0.5:
            return build("simulated_pressure")
        if down == 1 and self.pressure_frequency < 0.5:
            return build("bear_front")
        if down == 1:
            return build("simulated_pressure")
        return build("cover3_match")
