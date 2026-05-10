from __future__ import annotations

import json
from typing import Any


def render_observation_for_offense(observation: dict[str, Any]) -> str:
    """Render the offense-side observation as a compact JSON string for prompting.

    Includes ONLY fields that deterministic agents also see:
      - game_state
      - legal_concepts
      - own_resource_remaining
      - events (if present in observation; otherwise omitted)

    Explicitly excludes graph_card_ids, interaction details, hidden traits, debug traces.
    """
    payload = _payload(observation, "legal_concepts")
    return "Pick exactly one legal concept_family (offense)\n" + json.dumps(payload, sort_keys=True, indent=2)


def render_observation_for_defense(observation: dict[str, Any]) -> str:
    """Same shape, with legal_calls instead of legal_concepts."""
    payload = _payload(observation, "legal_calls")
    return "Pick exactly one legal coverage_family (defense)\n" + json.dumps(payload, sort_keys=True, indent=2)


def _payload(observation: dict[str, Any], legal_key: str) -> dict[str, Any]:
    keys = ("side", "game_state", legal_key, "own_resource_remaining")
    payload = {key: observation[key] for key in keys if key in observation}
    if "events" in observation:
        payload["events"] = observation["events"]
    return payload
