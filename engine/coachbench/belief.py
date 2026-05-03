from __future__ import annotations

from typing import Iterable

from .schema import AgentMemory


def update_beliefs(
    offense_memory: AgentMemory,
    defense_memory: AgentMemory,
    offense_event_tags: Iterable[str],
    defense_event_tags: Iterable[str],
) -> None:
    offense_tags = set(offense_event_tags)
    defense_tags = set(defense_event_tags)

    if "screen_baited" in offense_tags or "simulated_pressure_revealed" in offense_tags:
        offense_memory.beliefs.simulated_pressure_risk += 0.22
        offense_memory.beliefs.screen_trap_risk += 0.24
        offense_memory.beliefs.true_pressure_confidence -= 0.12

    if "screen_baited" in defense_tags:
        defense_memory.beliefs.screen_trap_risk += 0.12

    if "pressure_punished" in offense_tags:
        offense_memory.beliefs.true_pressure_confidence += 0.16

    if "pressure_punished" in defense_tags:
        defense_memory.beliefs.screen_trap_risk += 0.12

    if "coverage_switch_stress" in offense_tags or "nickel_passoff_test" in offense_tags:
        offense_memory.beliefs.match_coverage_stress += 0.20

    if "coverage_switch_stress" in defense_tags or "nickel_passoff_test" in defense_tags:
        defense_memory.beliefs.match_coverage_stress += 0.16

    if "wide_zone_constrained" in offense_tags or "front_strength_declared" in offense_tags:
        offense_memory.beliefs.run_fit_aggression += 0.18

    if "wide_zone_constrained" in defense_tags:
        defense_memory.beliefs.run_fit_aggression += 0.10

    if "underneath_space_taken" in defense_tags:
        defense_memory.beliefs.match_coverage_stress += 0.08

    if "run_tendency_exploited" in defense_tags:
        defense_memory.beliefs.run_fit_aggression += 0.08

    offense_memory.beliefs.clamp()
    defense_memory.beliefs.clamp()
