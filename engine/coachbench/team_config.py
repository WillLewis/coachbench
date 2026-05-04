from __future__ import annotations

import json
from importlib import import_module
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
    roster_path: str | None
    matchup_traits_path: str | None
    scouting_report_path: str | None
    notes: str


REQUIRED_TEAM_FIELDS = {
    "team_id",
    "label",
    "offense_agent",
    "defense_agent",
    "offense_profile_key",
    "defense_profile_key",
    "roster_path",
    "matchup_traits_path",
    "scouting_report_path",
    "notes",
}


def load_team(path: Path | str) -> TeamConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
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


def _import_agent(path: str, config: dict[str, Any] | None) -> Any:
    if "." not in path:
        raise ValueError(f"Import agent path must include module and class: {path}")
    module_name, class_name = path.rsplit(".", 1)
    try:
        module = import_module(module_name)
    except Exception as exc:
        raise ValueError(f"Could not import agent module {module_name}: {exc}") from exc
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(f"Agent class {path} was not found") from exc
    for attr in ("name", "choose_action"):
        if not hasattr(cls, attr):
            raise ValueError(f"Agent class {path} has no attribute '{attr}'")
    try:
        return cls(config or {})
    except TypeError:
        return cls()


def _build_agent(kind: str, side: str, profile: dict[str, Any] | None) -> Any:
    if kind == "static" and side == "offense":
        return StaticOffense()
    if kind == "static" and side == "defense":
        return StaticDefense()
    if kind == "adaptive" and side == "offense":
        return AdaptiveOffense(profile)
    if kind == "adaptive" and side == "defense":
        return AdaptiveDefense(profile)
    if kind.startswith("import:"):
        return _import_agent(kind.removeprefix("import:"), profile)
    raise ValueError(f"Unknown {side} agent kind: {kind}")


def build_team_agents(team: TeamConfig) -> tuple[StaticOffense | AdaptiveOffense, StaticDefense | AdaptiveDefense, dict[str, Any]]:
    profiles = _load_profiles()
    offense_profile = _profile(profiles, "offense_archetypes", team.offense_profile_key)
    defense_profile = _profile(profiles, "defense_archetypes", team.defense_profile_key)
    offense_agent = _build_agent(team.offense_agent, "offense", offense_profile)
    defense_agent = _build_agent(team.defense_agent, "defense", defense_profile)
    offense_config = offense_profile or {"profile_key": "static_baseline", "label": "Static Baseline"}
    defense_config = defense_profile or {"profile_key": "static_baseline", "label": "Static Baseline"}

    return offense_agent, defense_agent, {
        "team_id": team.team_id,
        "team_label": team.label,
        "offense_profile": offense_config,
        "defense_profile": defense_config,
    }
