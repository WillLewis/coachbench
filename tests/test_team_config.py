from __future__ import annotations

from pathlib import Path

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.team_config import TeamConfig, build_team_agents, load_team


TEAM_A = Path("data/teams/team_a_static_baseline.json")
TEAM_B = Path("data/teams/team_b_adaptive_counter.json")


def test_team_json_files_load_and_build_expected_agents() -> None:
    team_a = load_team(TEAM_A)
    team_b = load_team(TEAM_B)

    offense_a, defense_a, config_a = build_team_agents(team_a)
    offense_b, defense_b, config_b = build_team_agents(team_b)

    assert isinstance(offense_a, StaticOffense)
    assert isinstance(defense_a, StaticDefense)
    assert isinstance(offense_b, AdaptiveOffense)
    assert isinstance(defense_b, AdaptiveDefense)
    assert config_a["team_id"] == "team_a_static_baseline"
    assert config_b["offense_profile"]["profile_key"] == "misdirection_artist"
    assert config_b["defense_profile"]["profile_key"] == "disguise_specialist"


def test_unknown_agent_kind_raises_clear_error() -> None:
    team = TeamConfig(
        team_id="test_team",
        label="Test Team",
        offense_agent="unknown",
        defense_agent="static",
        offense_profile_key=None,
        defense_profile_key=None,
        notes="invalid test",
    )

    try:
        build_team_agents(team)
    except ValueError as exc:
        assert "Unknown offense agent kind" in str(exc)
    else:
        raise AssertionError("Unknown offense agent kind was accepted")


def test_unknown_profile_key_raises_clear_error() -> None:
    team = TeamConfig(
        team_id="test_team",
        label="Test Team",
        offense_agent="adaptive",
        defense_agent="static",
        offense_profile_key="missing_profile",
        defense_profile_key=None,
        notes="invalid test",
    )

    try:
        build_team_agents(team)
    except ValueError as exc:
        assert "Unknown profile key" in str(exc)
    else:
        raise AssertionError("Unknown profile key was accepted")
