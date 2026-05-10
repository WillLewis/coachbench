from __future__ import annotations

from typing import Any


class NetworkAgent:
    requires_network: bool = True
    name: str = "NetworkAgent"

    def observe(self, observation: dict[str, Any]) -> None:
        pass

    def choose_action(self, observation: dict[str, Any], memory: Any = None, legal: Any = None) -> Any:
        if observation.get("legal_concepts"):
            concept = observation["legal_concepts"][0]
            return legal.build_offense_action(concept, "conservative") if legal else concept
        call = observation["legal_calls"][0]
        return legal.build_defense_action(call, "conservative") if legal else call
