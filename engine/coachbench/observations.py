from __future__ import annotations

from typing import Any, Dict, List

from .schema import GameState, PlayResolution


def offense_observation_before_play(
    state: GameState,
    legal_concepts: List[str],
    resource_remaining: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "side": "offense",
        "game_state": state.to_public_dict(),
        "legal_concepts": list(legal_concepts),
        "own_resource_remaining": dict(resource_remaining),
    }


def defense_observation_before_play(
    state: GameState,
    legal_calls: List[str],
    resource_remaining: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "side": "defense",
        "game_state": state.to_public_dict(),
        "legal_calls": list(legal_calls),
        "own_resource_remaining": dict(resource_remaining),
    }


def events_visible_to(result: PlayResolution, side: str) -> List[Dict[str, Any]]:
    return [
        event
        for event in result.events
        if side in event.get("visible_to", ["offense", "defense"])
    ]


def _graph_card_ids_for_events(events: List[Dict[str, Any]]) -> List[str]:
    return list(dict.fromkeys(event["graph_card_id"] for event in events))


def post_play_public_observation(result: PlayResolution) -> Dict[str, Any]:
    events = events_visible_to(result, "offense")
    events = [event for event in events if "defense" in event.get("visible_to", [])]
    return {
        "play_index": result.play_index,
        "offense_action": result.offense_action.to_dict(),
        "defense_action": result.defense_action.to_dict(),
        "yards_gained": result.yards_gained,
        "expected_value_delta": round(result.expected_value_delta, 3),
        "success": result.success,
        "terminal": result.terminal,
        "terminal_reason": result.terminal_reason,
        "events": events,
        "graph_card_ids": _graph_card_ids_for_events(events),
        "next_state": result.next_state.to_public_dict(),
    }


def post_play_offense_observation(result: PlayResolution) -> Dict[str, Any]:
    events = events_visible_to(result, "offense")
    return {
        "play_index": result.play_index,
        "yards_gained": result.yards_gained,
        "success": result.success,
        "terminal": result.terminal,
        "terminal_reason": result.terminal_reason,
        "events": events,
        "graph_card_ids": _graph_card_ids_for_events(events),
        "next_state": result.next_state.to_public_dict(),
        "belief_after": result.offense_belief_after,
    }


def post_play_defense_observation(result: PlayResolution) -> Dict[str, Any]:
    events = events_visible_to(result, "defense")
    return {
        "play_index": result.play_index,
        "yards_gained": result.yards_gained,
        "success": result.success,
        "terminal": result.terminal,
        "terminal_reason": result.terminal_reason,
        "events": events,
        "graph_card_ids": _graph_card_ids_for_events(events),
        "next_state": result.next_state.to_public_dict(),
        "belief_after": result.defense_belief_after,
    }
