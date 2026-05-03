from __future__ import annotations

from typing import Dict, List

from .graph_loader import StrategyGraph
from .schema import DefenseAction, OffenseAction


class ActionValidationError(ValueError):
    def __init__(self, reasons: List[str]) -> None:
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons))


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

    def legal_offense_concepts(self, remaining_budget: Dict[str, int] | None = None) -> List[str]:
        per_call_budget = self.graph.constraints["budgets"]["offense"]
        budget = remaining_budget or self.graph.constraints["drive_budgets"]["offense"]
        costs = self.graph.constraints["offense_costs"]
        return [
            concept
            for concept, cost in costs.items()
            if _within_budget(cost, per_call_budget) and _within_budget(cost, budget)
        ]

    def legal_defense_calls(self, remaining_budget: Dict[str, int] | None = None) -> List[str]:
        per_call_budget = self.graph.constraints["budgets"]["defense"]
        budget = remaining_budget or self.graph.constraints["drive_budgets"]["defense"]
        costs = self.graph.constraints["defense_costs"]
        return [
            call
            for call, cost in costs.items()
            if _within_budget(cost, per_call_budget) and _within_budget(cost, budget)
        ]

    def build_offense_action(
        self,
        concept: str,
        risk_level: str = "balanced",
        remaining_budget: Dict[str, int] | None = None,
    ) -> OffenseAction:
        if concept not in self.legal_offense_concepts(remaining_budget):
            raise ActionValidationError([f"Illegal or resource-impossible offense concept: {concept}"])
        fields = self.graph.offense_concept(concept)["action_fields"]
        return _make_offense_action(concept, risk_level, fields)

    def build_defense_action(
        self,
        call: str,
        risk_level: str = "balanced",
        remaining_budget: Dict[str, int] | None = None,
    ) -> DefenseAction:
        if call not in self.legal_defense_calls(remaining_budget):
            raise ActionValidationError([f"Illegal or resource-impossible defense call: {call}"])
        fields = self.graph.defense_call(call)["action_fields"]
        return _make_defense_action(call, risk_level, fields)

    def validate_offense_action(self, action: OffenseAction, remaining_budget: Dict[str, int] | None = None) -> None:
        reasons = self.validate_offense_action_reasons(action, remaining_budget)
        if reasons:
            raise ActionValidationError(reasons)

    def validate_offense_action_reasons(
        self,
        action: OffenseAction,
        remaining_budget: Dict[str, int] | None = None,
    ) -> List[str]:
        reasons: List[str] = []
        concept = action.concept_family
        if concept not in self.legal_offense_concepts(remaining_budget):
            reasons.append(f"Invalid or resource-impossible offense concept: {concept}")
            return reasons

        allowed_risks = set(self.graph.resolution_model["risk_levels"])
        if action.risk_level not in allowed_risks:
            reasons.append(f"Invalid offense risk level: {action.risk_level}")

        expected = self.graph.offense_concept(concept)["action_fields"]
        actual = action.to_dict()
        for key, value in expected.items():
            if actual.get(key) != value:
                reasons.append(f"Invalid offense {key}: {actual.get(key)}")
        if action.constraint_tag != f"legal:{concept}":
            reasons.append(f"Invalid offense constraint_tag: {action.constraint_tag}")
        return reasons

    def validate_defense_action(self, action: DefenseAction, remaining_budget: Dict[str, int] | None = None) -> None:
        reasons = self.validate_defense_action_reasons(action, remaining_budget)
        if reasons:
            raise ActionValidationError(reasons)

    def validate_defense_action_reasons(
        self,
        action: DefenseAction,
        remaining_budget: Dict[str, int] | None = None,
    ) -> List[str]:
        reasons: List[str] = []
        call = action.coverage_family
        if call not in self.legal_defense_calls(remaining_budget):
            reasons.append(f"Invalid or resource-impossible defense call: {call}")
            return reasons

        allowed_risks = set(self.graph.resolution_model["risk_levels"])
        if action.risk_level not in allowed_risks:
            reasons.append(f"Invalid defense risk level: {action.risk_level}")

        expected = self.graph.defense_call(call)["action_fields"]
        actual = action.to_dict()
        for key, value in expected.items():
            if actual.get(key) != value:
                reasons.append(f"Invalid defense {key}: {actual.get(key)}")
        if action.constraint_tag != f"legal:{call}":
            reasons.append(f"Invalid defense constraint_tag: {action.constraint_tag}")
        return reasons

    def public_legal_sets(
        self,
        offense_remaining: Dict[str, int] | None = None,
        defense_remaining: Dict[str, int] | None = None,
    ) -> Dict[str, List[str]]:
        return {
            "offense": self.legal_offense_concepts(offense_remaining),
            "defense": self.legal_defense_calls(defense_remaining),
        }

    def restricted_api(
        self,
        offense_remaining: Dict[str, int] | None = None,
        defense_remaining: Dict[str, int] | None = None,
    ) -> "LegalActionFacade":
        offense_concepts = self.legal_offense_concepts(offense_remaining)
        defense_calls = self.legal_defense_calls(defense_remaining)
        return LegalActionFacade(
            offense_concepts=offense_concepts,
            defense_calls=defense_calls,
            offense_action_fields={
                concept: self.graph.offense_concept(concept)["action_fields"]
                for concept in offense_concepts
            },
            defense_action_fields={
                call: self.graph.defense_call(call)["action_fields"]
                for call in defense_calls
            },
            risk_levels=list(self.graph.resolution_model["risk_levels"]),
        )

    def fallback_offense_action(self, remaining_budget: Dict[str, int]) -> OffenseAction:
        legal = self.legal_offense_concepts(remaining_budget)
        if not legal:
            raise ActionValidationError(["No legal offense fallback available"])
        concept = min(legal, key=lambda item: (self.graph.base_ep_for_offense(item), item))
        return self.build_offense_action(concept, "conservative", remaining_budget)

    def fallback_defense_action(self, remaining_budget: Dict[str, int]) -> DefenseAction:
        legal = self.legal_defense_calls(remaining_budget)
        if not legal:
            raise ActionValidationError(["No legal defense fallback available"])
        call = min(legal, key=lambda item: (float(self.graph.defense_call(item)["base_ep_allowed"]), item))
        return self.build_defense_action(call, "conservative", remaining_budget)


class LegalActionFacade:
    """Agent-facing action API without graph or interaction access."""

    __slots__ = (
        "_offense_concepts",
        "_offense_concept_set",
        "_offense_action_fields",
        "_defense_calls",
        "_defense_call_set",
        "_defense_action_fields",
        "_risk_levels",
    )

    def __init__(
        self,
        offense_concepts: List[str],
        defense_calls: List[str],
        offense_action_fields: Dict[str, Dict[str, str]],
        defense_action_fields: Dict[str, Dict[str, str]],
        risk_levels: List[str],
    ) -> None:
        self._offense_concepts = tuple(offense_concepts)
        self._offense_concept_set = frozenset(offense_concepts)
        self._offense_action_fields = dict(offense_action_fields)
        self._defense_calls = tuple(defense_calls)
        self._defense_call_set = frozenset(defense_calls)
        self._defense_action_fields = dict(defense_action_fields)
        self._risk_levels = frozenset(risk_levels)

    def legal_offense_concepts(self) -> List[str]:
        return list(self._offense_concepts)

    def legal_defense_calls(self) -> List[str]:
        return list(self._defense_calls)

    def build_offense_action(self, concept: str, risk_level: str = "balanced") -> OffenseAction:
        if concept not in self._offense_concept_set:
            raise ActionValidationError([f"Illegal or resource-impossible offense concept: {concept}"])
        if risk_level not in self._risk_levels:
            raise ActionValidationError([f"Illegal offense risk level: {risk_level}"])
        return _make_offense_action(concept, risk_level, self._offense_action_fields[concept])

    def build_defense_action(self, call: str, risk_level: str = "balanced") -> DefenseAction:
        if call not in self._defense_call_set:
            raise ActionValidationError([f"Illegal or resource-impossible defense call: {call}"])
        if risk_level not in self._risk_levels:
            raise ActionValidationError([f"Illegal defense risk level: {risk_level}"])
        return _make_defense_action(call, risk_level, self._defense_action_fields[call])
