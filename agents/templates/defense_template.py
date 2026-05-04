from __future__ import annotations

from typing import Any

from coachbench.action_legality import LegalActionFacade
from coachbench.schema import AgentMemory, DefenseAction


class TemplateDefense:
    """Starter defense agent.

    Protocol:
      name: str
      choose_action(observation, memory, legal) -> DefenseAction

    Pre-play observation contains:
      game_state: public down, distance, yardline, play index, points, terminal
      legal_calls: currently legal defense calls
      own_resource_remaining: this side's remaining resource budget

    AgentMemory exposes:
      own_recent_calls: your recent call ids
      opponent_visible_tendencies: event-derived tendency counts
      beliefs: public belief values such as match_coverage_stress and run_fit_aggression

    LegalActionFacade exposes:
      legal_defense_calls()
      build_defense_action(call, risk_level="balanced")

    It does not expose the graph, interaction matrix, hidden opponent calls, or debug fields.

    Forbidden patterns:
      do not access hidden engine fields
      do not return an action whose constraint_tag does not start with "legal:"
      do not introspect the opponent's pre-commit action
    """

    name = "Template Defense"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def choose_action(
        self,
        observation: dict[str, Any],
        memory: AgentMemory,
        legal: LegalActionFacade,
    ) -> DefenseAction:
        calls = legal.legal_defense_calls()
        return legal.build_defense_action(calls[0], "conservative")
