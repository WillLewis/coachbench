from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Dict, Protocol

from .action_legality import ActionValidationError, LegalActionFacade, LegalActionEnumerator
from .graph_loader import StrategyGraph
from .observations import (
    defense_observation_before_play,
    offense_observation_before_play,
    post_play_defense_observation,
    post_play_offense_observation,
    post_play_public_observation,
)
from .replay import build_replay
from .resolution_engine import ResolutionEngine
from .schema import AgentMemory, DefenseAction, GameState, OffenseAction


class OffenseAgent(Protocol):
    name: str
    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction: ...


class DefenseAgent(Protocol):
    name: str
    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionFacade) -> DefenseAction: ...


class CoachBenchEngine:
    def __init__(self, seed: int = 42, graph: StrategyGraph | None = None) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.graph = graph or StrategyGraph()
        self.legal = LegalActionEnumerator(self.graph)
        self.resolution = ResolutionEngine(self.graph, self.rng)

    def _legal_action_set_id(self, legal_sets: Dict[str, Any]) -> str:
        payload = json.dumps(legal_sets, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:12]

    def _spend_resources(self, remaining: Dict[str, int], costs: Dict[str, int]) -> Dict[str, int]:
        return {
            key: int(remaining[key]) - int(costs.get(key, 0))
            for key in remaining
        }

    def _resource_budget_snapshot(
        self,
        offense_action: OffenseAction,
        defense_action: DefenseAction,
        offense_before: Dict[str, int],
        defense_before: Dict[str, int],
        offense_after: Dict[str, int],
        defense_after: Dict[str, int],
    ) -> Dict[str, Any]:
        constraints = self.graph.constraints
        offense_cost = constraints["offense_costs"][offense_action.concept_family]
        defense_cost = constraints["defense_costs"][defense_action.coverage_family]
        return {
            "offense_drive_budget": dict(constraints["drive_budgets"]["offense"]),
            "offense_before": dict(offense_before),
            "offense_cost": dict(offense_cost),
            "offense_remaining": dict(offense_after),
            "defense_drive_budget": dict(constraints["drive_budgets"]["defense"]),
            "defense_before": dict(defense_before),
            "defense_cost": dict(defense_cost),
            "defense_remaining": dict(defense_after),
        }

    def _valid_side_result(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "reasons": [],
            "fallback_used": False,
            "fallback_action_source": None,
        }

    def _invalid_side_result(self, reasons: list[str]) -> Dict[str, Any]:
        return {
            "ok": False,
            "reasons": list(reasons),
            "fallback_used": True,
            "fallback_action_source": "validator_safe_fallback",
        }

    def _validation_result(self, offense_result: Dict[str, Any], defense_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ok": bool(offense_result["ok"] and defense_result["ok"]),
            "offense": offense_result,
            "defense": defense_result,
        }

    def run_drive(
        self,
        offense_agent: OffenseAgent,
        defense_agent: DefenseAgent,
        agent_garage_config: Dict[str, Any] | None = None,
        max_plays: int = 8,
        start_yardline: int = 22,
    ) -> Dict[str, Any]:
        state = GameState(max_plays=max_plays, yardline=start_yardline)
        initial_state = state
        offense_resources = dict(self.graph.constraints["drive_budgets"]["offense"])
        defense_resources = dict(self.graph.constraints["drive_budgets"]["defense"])
        offense_memory = AgentMemory()
        defense_memory = AgentMemory()
        play_results = []
        invalid_action_count = 0

        while not state.terminal:
            legal_sets = self.legal.public_legal_sets(offense_resources, defense_resources)
            off_obs = offense_observation_before_play(state, legal_sets["offense"], offense_resources)
            def_obs = defense_observation_before_play(state, legal_sets["defense"], defense_resources)
            agent_legal = self.legal.restricted_api(offense_resources, defense_resources)

            offense_validation = self._valid_side_result()
            defense_validation = self._valid_side_result()

            try:
                offense_action = offense_agent.choose_action(off_obs, offense_memory, agent_legal)
                self.legal.validate_offense_action(offense_action, offense_resources)
            except ActionValidationError as exc:
                offense_validation = self._invalid_side_result(exc.reasons)
                invalid_action_count += 1
                offense_action = self.legal.fallback_offense_action(offense_resources)

            try:
                defense_action = defense_agent.choose_action(def_obs, defense_memory, agent_legal)
                self.legal.validate_defense_action(defense_action, defense_resources)
            except ActionValidationError as exc:
                defense_validation = self._invalid_side_result(exc.reasons)
                invalid_action_count += 1
                defense_action = self.legal.fallback_defense_action(defense_resources)

            offense_resources_after = self._spend_resources(
                offense_resources,
                self.graph.constraints["offense_costs"][offense_action.concept_family],
            )
            defense_resources_after = self._spend_resources(
                defense_resources,
                self.graph.constraints["defense_costs"][defense_action.coverage_family],
            )

            result = self.resolution.resolve(state, offense_action, defense_action, offense_memory, defense_memory)
            engine_internal = result.to_dict()
            engine_internal["legal_action_set_id"] = self._legal_action_set_id(legal_sets)
            engine_internal["legal_action_sets"] = legal_sets
            engine_internal["resource_budget_snapshot"] = self._resource_budget_snapshot(
                offense_action,
                defense_action,
                offense_resources,
                defense_resources,
                offense_resources_after,
                defense_resources_after,
            )
            engine_internal["validation_result"] = self._validation_result(offense_validation, defense_validation)
            public_result = post_play_public_observation(result)
            public_result["legal_action_set_id"] = engine_internal["legal_action_set_id"]
            public_result["legal_action_sets"] = legal_sets
            public_result["resource_budget_snapshot"] = engine_internal["resource_budget_snapshot"]
            public_result["validation_result"] = engine_internal["validation_result"]
            play_results.append({
                "public": public_result,
                "offense_observed": post_play_offense_observation(result),
                "defense_observed": post_play_defense_observation(result),
                "engine_internal": engine_internal,
            })
            offense_resources = offense_resources_after
            defense_resources = defense_resources_after
            state = result.next_state

        return build_replay(
            seed=self.seed,
            start_yardline=initial_state.yardline,
            max_plays=initial_state.max_plays,
            initial_down=initial_state.down,
            initial_distance=initial_state.distance,
            drive_terminal_condition=state.terminal_reason or "unknown",
            graph_version=str(self.graph.meta.get("version", "unknown")),
            engine_version="0.1.0",
            offense_agent=offense_agent.name,
            defense_agent=defense_agent.name,
            agent_garage_config=agent_garage_config or {},
            play_results=play_results,
            final_points=state.points,
            invalid_action_count=invalid_action_count,
            touchdown_points=int(self.graph.resolution_model["touchdown_points"]),
            field_goal_points=int(self.graph.resolution_model["field_goal_model"]["points"]),
            legal_sets=self.legal.public_legal_sets(
                self.graph.constraints["drive_budgets"]["offense"],
                self.graph.constraints["drive_budgets"]["defense"],
            ),
            graph=self.graph,
        )
