from __future__ import annotations

from typing import Dict, List

from .graph_loader import StrategyGraph
from .schema import DefenseAction, OffenseAction


class ActionValidationError(ValueError):
    pass


def _within_budget(costs: Dict[str, int], budget: Dict[str, int]) -> bool:
    return all(int(costs.get(key, 0)) <= int(budget.get(key, 0)) for key in budget)


def _make_offense_action(concept: str, risk_level: str) -> OffenseAction:
    return OffenseAction(
        personnel_family="fictional_11",
        formation_family="bunch" if concept == "bunch_mesh" else "compact",
        motion_family="orbit" if concept in {"rpo_glance", "screen"} else "none",
        concept_family=concept,
        protection_family="max" if concept == "vertical_shot" else "standard",
        risk_level=risk_level,
        constraint_tag=f"legal:{concept}",
    )


def _make_defense_action(call: str, risk_level: str) -> DefenseAction:
    return DefenseAction(
        personnel_family="fictional_nickel",
        front_family="bear" if call == "bear_front" else "even",
        coverage_family=call,
        pressure_family="pressure" if "pressure" in call else "four_man",
        disguise_family="late" if call in {"simulated_pressure", "trap_coverage"} else "none",
        matchup_focus="red_zone_space",
        risk_level=risk_level,
        constraint_tag=f"legal:{call}",
    )


class LegalActionEnumerator:
    def __init__(self, graph: StrategyGraph) -> None:
        self.graph = graph

    def legal_offense_concepts(self) -> List[str]:
        budget = self.graph.constraints["budgets"]["offense"]
        costs = self.graph.constraints["offense_costs"]
        return [concept for concept, cost in costs.items() if _within_budget(cost, budget)]

    def legal_defense_calls(self) -> List[str]:
        budget = self.graph.constraints["budgets"]["defense"]
        costs = self.graph.constraints["defense_costs"]
        return [call for call, cost in costs.items() if _within_budget(cost, budget)]

    def build_offense_action(self, concept: str, risk_level: str = "balanced") -> OffenseAction:
        if concept not in self.legal_offense_concepts():
            raise ActionValidationError(f"Illegal or resource-impossible offense concept: {concept}")
        return _make_offense_action(concept, risk_level)

    def build_defense_action(self, call: str, risk_level: str = "balanced") -> DefenseAction:
        if call not in self.legal_defense_calls():
            raise ActionValidationError(f"Illegal or resource-impossible defense call: {call}")
        return _make_defense_action(call, risk_level)

    def validate_offense_action(self, action: OffenseAction) -> None:
        concept = action.concept_family
        if concept not in self.legal_offense_concepts():
            raise ActionValidationError(f"Invalid offense concept: {concept}")

    def validate_defense_action(self, action: DefenseAction) -> None:
        call = action.coverage_family
        if call not in self.legal_defense_calls():
            raise ActionValidationError(f"Invalid defense call: {call}")

    def public_legal_sets(self) -> Dict[str, List[str]]:
        return {
            "offense": self.legal_offense_concepts(),
            "defense": self.legal_defense_calls(),
        }

    def restricted_api(self) -> "LegalActionFacade":
        return LegalActionFacade(
            offense_concepts=self.legal_offense_concepts(),
            defense_calls=self.legal_defense_calls(),
        )


class LegalActionFacade:
    """Agent-facing action API without graph or interaction access."""

    __slots__ = ("_offense_concepts", "_offense_concept_set", "_defense_calls", "_defense_call_set")

    def __init__(self, offense_concepts: List[str], defense_calls: List[str]) -> None:
        self._offense_concepts = tuple(offense_concepts)
        self._offense_concept_set = frozenset(offense_concepts)
        self._defense_calls = tuple(defense_calls)
        self._defense_call_set = frozenset(defense_calls)

    def legal_offense_concepts(self) -> List[str]:
        return list(self._offense_concepts)

    def legal_defense_calls(self) -> List[str]:
        return list(self._defense_calls)

    def build_offense_action(self, concept: str, risk_level: str = "balanced") -> OffenseAction:
        if concept not in self._offense_concept_set:
            raise ActionValidationError(f"Illegal or resource-impossible offense concept: {concept}")
        return _make_offense_action(concept, risk_level)

    def build_defense_action(self, call: str, risk_level: str = "balanced") -> DefenseAction:
        if call not in self._defense_call_set:
            raise ActionValidationError(f"Illegal or resource-impossible defense call: {call}")
        return _make_defense_action(call, risk_level)
