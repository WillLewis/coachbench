from __future__ import annotations

from typing import Any

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, OffenseAction


class TemplateOffense:
    """Starter offense agent.

    Protocol:
      name: str
      choose_action(observation, memory, legal) -> OffenseAction

    Pre-play observation contains:
      game_state: public down, distance, yardline, play index, points, terminal
      legal_concepts: currently legal offense concepts
      own_resource_remaining: this side's remaining resource budget

    AgentMemory exposes:
      own_recent_calls: your recent concept ids
      opponent_visible_tendencies: event-derived tendency counts
      beliefs: public belief values such as screen_trap_risk and run_fit_aggression

    LegalActionFacade exposes:
      legal_offense_concepts()
      build_offense_action(concept, risk_level="balanced")

    It does not expose the graph, interaction matrix, hidden opponent calls, or debug fields.

    Forbidden patterns:
      do not access hidden engine fields
      do not return an action whose constraint_tag does not start with "legal:"
      do not introspect the opponent's pre-commit action
    """

    name = "Template Offense"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def choose_action(
        self,
        observation: dict[str, Any],
        memory: AgentMemory,
        legal: LegalActionFacade,
    ) -> OffenseAction:
        concepts = legal.legal_offense_concepts()
        return legal.build_offense_action(concepts[0], "conservative")
