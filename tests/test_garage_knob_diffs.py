from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.engine import CoachBenchEngine


SEED_FIXTURE = Path("tests/fixtures/garage_knob_seeds.json")


def _seeds() -> list[int]:
    payload = json.loads(SEED_FIXTURE.read_text(encoding="utf-8"))
    seeds = [int(seed) for seed in payload["seeds"]]
    assert len(seeds) == 5
    assert len(set(seeds)) == 5
    return seeds


def _run_pack(
    *,
    offense_config: dict[str, Any] | None = None,
    defense_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        CoachBenchEngine(seed=seed).run_drive(
            AdaptiveOffense(offense_config),
            AdaptiveDefense(defense_config),
        )
        for seed in _seeds()
    ]


def _concept_counts(replays: list[dict[str, Any]], side: str) -> Counter[str]:
    key = "offense_action" if side == "offense" else "defense_action"
    field = "concept_family" if side == "offense" else "coverage_family"
    counts: Counter[str] = Counter()
    for replay in replays:
        counts.update(play["public"][key][field] for play in replay["plays"])
    return counts


def _public_event_counts(replays: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for replay in replays:
        for play in replay["plays"]:
            counts.update(event["tag"] for event in play["public"]["events"])
    return counts


def _resource_burn(replays: list[dict[str, Any]], side: str) -> Counter[str]:
    cost_key = "offense_cost" if side == "offense" else "defense_cost"
    burn: Counter[str] = Counter()
    for replay in replays:
        for play in replay["plays"]:
            burn.update(play["public"]["resource_budget_snapshot"][cost_key])
    return burn


def _drive_outcomes(replays: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    return Counter(
        (replay["score"]["result"], replay["metadata"]["drive_terminal_condition"])
        for replay in replays
    )


def _total_points(replays: list[dict[str, Any]]) -> int:
    return sum(int(replay["score"]["points"]) for replay in replays)


def test_seed_pack_is_deterministic_and_varied() -> None:
    first = _run_pack()
    second = _run_pack()

    assert first == second
    outcomes = _drive_outcomes(first)
    assert outcomes[("touchdown", "touchdown")] >= 1
    assert outcomes[("field_goal", "max_plays_reached")] >= 1
    assert outcomes[("stopped", "turnover_on_downs")] >= 1

    low_adaptation = _run_pack(offense_config={"adaptation_speed": 0.1})
    assert any(replay["metadata"]["drive_terminal_condition"] == "turnover" for replay in low_adaptation)


def test_risk_tolerance_moves_drive_outcome() -> None:
    low = _run_pack(offense_config={"risk_tolerance": "low"})
    high = _run_pack(offense_config={"risk_tolerance": "high"})

    assert _drive_outcomes(low) != _drive_outcomes(high)
    assert _total_points(high) - _total_points(low) >= 21


def test_adaptation_speed_moves_play_distribution() -> None:
    low = _run_pack(offense_config={"adaptation_speed": 0.1})
    high = _run_pack(offense_config={"adaptation_speed": 0.9})

    low_calls = _concept_counts(low, "offense")
    high_calls = _concept_counts(high, "offense")
    assert high_calls["play_action_flood"] - low_calls["play_action_flood"] >= 6
    assert high_calls["quick_game"] - low_calls["quick_game"] >= 10


def test_screen_trigger_confidence_moves_graph_event_frequency() -> None:
    defense = {"pressure_frequency": 0.9, "disguise_sensitivity": 0.9, "risk_tolerance": "high"}
    low = _run_pack(offense_config={"screen_trigger_confidence": 0.1}, defense_config=defense)
    high = _run_pack(offense_config={"screen_trigger_confidence": 0.9}, defense_config=defense)

    low_events = _public_event_counts(low)
    high_events = _public_event_counts(high)
    low_pressure_screen_events = low_events["screen_baited"] + low_events["pressure_punished"]
    high_pressure_screen_events = high_events["screen_baited"] + high_events["pressure_punished"]
    assert low_pressure_screen_events - high_pressure_screen_events >= 5


def test_explosive_shot_tolerance_moves_play_distribution() -> None:
    low = _run_pack(offense_config={"run_pass_tendency": "pass_heavy", "explosive_shot_tolerance": 0.1})
    high = _run_pack(offense_config={"run_pass_tendency": "pass_heavy", "explosive_shot_tolerance": 0.9})

    low_calls = _concept_counts(low, "offense")
    high_calls = _concept_counts(high, "offense")
    assert high_calls["vertical_shot"] - low_calls["vertical_shot"] >= 5


def test_run_pass_tendency_moves_play_distribution() -> None:
    run_first = _run_pack(offense_config={"run_pass_tendency": "run_to_play_action"})
    pass_first = _run_pack(offense_config={"run_pass_tendency": "pass_heavy"})

    run_calls = _concept_counts(run_first, "offense")
    pass_calls = _concept_counts(pass_first, "offense")
    assert run_calls["inside_zone"] - pass_calls["inside_zone"] >= 6
    assert pass_calls["rpo_glance"] - run_calls["rpo_glance"] >= 8


def test_disguise_sensitivity_moves_play_distribution() -> None:
    offense = {"run_pass_tendency": "pass_heavy"}
    low = _run_pack(offense_config=offense, defense_config={"disguise_sensitivity": 0.1})
    high = _run_pack(offense_config=offense, defense_config={"disguise_sensitivity": 0.9})

    low_calls = _concept_counts(low, "defense")
    high_calls = _concept_counts(high, "defense")
    assert high_calls["simulated_pressure"] - low_calls["simulated_pressure"] >= 7
    assert low_calls["redzone_bracket"] - high_calls["redzone_bracket"] >= 6


def test_pressure_frequency_moves_resource_burn() -> None:
    low = _run_pack(defense_config={"pressure_frequency": 0.1})
    high = _run_pack(defense_config={"pressure_frequency": 0.9})

    low_burn = _resource_burn(low, "defense")
    high_burn = _resource_burn(high, "defense")
    assert high_burn["disguise"] - low_burn["disguise"] >= 10


def test_counter_repeat_tolerance_moves_play_distribution() -> None:
    offense = {"run_pass_tendency": "pass_heavy"}
    low = _run_pack(
        offense_config=offense,
        defense_config={"counter_repeat_tolerance": 0.1, "pressure_frequency": 0.1, "disguise_sensitivity": 0.1},
    )
    high = _run_pack(
        offense_config=offense,
        defense_config={"counter_repeat_tolerance": 0.9, "pressure_frequency": 0.1, "disguise_sensitivity": 0.1},
    )

    low_calls = _concept_counts(low, "defense")
    high_calls = _concept_counts(high, "defense")
    assert low_calls["redzone_bracket"] - high_calls["redzone_bracket"] >= 6
    assert _public_event_counts(high)["coverage_switch_stress"] - _public_event_counts(low)["coverage_switch_stress"] >= 5
