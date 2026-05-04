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
from .roster_budget import RosterBudget, defense_modifier, has_nonzero_modifier, offense_modifier
from .matchup_traits import MatchupTraits, defense_trait_modifier, has_nonzero_trait_modifier, offense_trait_modifier
from .scouting import ScoutingReport, belief_calibration_error
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
        offense_roster: RosterBudget | None = None,
        defense_roster: RosterBudget | None = None,
        matchup_traits: MatchupTraits | None = None,
        offense_scouting: ScoutingReport | None = None,
        defense_scouting: ScoutingReport | None = None,
    ) -> Dict[str, Any]:
        state = GameState(max_plays=max_plays, yardline=start_yardline)
        initial_state = state
        offense_resources = dict(self.graph.constraints["drive_budgets"]["offense"])
        defense_resources = dict(self.graph.constraints["drive_budgets"]["defense"])
        offense_memory = AgentMemory()
        defense_memory = AgentMemory()
        play_results = []
        invalid_action_count = 0

        if offense_scouting and hasattr(offense_agent, "pre_drive_observation"):
            offense_agent.pre_drive_observation(offense_scouting.to_agent_dict())
        if defense_scouting and hasattr(defense_agent, "pre_drive_observation"):
            defense_agent.pre_drive_observation(defense_scouting.to_agent_dict())

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

            hidden_modifier = (0.0, 0.0, 0)
            active_matchup_traits = bool(matchup_traits and has_nonzero_trait_modifier(matchup_traits))
            if active_matchup_traits and matchup_traits:
                off_epa, off_succ, off_noise = offense_trait_modifier(matchup_traits, offense_action.concept_family)
                def_epa, def_succ, def_noise = defense_trait_modifier(matchup_traits, defense_action.coverage_family)
                hidden_modifier = (
                    max(-0.15, min(0.15, off_epa + def_epa)),
                    max(-0.10, min(0.10, off_succ + def_succ)),
                    int(max(-2, min(2, off_noise + def_noise))),
                )

            if offense_roster or defense_roster or active_matchup_traits:
                result = self.resolution.resolve(
                    state,
                    offense_action,
                    defense_action,
                    offense_memory,
                    defense_memory,
                    offense_modifier(offense_roster, offense_action.concept_family) if offense_roster else (0.0, 0.0),
                    defense_modifier(defense_roster, defense_action.coverage_family) if defense_roster else (0.0, 0.0),
                    hidden_modifier,
                )
            else:
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

        replay_agent_garage_config = dict(agent_garage_config or {})
        if (
            (offense_roster and has_nonzero_modifier(offense_roster))
            or (defense_roster and has_nonzero_modifier(defense_roster))
        ):
            replay_agent_garage_config["rosters"] = {
                "offense": offense_roster.to_public_dict() if offense_roster else None,
                "defense": defense_roster.to_public_dict() if defense_roster else None,
            }
        if matchup_traits and has_nonzero_trait_modifier(matchup_traits):
            replay_agent_garage_config["matchup_traits"] = matchup_traits.to_public_dict()
        if offense_scouting or defense_scouting:
            replay_agent_garage_config["scouting"] = {
                "offense": offense_scouting.to_public_dict() if offense_scouting else None,
                "defense": defense_scouting.to_public_dict() if defense_scouting else None,
            }

        replay = build_replay(
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
            agent_garage_config=replay_agent_garage_config,
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
        if matchup_traits and has_nonzero_trait_modifier(matchup_traits):
            last_play = play_results[-1] if play_results else None
            offense_belief = last_play["offense_observed"]["belief_after"] if last_play else {}
            defense_belief = last_play["defense_observed"]["belief_after"] if last_play else {}
            replay["inference_report"] = {
                "report_id": f"inference_{replay['metadata']['episode_id']}",
                "matchup_id": matchup_traits.matchup_id,
                "offense_calibration": belief_calibration_error(matchup_traits, offense_belief),
                "defense_calibration": belief_calibration_error(matchup_traits, defense_belief),
                "scouting_used": bool(offense_scouting or defense_scouting),
                "notes": "Calibration is observational, not a quality gate.",
            }
        return replay
