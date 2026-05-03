from __future__ import annotations

from typing import Any, Dict, Iterable

from .schema import AgentMemory


def update_beliefs(
    offense_memory: AgentMemory,
    defense_memory: AgentMemory,
    offense_event_tags: Iterable[str],
    defense_event_tags: Iterable[str],
    belief_model: Dict[str, Any],
) -> None:
    deltas = belief_model["belief_deltas"]
    for tag in offense_event_tags:
        for key, delta in deltas.get(tag, {}).get("offense", {}).items():
            setattr(offense_memory.beliefs, key, getattr(offense_memory.beliefs, key) + float(delta))

    for tag in defense_event_tags:
        for key, delta in deltas.get(tag, {}).get("defense", {}).items():
            setattr(defense_memory.beliefs, key, getattr(defense_memory.beliefs, key) + float(delta))

    offense_memory.beliefs.clamp()
    defense_memory.beliefs.clamp()
