from __future__ import annotations

import json

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS, validate_replay_contract
from coachbench.engine import CoachBenchEngine
from coachbench.matchup_traits import load_matchup_traits


class InspectingOffense(AdaptiveOffense):
    def __init__(self) -> None:
        super().__init__()
        self.observations = []

    def choose_action(self, observation, memory, legal):
        self.observations.append(dict(observation))
        return super().choose_action(observation, memory, legal)


class InspectingDefense(AdaptiveDefense):
    def __init__(self) -> None:
        super().__init__()
        self.observations = []

    def choose_action(self, observation, memory, legal):
        self.observations.append(dict(observation))
        return super().choose_action(observation, memory, legal)


def _bytes(replay: dict) -> bytes:
    return json.dumps(replay, indent=2).encode("utf-8")


def test_no_traits_optional_arg_is_byte_identical_to_legacy_path() -> None:
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    explicit_none = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), matchup_traits=None)
    assert _bytes(baseline) == _bytes(explicit_none)


def test_neutral_traits_are_byte_identical_to_no_traits() -> None:
    neutral = load_matchup_traits("data/matchup_traits/neutral_v0.json")
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    with_neutral = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), matchup_traits=neutral)
    assert _bytes(baseline) == _bytes(with_neutral)


def test_pass_heavy_traits_change_replay_with_bounded_expected_value() -> None:
    traits = load_matchup_traits("data/matchup_traits/pass_heavy_offense_v0.json")
    baseline = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    with_traits = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), matchup_traits=traits)
    validate_replay_contract(with_traits)
    assert with_traits != baseline
    for base_play, trait_play in zip(baseline["plays"], with_traits["plays"]):
        diff = trait_play["public"]["expected_value_delta"] - base_play["public"]["expected_value_delta"]
        assert abs(diff) <= 0.15


def test_agent_observations_do_not_include_hidden_trait_fields() -> None:
    offense = InspectingOffense()
    defense = InspectingDefense()
    traits = load_matchup_traits("data/matchup_traits/pass_heavy_offense_v0.json")
    CoachBenchEngine(seed=42).run_drive(offense, defense, matchup_traits=traits, max_plays=2)
    forbidden = HIDDEN_OBSERVATION_FIELDS | {"matchup_id"}
    for observation in offense.observations + defense.observations:
        assert not (forbidden & set(observation))
