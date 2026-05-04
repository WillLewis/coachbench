from __future__ import annotations

import json

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine
from coachbench.roster_budget import load_roster


def _stable_bytes(replay: dict) -> bytes:
    return json.dumps(replay, indent=2).encode("utf-8")


def test_no_roster_optional_args_are_byte_identical_to_legacy_call_path() -> None:
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    explicit_none = CoachBenchEngine(seed=42).run_drive(
        AdaptiveOffense(),
        AdaptiveDefense(),
        offense_roster=None,
        defense_roster=None,
    )

    assert _stable_bytes(baseline) == _stable_bytes(explicit_none)


def test_balanced_rosters_do_not_change_tactical_replay() -> None:
    balanced = load_roster("data/rosters/balanced_v0.json")
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    with_rosters = CoachBenchEngine(seed=42).run_drive(
        AdaptiveOffense(),
        AdaptiveDefense(),
        offense_roster=balanced,
        defense_roster=balanced,
    )

    validate_replay_contract(with_rosters)
    assert _stable_bytes(with_rosters) == _stable_bytes(baseline)


def test_pass_heavy_offense_roster_changes_bounded_expected_value() -> None:
    pass_heavy = load_roster("data/rosters/pass_heavy_v0.json")
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    with_roster = CoachBenchEngine(seed=42).run_drive(
        AdaptiveOffense(),
        AdaptiveDefense(),
        offense_roster=pass_heavy,
    )

    assert with_roster != baseline
    assert with_roster["agent_garage_config"]["rosters"]["offense"]["roster_id"] == "pass_heavy_v0"
    for base_play, roster_play in zip(baseline["plays"], with_roster["plays"]):
        diff = roster_play["public"]["expected_value_delta"] - base_play["public"]["expected_value_delta"]
        assert abs(diff) <= 0.10
