from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .film_room import build_film_room
from .graph_loader import StrategyGraph


def seed_hash(seed: int) -> str:
    return hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12]


def build_replay(
    *,
    seed: int,
    start_yardline: int,
    max_plays: int,
    initial_down: int,
    initial_distance: int,
    drive_terminal_condition: str,
    graph_version: str,
    engine_version: str,
    offense_agent: str,
    defense_agent: str,
    agent_garage_config: Dict[str, Any],
    play_results: List[Dict[str, Any]],
    final_points: int,
    invalid_action_count: int,
    touchdown_points: int,
    field_goal_points: int,
    legal_sets: Dict[str, List[str]],
    graph: StrategyGraph | None = None,
) -> Dict[str, Any]:
    film_room = build_film_room(play_results, final_points, graph)
    return {
        "metadata": {
            "episode_id": f"showcase-{seed_hash(seed)}",
            "seed_hash": seed_hash(seed),
            "graph_version": graph_version,
            "engine_version": engine_version,
            "mode": "red_zone_showcase",
            "product_boundary": "fictional_teams_symbolic_concepts",
            "start_yardline": start_yardline,
            "max_plays": max_plays,
            "initial_down": initial_down,
            "initial_distance": initial_distance,
            "score_mode": "red_zone_points",
            "drive_terminal_condition": drive_terminal_condition,
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
            "result": "touchdown" if final_points >= touchdown_points else "field_goal" if final_points == field_goal_points else "stopped",
            "invalid_action_count": invalid_action_count,
        },
        "film_room": film_room,
        "debug": {
            "fields": [],
        },
    }
