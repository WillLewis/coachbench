from __future__ import annotations

import random
from typing import Optional

from .belief import update_beliefs
from .graph_loader import StrategyGraph
from .interaction_engine import ConceptInteractionEngine
from .schema import AgentMemory, DefenseAction, GameState, OffenseAction, PlayResolution


class ResolutionEngine:
    def __init__(self, graph: StrategyGraph, rng: random.Random) -> None:
        self.graph = graph
        self.rng = rng
        self.interactions = ConceptInteractionEngine(graph)
        self.model = graph.resolution_model

    def resolve(
        self,
        state: GameState,
        offense_action: OffenseAction,
        defense_action: DefenseAction,
        offense_memory: AgentMemory,
        defense_memory: AgentMemory,
        offense_roster_modifier: tuple[float, float] = (0.0, 0.0),
        defense_roster_modifier: tuple[float, float] = (0.0, 0.0),
        hidden_trait_modifier: tuple[float, float, int] = (0.0, 0.0, 0),
    ) -> PlayResolution:
        interaction = self.interactions.evaluate(
            offense_action,
            defense_action,
            recent_offense=offense_memory.own_recent_calls,
        )
        base = self.graph.base_ep_for_offense(offense_action.concept_family)
        risk = self.model["risk_levels"].get(offense_action.risk_level, self.model["risk_levels"]["balanced"])
        expected_value = base + interaction["epa_modifier"] + float(risk["epa_modifier"])
        expected_value += float(offense_roster_modifier[0])
        expected_value -= float(defense_roster_modifier[0])
        expected_value += float(hidden_trait_modifier[0])
        success_bounds = self.model["success_probability_bounds"]
        raw_success_probability = (
            self.graph.base_success_for_offense(offense_action.concept_family)
            + interaction["success_modifier"]
            + float(risk["success_modifier"])
            + float(offense_roster_modifier[1])
            - float(defense_roster_modifier[1])
            + float(hidden_trait_modifier[1])
        )
        success_probability = max(
            float(success_bounds["minimum"]),
            min(float(success_bounds["maximum"]), raw_success_probability),
        )
        success = self.rng.random() < success_probability

        yards_model = self.model["yardage_model"]
        noise = self.rng.randint(int(yards_model["noise_min"]), int(yards_model["noise_max"])) + int(hidden_trait_modifier[2])
        if success:
            yards = max(
                int(yards_model["minimum_success_yards"]),
                int(
                    float(yards_model["success_base_yards"])
                    + expected_value * float(yards_model["success_ep_multiplier"])
                    + noise
                ),
            )
        else:
            yards = min(
                int(yards_model["maximum_failure_yards"]),
                int(expected_value * float(yards_model["failure_ep_multiplier"]) + noise),
            )

        turnover_model = self.model["turnover_model"]
        turnover_probability = max(
            float(turnover_model["minimum_probability"]),
            float(turnover_model["baseline_probability"])
            + float(risk["turnover_modifier"])
            + float(interaction["turnover_modifier"]),
        )

        terminal = False
        terminal_reason: Optional[str] = None
        points = state.points
        next_yardline = max(0, state.yardline - yards)
        if yards >= state.distance:
            next_down = 1
            next_distance = min(10, max(1, next_yardline))
        else:
            next_down = state.down + 1
            next_distance = max(1, state.distance - yards)

        if (
            self.rng.random() < turnover_probability
            and offense_action.concept_family in set(turnover_model["eligible_offense_concepts"])
        ):
            terminal = True
            terminal_reason = "turnover"
            points = state.points
        elif next_yardline <= 0:
            terminal = True
            terminal_reason = "touchdown"
            points = int(self.model["touchdown_points"])
        elif state.play_index + 1 >= state.max_plays:
            terminal = True
            terminal_reason = "max_plays_reached"
            field_goal = self.model["field_goal_model"]
            points = int(field_goal["points"]) if next_yardline <= int(field_goal["max_yardline_for_attempt"]) else state.points
        elif next_down > 4:
            terminal = True
            terminal_reason = "turnover_on_downs"

        offense_event_tags = [
            event["tag"]
            for event in interaction["events"]
            if "offense" in event.get("visible_to", ["offense", "defense"])
        ]
        defense_event_tags = [
            event["tag"]
            for event in interaction["events"]
            if "defense" in event.get("visible_to", ["offense", "defense"])
        ]
        update_beliefs(offense_memory, defense_memory, offense_event_tags, defense_event_tags, self.graph.belief_model)
        offense_memory.remember_own_call(offense_action.concept_family)
        defense_memory.remember_own_call(defense_action.coverage_family)
        for tag in offense_event_tags:
            offense_memory.increment_tendency(tag)
        for tag in defense_event_tags:
            defense_memory.increment_tendency(tag)

        next_state = GameState(
            down=next_down,
            distance=next_distance,
            yardline=next_yardline,
            play_index=state.play_index + 1,
            max_plays=state.max_plays,
            points=points,
            terminal=terminal,
            terminal_reason=terminal_reason,
        )

        return PlayResolution(
            play_index=state.play_index + 1,
            offense_action=offense_action,
            defense_action=defense_action,
            events=interaction["events"],
            yards_gained=yards,
            expected_value_delta=expected_value,
            success=success,
            terminal=terminal,
            terminal_reason=terminal_reason,
            next_state=next_state,
            graph_card_ids=interaction["graph_card_ids"],
            offense_belief_after=offense_memory.beliefs.to_dict(),
            defense_belief_after=defense_memory.beliefs.to_dict(),
        )
