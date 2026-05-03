from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .film_room import build_film_room


def seed_hash(seed: int) -> str:
    return hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12]


def build_replay(
    *,
    seed: int,
    graph_version: str,
    engine_version: str,
    offense_agent: str,
    defense_agent: str,
    agent_garage_config: Dict[str, Any],
    play_results: List[Dict[str, Any]],
    final_points: int,
    legal_sets: Dict[str, List[str]],
) -> Dict[str, Any]:
    film_room = build_film_room(play_results, final_points)
    return {
        "metadata": {
            "episode_id": f"showcase-{seed_hash(seed)}",
            "seed_hash": seed_hash(seed),
            "graph_version": graph_version,
            "engine_version": engine_version,
            "mode": "red_zone_showcase",
            "product_boundary": "fictional_teams_symbolic_concepts",
        },
        "agents": {
            "offense": offense_agent,
            "defense": defense_agent,
        },
        "agent_garage_config": agent_garage_config,
        "legal_sets": legal_sets,
        "plays": play_results,
        "score": {
            "points": final_points,
            "result": "touchdown" if final_points >= 7 else "field_goal" if final_points == 3 else "stopped",
        },
        "film_room": film_room,
    }
