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

    def resolve(
        self,
        state: GameState,
        offense_action: OffenseAction,
        defense_action: DefenseAction,
        offense_memory: AgentMemory,
        defense_memory: AgentMemory,
    ) -> PlayResolution:
        interaction = self.interactions.evaluate(
            offense_action,
            defense_action,
            recent_offense=offense_memory.own_recent_calls,
        )
        base = self.graph.base_ep_for_offense(offense_action.concept_family)
        risk_adjustment = {
            "conservative": -0.08,
            "balanced": 0.0,
            "aggressive": 0.08,
        }.get(offense_action.risk_level, 0.0)
        expected_value = base + interaction["epa_modifier"] + risk_adjustment
        success_probability = max(0.05, min(0.90, 0.45 + interaction["success_modifier"] + risk_adjustment))
        success = self.rng.random() < success_probability

        noise = self.rng.randint(-2, 2)
        if success:
            yards = max(1, int(4 + expected_value * 4 + noise))
        else:
            yards = min(2, int(expected_value * 2 + noise))

        terminal = False
        terminal_reason: Optional[str] = None
        points = state.points
        next_yardline = max(0, state.yardline - yards)

        turnover_probability = max(0.01, 0.04 + (0.05 if offense_action.risk_level == "aggressive" else 0.0))
        if defense_action.coverage_family in {"trap_coverage", "zero_pressure"}:
            turnover_probability += 0.03

        if self.rng.random() < turnover_probability and offense_action.concept_family in {"vertical_shot", "screen", "rpo_glance"}:
            terminal = True
            terminal_reason = "turnover"
            points = state.points
        elif next_yardline <= 0:
            terminal = True
            terminal_reason = "touchdown"
            points = 7
        elif state.play_index + 1 >= state.max_plays:
            terminal = True
            terminal_reason = "max_plays_reached"
            points = 3 if next_yardline <= 8 else state.points
        elif yards >= state.distance:
            next_down = 1
            next_distance = min(10, max(1, next_yardline))
        else:
            next_down = state.down + 1
            next_distance = state.distance - yards
            if next_down > 4:
                terminal = True
                terminal_reason = "turnover_on_downs"

        if not terminal:
            if yards >= state.distance:
                next_down = 1
                next_distance = min(10, max(1, next_yardline))
            else:
                next_down = state.down + 1
                next_distance = max(1, state.distance - yards)
        else:
            next_down = state.down
            next_distance = max(1, state.distance - yards)

        event_tags = [event["tag"] for event in interaction["events"]]
        update_beliefs(offense_memory, defense_memory, event_tags)
        offense_memory.remember_own_call(offense_action.concept_family)
        defense_memory.remember_own_call(defense_action.coverage_family)
        offense_memory.increment_tendency(defense_action.coverage_family)
        defense_memory.increment_tendency(offense_action.concept_family)

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
