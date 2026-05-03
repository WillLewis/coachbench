from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class StrategyGraph:
    def __init__(self, graph_dir: Path | None = None) -> None:
        self.graph_dir = graph_dir or project_root() / "graph" / "redzone_v0"
        self.meta = self._load_json("graph.meta.json")
        self.concepts = self._load_json("concepts.json")
        self.constraints = self._load_json("resource_constraints.json")
        self.interactions = self._load_json("interactions.json")["interactions"]
        self.resolution_model = self._load_json("resolution_model.json")
        self.belief_model = self._load_json("belief_model.json")

    def _load_json(self, name: str) -> Dict[str, Any]:
        path = self.graph_dir / name
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def offense_concepts(self) -> List[str]:
        return [item["id"] for item in self.concepts["offense"]]

    def defense_calls(self) -> List[str]:
        return [item["id"] for item in self.concepts["defense"]]

    def base_ep_for_offense(self, concept: str) -> float:
        return float(self.offense_concept(concept)["base_ep"])

    def base_success_for_offense(self, concept: str) -> float:
        return float(self.offense_concept(concept)["base_success"])

    def offense_concept(self, concept: str) -> Dict[str, Any]:
        for item in self.concepts["offense"]:
            if item["id"] == concept:
                return item
        raise KeyError(f"Unknown offense concept: {concept}")

    def defense_call(self, call: str) -> Dict[str, Any]:
        for item in self.concepts["defense"]:
            if item["id"] == call:
                return item
        raise KeyError(f"Unknown defense call: {call}")

    def matching_interactions(self, offense_concept: str, defense_call: str, recent_offense: list[str]) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for interaction in self.interactions:
            if offense_concept not in interaction.get("offense_concepts", []):
                continue
            if defense_call not in interaction.get("defense_calls", []):
                continue
            trigger = interaction.get("sequence_trigger")
            if trigger:
                allowed = set(trigger.get("offense_recent", []))
                min_count = int(trigger.get("min_count", 1))
                count = sum(1 for item in recent_offense if item in allowed)
                if count < min_count:
                    continue
            matches.append(interaction)
        return matches
