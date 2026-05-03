from __future__ import annotations

from typing import Dict, List

from .graph_loader import StrategyGraph
from .schema import DefenseAction, OffenseAction


class ActionValidationError(ValueError):
    pass


def _within_budget(costs: Dict[str, int], budget: Dict[str, int]) -> bool:
    return all(int(costs.get(key, 0)) <= int(budget.get(key, 0)) for key in budget)


def _make_offense_action(concept: str, risk_level: str, action_fields: Dict[str, str]) -> OffenseAction:
    return OffenseAction(
        personnel_family=action_fields["personnel_family"],
        formation_family=action_fields["formation_family"],
        motion_family=action_fields["motion_family"],
        concept_family=concept,
        protection_family=action_fields["protection_family"],
        risk_level=risk_level,
        constraint_tag=f"legal:{concept}",
    )


def _make_defense_action(call: str, risk_level: str, action_fields: Dict[str, str]) -> DefenseAction:
    return DefenseAction(
        personnel_family=action_fields["personnel_family"],
        front_family=action_fields["front_family"],
        coverage_family=call,
        pressure_family=action_fields["pressure_family"],
        disguise_family=action_fields["disguise_family"],
        matchup_focus=action_fields["matchup_focus"],
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
        fields = self.graph.offense_concept(concept)["action_fields"]
        return _make_offense_action(concept, risk_level, fields)

    def build_defense_action(self, call: str, risk_level: str = "balanced") -> DefenseAction:
        if call not in self.legal_defense_calls():
            raise ActionValidationError(f"Illegal or resource-impossible defense call: {call}")
        fields = self.graph.defense_call(call)["action_fields"]
        return _make_defense_action(call, risk_level, fields)

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
            offense_action_fields={
                concept: self.graph.offense_concept(concept)["action_fields"]
                for concept in self.legal_offense_concepts()
            },
            defense_action_fields={
                call: self.graph.defense_call(call)["action_fields"]
                for call in self.legal_defense_calls()
            },
        )


class LegalActionFacade:
    """Agent-facing action API without graph or interaction access."""

    __slots__ = (
        "_offense_concepts",
        "_offense_concept_set",
        "_offense_action_fields",
        "_defense_calls",
        "_defense_call_set",
        "_defense_action_fields",
    )

    def __init__(
        self,
        offense_concepts: List[str],
        defense_calls: List[str],
        offense_action_fields: Dict[str, Dict[str, str]],
        defense_action_fields: Dict[str, Dict[str, str]],
    ) -> None:
        self._offense_concepts = tuple(offense_concepts)
        self._offense_concept_set = frozenset(offense_concepts)
        self._offense_action_fields = dict(offense_action_fields)
        self._defense_calls = tuple(defense_calls)
        self._defense_call_set = frozenset(defense_calls)
        self._defense_action_fields = dict(defense_action_fields)

    def legal_offense_concepts(self) -> List[str]:
        return list(self._offense_concepts)

    def legal_defense_calls(self) -> List[str]:
        return list(self._defense_calls)

    def build_offense_action(self, concept: str, risk_level: str = "balanced") -> OffenseAction:
        if concept not in self._offense_concept_set:
            raise ActionValidationError(f"Illegal or resource-impossible offense concept: {concept}")
        return _make_offense_action(concept, risk_level, self._offense_action_fields[concept])

    def build_defense_action(self, call: str, risk_level: str = "balanced") -> DefenseAction:
        if call not in self._defense_call_set:
            raise ActionValidationError(f"Illegal or resource-impossible defense call: {call}")
        return _make_defense_action(call, risk_level, self._defense_action_fields[call])
