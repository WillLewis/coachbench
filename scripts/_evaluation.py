from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine
from coachbench.team_config import TeamConfig, build_team_agents, load_team


def parse_seeds(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_teams(team_a_path: Path, team_b_path: Path) -> tuple[TeamConfig, TeamConfig]:
    return load_team(team_a_path), load_team(team_b_path)


def run_direction(
    *,
    offense_team: TeamConfig,
    defense_team: TeamConfig,
    seed: int,
    max_plays: int,
    matchup_direction: str,
) -> dict[str, Any]:
    offense_agent, _, offense_config = build_team_agents(offense_team)
    _, defense_agent, defense_config = build_team_agents(defense_team)
    garage_config = {
        "source": "team_config_v0",
        "offense_team_id": offense_team.team_id,
        "defense_team_id": defense_team.team_id,
        "matchup_direction": matchup_direction,
        "offense_profile": offense_config["offense_profile"],
        "defense_profile": defense_config["defense_profile"],
    }
    replay = CoachBenchEngine(seed=seed).run_drive(
        offense_agent,
        defense_agent,
        agent_garage_config=garage_config,
        max_plays=max_plays,
    )
    validate_replay_contract(replay)
    return replay


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0
