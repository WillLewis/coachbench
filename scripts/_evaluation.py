from __future__ import annotations

import json
from pathlib import Path
from importlib import import_module
from typing import Any

try:
    import _path  # noqa: F401
except ModuleNotFoundError:
    from scripts import _path  # noqa: F401

from coachbench.contracts import validate_replay_contract
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS, validate_action_schema
from coachbench.engine import CoachBenchEngine
from coachbench.roster_budget import RosterBudget, load_roster
from coachbench.matchup_traits import MatchupTraits
from coachbench.scouting import ScoutingReport
from coachbench.schema import DefenseAction, OffenseAction
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
    offense_roster: RosterBudget | None = None,
    defense_roster: RosterBudget | None = None,
    matchup_traits: MatchupTraits | None = None,
    offense_scouting: ScoutingReport | None = None,
    defense_scouting: ScoutingReport | None = None,
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
    if offense_team.roster_path and offense_roster is None:
        offense_roster = load_roster(offense_team.roster_path)
    if defense_team.roster_path and defense_roster is None:
        defense_roster = load_roster(defense_team.roster_path)
    replay = CoachBenchEngine(seed=seed).run_drive(
        offense_agent,
        defense_agent,
        agent_garage_config=garage_config,
        max_plays=max_plays,
        offense_roster=offense_roster,
        defense_roster=defense_roster,
        matchup_traits=matchup_traits,
        offense_scouting=offense_scouting,
        defense_scouting=defense_scouting,
    )
    validate_replay_contract(replay)
    return replay


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def load_agent(dotted_path: str) -> Any:
    if "." not in dotted_path:
        raise ValueError(f"Agent path must include module and class: {dotted_path}")
    module_name, class_name = dotted_path.rsplit(".", 1)
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


class ValidationFailure(ValueError):
    def __init__(self, check: str, detail: str) -> None:
        self.check = check
        self.detail = detail
        super().__init__(f"{check}: {detail}")


class InspectingAgent:
    def __init__(self, agent: Any, side: str) -> None:
        self.agent = agent
        self.side = side
        self.name = getattr(agent, "name", agent.__class__.__name__)
        self.failures: list[dict[str, str]] = []
        self.actions: list[dict[str, Any]] = []

    def choose_action(self, observation: dict[str, Any], memory: Any, legal: Any) -> OffenseAction | DefenseAction:
        self._check_observation(observation)
        action = self.agent.choose_action(observation, memory, legal)
        self._check_observation(observation)
        self._check_action(action, observation)
        return action

    def _fail(self, check: str, detail: str) -> None:
        self.failures.append({"check": check, "detail": detail})

    def _check_observation(self, observation: dict[str, Any]) -> None:
        hidden = sorted(HIDDEN_OBSERVATION_FIELDS & set(observation))
        if hidden:
            self._fail("V3", f"observation includes hidden fields: {hidden}")
        if self.side == "offense" and "defense_action" in observation:
            self._fail("V3", "offense observation includes pre-commit defense action")
        if self.side == "defense" and "offense_action" in observation:
            self._fail("V3", "defense observation includes pre-commit offense action")

    def _check_action(self, action: OffenseAction | DefenseAction, observation: dict[str, Any]) -> None:
        action_dict = action.to_dict()
        try:
            validate_action_schema(action_dict, self.side)
        except Exception as exc:
            self._fail("V1", str(exc))
            return
        if not str(action_dict.get("constraint_tag", "")).startswith("legal:"):
            self._fail("V1", "constraint_tag does not start with legal:")
        if self.side == "offense" and action.concept_family not in observation.get("legal_concepts", []):
            self._fail("V1", f"illegal offense concept returned: {action.concept_family}")
        if self.side == "defense" and action.coverage_family not in observation.get("legal_calls", []):
            self._fail("V1", f"illegal defense call returned: {action.coverage_family}")
        self.actions.append(action_dict)


def static_counterpart(side: str) -> Any:
    from agents.static_defense import StaticDefense
    from agents.static_offense import StaticOffense

    return StaticDefense() if side == "offense" else StaticOffense()


def run_validated_drive(
    *,
    agent: Any,
    side: str,
    opponent: Any,
    seed: int,
    max_plays: int,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    inspected = InspectingAgent(agent, side)
    if side == "offense":
        replay = CoachBenchEngine(seed=seed).run_drive(inspected, opponent, max_plays=max_plays)
    else:
        replay = CoachBenchEngine(seed=seed).run_drive(opponent, inspected, max_plays=max_plays)
    failures = list(inspected.failures)
    for play in replay["plays"]:
        side_result = play["public"]["validation_result"][side]
        if side_result["fallback_used"]:
            failures.append({"check": "V2", "detail": f"fallback used on play {play['public']['play_index']}"})
    return replay, failures
