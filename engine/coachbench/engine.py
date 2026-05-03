from __future__ import annotations

import random
from typing import Any, Dict, Protocol

from .action_legality import LegalActionEnumerator
from .graph_loader import StrategyGraph
from .observations import defense_observation_before_play, offense_observation_before_play, post_play_public_observation
from .replay import build_replay
from .resolution_engine import ResolutionEngine
from .schema import AgentMemory, DefenseAction, GameState, OffenseAction


class OffenseAgent(Protocol):
    name: str
    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionEnumerator) -> OffenseAction: ...


class DefenseAgent(Protocol):
    name: str
    def choose_action(self, observation: Dict[str, Any], memory: AgentMemory, legal: LegalActionEnumerator) -> DefenseAction: ...


class CoachBenchEngine:
    def __init__(self, seed: int = 42, graph: StrategyGraph | None = None) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.graph = graph or StrategyGraph()
        self.legal = LegalActionEnumerator(self.graph)
        self.resolution = ResolutionEngine(self.graph, self.rng)

    def run_drive(
        self,
        offense_agent: OffenseAgent,
        defense_agent: DefenseAgent,
        agent_garage_config: Dict[str, Any] | None = None,
        max_plays: int = 8,
    ) -> Dict[str, Any]:
        state = GameState(max_plays=max_plays)
        offense_memory = AgentMemory()
        defense_memory = AgentMemory()
        play_results = []

        while not state.terminal:
            off_obs = offense_observation_before_play(state, "shell_unconfirmed", self.legal.legal_offense_concepts())
            def_obs = defense_observation_before_play(state, "compact_offense", self.legal.legal_defense_calls())

            offense_action = offense_agent.choose_action(off_obs, offense_memory, self.legal)
            defense_action = defense_agent.choose_action(def_obs, defense_memory, self.legal)
            self.legal.validate_offense_action(offense_action)
            self.legal.validate_defense_action(defense_action)

            result = self.resolution.resolve(state, offense_action, defense_action, offense_memory, defense_memory)
            public_result = result.to_dict()
            public_result["public_observation"] = post_play_public_observation(result)
            play_results.append(public_result)
            state = result.next_state

        return build_replay(
            seed=self.seed,
            graph_version=str(self.graph.meta.get("version", "unknown")),
            engine_version="0.1.0",
            offense_agent=offense_agent.name,
            defense_agent=defense_agent.name,
            agent_garage_config=agent_garage_config or {},
            play_results=play_results,
            final_points=state.points,
            legal_sets=self.legal.public_legal_sets(),
        )
