from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense


@dataclass(frozen=True)
class TeamConfig:
    team_id: str
    label: str
    offense_agent: str
    defense_agent: str
    offense_profile_key: str | None
    defense_profile_key: str | None
    notes: str


REQUIRED_TEAM_FIELDS = {
    "team_id",
    "label",
    "offense_agent",
    "defense_agent",
    "offense_profile_key",
    "defense_profile_key",
    "notes",
}


def load_team(path: Path) -> TeamConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_TEAM_FIELDS - set(payload)
    if missing:
        raise ValueError(f"Team config missing fields: {sorted(missing)}")
    return TeamConfig(**{field: payload[field] for field in REQUIRED_TEAM_FIELDS})


def _load_profiles() -> dict[str, Any]:
    path = Path("agent_garage/profiles.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _profile(profiles: dict[str, Any], group: str, key: str | None) -> dict[str, Any] | None:
    if key is None:
        return None
    if key not in profiles[group]:
        raise ValueError(f"Unknown profile key: {key}")
    profile = dict(profiles[group][key])
    profile["profile_key"] = key
    return profile


def build_team_agents(team: TeamConfig) -> tuple[StaticOffense | AdaptiveOffense, StaticDefense | AdaptiveDefense, dict[str, Any]]:
    profiles = _load_profiles()
    offense_profile = _profile(profiles, "offense_archetypes", team.offense_profile_key)
    defense_profile = _profile(profiles, "defense_archetypes", team.defense_profile_key)

    if team.offense_agent == "static":
        offense_agent = StaticOffense()
        offense_config = {"profile_key": "static_baseline", "label": "Static Baseline"}
    elif team.offense_agent == "adaptive":
        offense_agent = AdaptiveOffense(offense_profile)
        offense_config = offense_profile or {}
    else:
        raise ValueError(f"Unknown offense agent kind: {team.offense_agent}")

    if team.defense_agent == "static":
        defense_agent = StaticDefense()
        defense_config = {"profile_key": "static_baseline", "label": "Static Baseline"}
    elif team.defense_agent == "adaptive":
        defense_agent = AdaptiveDefense(defense_profile)
        defense_config = defense_profile or {}
    else:
        raise ValueError(f"Unknown defense agent kind: {team.defense_agent}")

    return offense_agent, defense_agent, {
        "team_id": team.team_id,
        "team_label": team.label,
        "offense_profile": offense_config,
        "defense_profile": defense_config,
    }
