from __future__ import annotations

from typing import Iterable

from .schema import AgentMemory, PlayResolution


def update_beliefs(offense_memory: AgentMemory, defense_memory: AgentMemory, event_tags: Iterable[str]) -> None:
    tags = set(event_tags)

    if "screen_baited" in tags or "simulated_pressure_revealed" in tags:
        offense_memory.beliefs.simulated_pressure_risk += 0.22
        offense_memory.beliefs.screen_trap_risk += 0.24
        offense_memory.beliefs.true_pressure_confidence -= 0.12

    if "pressure_punished" in tags:
        offense_memory.beliefs.true_pressure_confidence += 0.16
        defense_memory.beliefs.screen_trap_risk += 0.12

    if "coverage_switch_stress" in tags or "nickel_passoff_test" in tags:
        offense_memory.beliefs.match_coverage_stress += 0.20
        defense_memory.beliefs.match_coverage_stress += 0.16

    if "wide_zone_constrained" in tags or "front_strength_declared" in tags:
        offense_memory.beliefs.run_fit_aggression += 0.18
        defense_memory.beliefs.run_fit_aggression += 0.10

    if "underneath_space_taken" in tags:
        defense_memory.beliefs.match_coverage_stress += 0.08

    if "run_tendency_exploited" in tags:
        defense_memory.beliefs.run_fit_aggression += 0.08

    offense_memory.beliefs.clamp()
    defense_memory.beliefs.clamp()
