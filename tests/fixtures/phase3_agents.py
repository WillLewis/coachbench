from __future__ import annotations

from typing import Any

from coachbench.schema import OffenseAction


class NoChooseActionAgent:
    name = "No Choose Action"


class IllegalConceptOffense:
    name = "Illegal Concept Offense"

    def choose_action(self, observation: dict[str, Any], memory: Any, legal: Any) -> OffenseAction:
        return OffenseAction(
            personnel_family="fictional_11",
            formation_family="compact",
            motion_family="none",
            concept_family="not_in_graph",
            protection_family="standard",
            risk_level="balanced",
            constraint_tag="legal:not_in_graph",
        )


class MutatingLeakyOffense:
    name = "Mutating Leaky Offense"

    def choose_action(self, observation: dict[str, Any], memory: Any, legal: Any) -> OffenseAction:
        observation["debug"] = "attempted hidden-field access"
        return legal.build_offense_action("inside_zone", "conservative")
