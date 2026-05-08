from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.engine import CoachBenchEngine


PROFILE_PATH = Path("agent_garage/profiles.json")
SEED_FIXTURE = Path("tests/fixtures/garage_knob_seeds.json")

OFFENSE_KNOBS = {
    "risk_tolerance",
    "adaptation_speed",
    "screen_trigger_confidence",
    "explosive_shot_tolerance",
    "run_pass_tendency",
}
DEFENSE_KNOBS = {
    "risk_tolerance",
    "disguise_sensitivity",
    "pressure_frequency",
    "counter_repeat_tolerance",
}
PRESET_FIELDS = {"label", "strategic_intent", "parameters", "expected_behavior", "known_counter"}


def _seeds() -> list[int]:
    payload = json.loads(SEED_FIXTURE.read_text(encoding="utf-8"))
    return [int(seed) for seed in payload["seeds"]]


def _profiles() -> dict[str, Any]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _run_pack(
    *,
    offense_params: dict[str, Any] | None = None,
    defense_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        CoachBenchEngine(seed=seed).run_drive(
            AdaptiveOffense({"parameters": offense_params} if offense_params else None),
            AdaptiveDefense({"parameters": defense_params} if defense_params else None),
        )
        for seed in _seeds()
    ]


def _counter(replays: list[dict[str, Any]], side: str, field: str) -> Counter[str]:
    action_key = "offense_action" if side == "offense" else "defense_action"
    counts: Counter[str] = Counter()
    for replay in replays:
        for play in replay["plays"]:
            counts.update([play["public"][action_key][field]])
    return counts


def _events(replays: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for replay in replays:
        for play in replay["plays"]:
            counts.update(event["tag"] for event in play["public"]["events"])
    return counts


def _resource_burn(replays: list[dict[str, Any]], side: str) -> Counter[str]:
    key = "offense_cost" if side == "offense" else "defense_cost"
    burn: Counter[str] = Counter()
    for replay in replays:
        for play in replay["plays"]:
            burn.update(play["public"]["resource_budget_snapshot"][key])
    return burn


def _assert_resource_constraints_hold(replays: list[dict[str, Any]]) -> None:
    for replay in replays:
        for play in replay["plays"]:
            assert play["public"]["validation_result"]["ok"]
            assert not play["public"]["validation_result"]["offense"]["fallback_used"]
            assert not play["public"]["validation_result"]["defense"]["fallback_used"]
            snapshot = play["public"]["resource_budget_snapshot"]
            for key in ("offense_remaining", "defense_remaining"):
                assert all(value >= 0 for value in snapshot[key].values())


def _points(replays: list[dict[str, Any]]) -> list[int]:
    return [int(replay["score"]["points"]) for replay in replays]


SignatureAssertion = Callable[[list[dict[str, Any]]], None]


def _offense_risk(replays: list[dict[str, Any]]) -> Counter[str]:
    return _counter(replays, "offense", "risk_level")


def _defense_risk(replays: list[dict[str, Any]]) -> Counter[str]:
    return _counter(replays, "defense", "risk_level")


def _offense_calls(replays: list[dict[str, Any]]) -> Counter[str]:
    return _counter(replays, "offense", "concept_family")


def _defense_calls(replays: list[dict[str, Any]]) -> Counter[str]:
    return _counter(replays, "defense", "coverage_family")


SIGNATURES: dict[str, SignatureAssertion] = {
    "conservative offense risk on every call": lambda replays: (
        assert_counter_equals_total(_offense_risk(replays), "conservative", replays)
    ),
    "quick_game plus play_action_flood >= 20 calls across seed pack": lambda replays: (
        assert_min(_offense_calls(replays)["quick_game"] + _offense_calls(replays)["play_action_flood"], 20)
    ),
    "no vertical_shot calls across seed pack": lambda replays: assert_equal(_offense_calls(replays)["vertical_shot"], 0),
    "aggressive offense risk >= 80% of calls": lambda replays: assert_ratio(
        _offense_risk(replays)["aggressive"], _total_plays(replays), 0.8
    ),
    "touchdowns on every baseline seed": lambda replays: assert_equal(sum(points >= 7 for points in _points(replays)), len(replays)),
    "rpo_glance calls >= 8 across seed pack": lambda replays: assert_min(_offense_calls(replays)["rpo_glance"], 8),
    "screen calls >= 3 across seed pack": lambda replays: assert_min(_offense_calls(replays)["screen"], 3),
    "offense spacing burn >= 40 across seed pack": lambda replays: assert_min(_resource_burn(replays, "offense")["spacing"], 40),
    "inside_zone calls >= 7 across seed pack": lambda replays: assert_min(_offense_calls(replays)["inside_zone"], 7),
    "play_action_flood calls >= 7 across seed pack": lambda replays: assert_min(_offense_calls(replays)["play_action_flood"], 7),
    "conservative defense risk on every call": lambda replays: (
        assert_counter_equals_total(_defense_risk(replays), "conservative", replays)
    ),
    "redzone_bracket plus bear_front >= 30 calls across seed pack": lambda replays: (
        assert_min(_defense_calls(replays)["redzone_bracket"] + _defense_calls(replays)["bear_front"], 30)
    ),
    "underneath_space_taken events >= 15 across seed pack": lambda replays: assert_min(_events(replays)["underneath_space_taken"], 15),
    "zero_pressure plus simulated_pressure >= 15 calls across seed pack": lambda replays: (
        assert_min(_defense_calls(replays)["zero_pressure"] + _defense_calls(replays)["simulated_pressure"], 15)
    ),
    "aggressive defense risk >= 15 calls across seed pack": lambda replays: assert_min(_defense_risk(replays)["aggressive"], 15),
    "defense rush burn >= 45 across seed pack": lambda replays: assert_min(_resource_burn(replays, "defense")["rush"], 45),
    "simulated_pressure calls >= 13 across seed pack": lambda replays: assert_min(_defense_calls(replays)["simulated_pressure"], 13),
    "defense disguise burn >= 50 across seed pack": lambda replays: assert_min(_resource_burn(replays, "defense")["disguise"], 50),
    "zero_pressure calls == 0 across seed pack": lambda replays: assert_equal(_defense_calls(replays)["zero_pressure"], 0),
    "cover1_man calls >= 6 across seed pack": lambda replays: assert_min(_defense_calls(replays)["cover1_man"], 6),
    "aggressive defense risk >= 6 calls across seed pack": lambda replays: assert_min(_defense_risk(replays)["aggressive"], 6),
    "redzone_bracket plus bear_front >= 26 calls across seed pack": lambda replays: (
        assert_min(_defense_calls(replays)["redzone_bracket"] + _defense_calls(replays)["bear_front"], 26)
    ),
}


def assert_min(actual: int, expected: int) -> None:
    assert actual >= expected


def assert_equal(actual: int, expected: int) -> None:
    assert actual == expected


def assert_ratio(actual: int, total: int, minimum: float) -> None:
    assert total > 0
    assert actual / total >= minimum


def assert_counter_equals_total(counter: Counter[str], key: str, replays: list[dict[str, Any]]) -> None:
    assert counter[key] == _total_plays(replays)


def _total_plays(replays: list[dict[str, Any]]) -> int:
    return sum(len(replay["plays"]) for replay in replays)


def test_presets_use_only_live_knobs_and_required_metadata() -> None:
    profiles = _profiles()

    for key, profile in profiles["offense_archetypes"].items():
        assert PRESET_FIELDS <= set(profile), key
        assert set(profile["parameters"]) == OFFENSE_KNOBS
        assert profile["label"]
        assert profile["strategic_intent"]
        assert profile["expected_behavior"]
        assert profile["known_counter"]

    for key, profile in profiles["defense_archetypes"].items():
        assert PRESET_FIELDS <= set(profile), key
        assert set(profile["parameters"]) == DEFENSE_KNOBS
        assert profile["label"]
        assert profile["strategic_intent"]
        assert profile["expected_behavior"]
        assert profile["known_counter"]


def test_offense_preset_expected_signatures_hold_against_fixed_baseline() -> None:
    for key, profile in _profiles()["offense_archetypes"].items():
        replays = _run_pack(offense_params=profile["parameters"])
        _assert_resource_constraints_hold(replays)
        for signature in profile["expected_behavior"]:
            assert signature in SIGNATURES, f"{key} has untested signature: {signature}"
            SIGNATURES[signature](replays)


def test_defense_preset_expected_signatures_hold_against_fixed_baseline() -> None:
    for key, profile in _profiles()["defense_archetypes"].items():
        replays = _run_pack(defense_params=profile["parameters"])
        _assert_resource_constraints_hold(replays)
        for signature in profile["expected_behavior"]:
            assert signature in SIGNATURES, f"{key} has untested signature: {signature}"
            SIGNATURES[signature](replays)


def test_known_counters_win_majority_of_seed_pack() -> None:
    profiles = _profiles()

    for key, profile in profiles["offense_archetypes"].items():
        bucket, counter_key = profile["known_counter"].split(".", 1)
        assert bucket == "defense_archetypes", key
        defense = profiles[bucket][counter_key]["parameters"]
        replays = _run_pack(offense_params=profile["parameters"], defense_params=defense)
        _assert_resource_constraints_hold(replays)
        assert sum(points < 7 for points in _points(replays)) >= 3

    for key, profile in profiles["defense_archetypes"].items():
        bucket, counter_key = profile["known_counter"].split(".", 1)
        assert bucket == "offense_archetypes", key
        offense = profiles[bucket][counter_key]["parameters"]
        replays = _run_pack(offense_params=offense, defense_params=profile["parameters"])
        _assert_resource_constraints_hold(replays)
        assert sum(points >= 7 for points in _points(replays)) >= 3
