from __future__ import annotations

from typing import Any, Dict, List

from .schema import GameState, PlayResolution


def offense_observation_before_play(state: GameState, visible_defensive_shell: str, legal_concepts: List[str]) -> Dict[str, Any]:
    return {
        "side": "offense",
        "game_state": state.to_public_dict(),
        "visible_defensive_shell": visible_defensive_shell,
        "legal_concepts": list(legal_concepts),
    }


def defense_observation_before_play(state: GameState, visible_offensive_shape: str, legal_calls: List[str]) -> Dict[str, Any]:
    return {
        "side": "defense",
        "game_state": state.to_public_dict(),
        "visible_offensive_shape": visible_offensive_shape,
        "legal_calls": list(legal_calls),
    }


def post_play_public_observation(result: PlayResolution) -> Dict[str, Any]:
    return {
        "play_index": result.play_index,
        "yards_gained": result.yards_gained,
        "success": result.success,
        "terminal": result.terminal,
        "terminal_reason": result.terminal_reason,
        "events": result.events,
        "graph_card_ids": result.graph_card_ids,
        "next_state": result.next_state.to_public_dict(),
    }
