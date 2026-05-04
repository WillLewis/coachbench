from __future__ import annotations

import json
from pathlib import Path

import pytest

from coachbench.contracts import ContractValidationError, validate_matchup_traits
from coachbench.matchup_traits import (
    ALLOWED_TRAITS,
    defense_trait_modifier,
    load_matchup_traits,
    offense_trait_modifier,
)


PATHS = [
    Path("data/matchup_traits/neutral_v0.json"),
    Path("data/matchup_traits/pass_heavy_offense_v0.json"),
    Path("data/matchup_traits/trap_defense_v0.json"),
]


def _payload(path: Path = PATHS[0]) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_matchup_trait_files_load_and_validate() -> None:
    for path in PATHS:
        payload = _payload(path)
        validate_matchup_traits(payload)
        traits = load_matchup_traits(path)
        assert set(traits.values) == set(ALLOWED_TRAITS)


def test_neutral_traits_are_zero_delta_for_known_calls() -> None:
    traits = load_matchup_traits(PATHS[0])
    for concept in ("vertical_shot", "screen", "inside_zone", "quick_game"):
        assert offense_trait_modifier(traits, concept) == (0.0, 0.0, 0)
    for coverage in ("simulated_pressure", "trap_coverage", "redzone_bracket", "base_cover3"):
        assert defense_trait_modifier(traits, coverage) == (0.0, 0.0, 0)


def test_hostile_values_stay_clamped() -> None:
    payload = _payload()
    payload["values"] = {key: 1.0 for key in ALLOWED_TRAITS}
    path = Path("/tmp/hostile_traits.json")
    path.write_text(json.dumps(payload), encoding="utf-8")
    traits = load_matchup_traits(path)
    for concept in ("vertical_shot", "screen", "inside_zone"):
        epa, success, noise = offense_trait_modifier(traits, concept)
        assert -0.15 <= epa <= 0.15
        assert -0.10 <= success <= 0.10
        assert -2 <= noise <= 2


def test_matchup_traits_reject_invalid_values() -> None:
    payload = _payload()
    payload["values"]["matchup_volatility"] = 1.2
    with pytest.raises(ContractValidationError, match=r"\[0, 1\]"):
        validate_matchup_traits(payload)


def test_matchup_traits_reject_unknown_trait() -> None:
    payload = _payload()
    payload["values"]["unknown_trait"] = 0.5
    with pytest.raises(ContractValidationError, match="invalid"):
        validate_matchup_traits(payload)


def test_matchup_traits_reject_missing_trait() -> None:
    payload = _payload()
    del payload["values"]["matchup_volatility"]
    with pytest.raises(ContractValidationError, match="invalid"):
        validate_matchup_traits(payload)
