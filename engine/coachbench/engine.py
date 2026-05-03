from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Dict, Protocol

from .action_legality import LegalActionFacade, LegalActionEnumerator
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

    def _legal_action_set_id(self) -> str:
        legal_sets = self.legal.public_legal_sets()
        payload = json.dumps(legal_sets, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:12]

    def _resource_budget_snapshot(self, offense_action: OffenseAction, defense_action: DefenseAction) -> Dict[str, Any]:
        constraints = self.graph.constraints
        offense_budget = constraints["budgets"]["offense"]
        defense_budget = constraints["budgets"]["defense"]
        offense_cost = constraints["offense_costs"][offense_action.concept_family]
        defense_cost = constraints["defense_costs"][defense_action.coverage_family]
        return {
            "offense_budget": dict(offense_budget),
            "offense_cost": dict(offense_cost),
            "offense_remaining": {
                key: int(offense_budget[key]) - int(offense_cost.get(key, 0))
                for key in offense_budget
            },
            "defense_budget": dict(defense_budget),
            "defense_cost": dict(defense_cost),
            "defense_remaining": {
                key: int(defense_budget[key]) - int(defense_cost.get(key, 0))
                for key in defense_budget
            },
        }

    def run_drive(
        self,
        offense_agent: OffenseAgent,
        defense_agent: DefenseAgent,
        agent_garage_config: Dict[str, Any] | None = None,
        max_plays: int = 8,
    ) -> Dict[str, Any]:
        state = GameState(max_plays=max_plays)
        initial_state = state
        offense_memory = AgentMemory()
        defense_memory = AgentMemory()
        play_results = []

        while not state.terminal:
            off_obs = offense_observation_before_play(state, self.legal.legal_offense_concepts())
            def_obs = defense_observation_before_play(state, self.legal.legal_defense_calls())
            agent_legal = self.legal.restricted_api()

            offense_action = offense_agent.choose_action(off_obs, offense_memory, agent_legal)
            defense_action = defense_agent.choose_action(def_obs, defense_memory, agent_legal)
            self.legal.validate_offense_action(offense_action)
            self.legal.validate_defense_action(defense_action)

            result = self.resolution.resolve(state, offense_action, defense_action, offense_memory, defense_memory)
            engine_internal = result.to_dict()
            engine_internal["legal_action_set_id"] = self._legal_action_set_id()
            engine_internal["resource_budget_snapshot"] = self._resource_budget_snapshot(offense_action, defense_action)
            engine_internal["validation_result"] = {
                "offense": "valid",
                "defense": "valid",
            }
            public_result = post_play_public_observation(result)
            public_result["legal_action_set_id"] = engine_internal["legal_action_set_id"]
            public_result["resource_budget_snapshot"] = engine_internal["resource_budget_snapshot"]
            public_result["validation_result"] = engine_internal["validation_result"]
            play_results.append({
                "public": public_result,
                "offense_observed": post_play_offense_observation(result),
                "defense_observed": post_play_defense_observation(result),
                "engine_internal": engine_internal,
            })
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
            touchdown_points=int(self.graph.resolution_model["touchdown_points"]),
            field_goal_points=int(self.graph.resolution_model["field_goal_model"]["points"]),
            legal_sets=self.legal.public_legal_sets(),
        )
