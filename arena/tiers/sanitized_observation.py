from __future__ import annotations

from typing import Any

from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS

from .base import SanitizedObservation

FORBIDDEN_TIER_OBSERVATION_KEYS = HIDDEN_OBSERVATION_FIELDS | {
    "seed",
    "seed_hash",
    "legal_action_set_id",
    "resource_budget_snapshot",
    "debug",
    "admin_metadata",
}


def _memory_summary(memory: Any) -> dict:
    beliefs = getattr(memory, "beliefs", None)
    return {
        "own_recent_calls": list(getattr(memory, "own_recent_calls", [])),
        "opponent_visible_tendencies": dict(getattr(memory, "opponent_visible_tendencies", {})),
        "beliefs": beliefs.to_dict() if hasattr(beliefs, "to_dict") else dict(beliefs or {}),
    }


def _remaining_totals(resources: dict[str, Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in resources.items()}


def build_tier_observation(
    side: str,
    engine_state: dict[str, Any],
    memory: Any,
    legal_actions: list[str],
    own_resource_remaining: dict[str, Any],
) -> SanitizedObservation:
    game_state = dict(engine_state.get("game_state", engine_state))
    allowed_state = {
        "down": game_state.get("down"),
        "distance": game_state.get("distance"),
        "yardline": game_state.get("yardline"),
        "play_index": game_state.get("play_index"),
        "points": game_state.get("points"),
        "max_plays": game_state.get("max_plays"),
    }
    payload = SanitizedObservation(
        side=side,
        game_state=allowed_state,
        legal_actions=list(legal_actions),
        own_resource_remaining=_remaining_totals(own_resource_remaining),
        memory_summary=_memory_summary(memory),
    )
    as_dict = {
        "side": payload.side,
        "game_state": payload.game_state,
        "legal_actions": payload.legal_actions,
        "own_resource_remaining": payload.own_resource_remaining,
        "memory_summary": payload.memory_summary,
    }
    leaked = FORBIDDEN_TIER_OBSERVATION_KEYS & set(as_dict)
    if leaked:
        raise AssertionError(f"tier observation leaked forbidden fields: {sorted(leaked)}")
    encoded = repr(as_dict)
    for forbidden in FORBIDDEN_TIER_OBSERVATION_KEYS:
        if forbidden in encoded:
            raise AssertionError(f"tier observation leaked forbidden value: {forbidden}")
    return payload
