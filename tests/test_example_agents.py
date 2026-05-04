from __future__ import annotations

from agents.example_agent import ExampleCustomDefense, ExampleCustomOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine


def test_example_custom_offense_runs_deterministically() -> None:
    first = CoachBenchEngine(seed=42).run_drive(ExampleCustomOffense(), StaticDefense())
    second = CoachBenchEngine(seed=42).run_drive(ExampleCustomOffense(), StaticDefense())

    validate_replay_contract(first)
    assert first == second
    assert first["score"]["invalid_action_count"] == 0


def test_example_custom_defense_runs_deterministically() -> None:
    first = CoachBenchEngine(seed=42).run_drive(StaticOffense(), ExampleCustomDefense())
    second = CoachBenchEngine(seed=42).run_drive(StaticOffense(), ExampleCustomDefense())

    validate_replay_contract(first)
    assert first == second
    assert first["score"]["invalid_action_count"] == 0
