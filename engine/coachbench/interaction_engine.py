from __future__ import annotations

from typing import Any, Dict, List

from .graph_loader import StrategyGraph
from .schema import DefenseAction, OffenseAction


class ConceptInteractionEngine:
    def __init__(self, graph: StrategyGraph) -> None:
        self.graph = graph

    def evaluate(self, offense_action: OffenseAction, defense_action: DefenseAction, recent_offense: list[str]) -> Dict[str, Any]:
        offense_concept = offense_action.concept_family
        defense_call = defense_action.coverage_family
        matches = self.graph.matching_interactions(offense_concept, defense_call, recent_offense)
        events: List[Dict[str, Any]] = []
        epa_modifier = 0.0
        success_modifier = 0.0
        graph_card_ids: List[str] = []

        for item in matches:
            graph_card_ids.append(item["id"])
            epa_modifier += float(item.get("epa_modifier", 0.0))
            success_modifier += float(item.get("success_modifier", 0.0))
            for event in item.get("tactical_events", []):
                events.append({
                    "tag": event,
                    "graph_card_id": item["id"],
                    "description": item["name"],
                    "counters": item.get("counters", []),
                })

        return {
            "events": events,
            "epa_modifier": epa_modifier,
            "success_modifier": success_modifier,
            "graph_card_ids": graph_card_ids,
        }
