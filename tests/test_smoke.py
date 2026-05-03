from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.action_legality import ActionValidationError, LegalActionEnumerator
from coachbench.engine import CoachBenchEngine
from coachbench.graph_loader import StrategyGraph
from coachbench.schema import OffenseAction


def test_showcase_replay_is_deterministic() -> None:
    first = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    second = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    assert first == second
    assert first["plays"]
    assert "film_room" in first


def test_legal_action_enumerator_rejects_invalid_action() -> None:
    legal = LegalActionEnumerator(StrategyGraph())
    bad = OffenseAction(
        personnel_family="fictional_11",
        formation_family="compact",
        motion_family="none",
        concept_family="impossible_magic_play",
        protection_family="standard",
        risk_level="balanced",
        constraint_tag="bad",
    )
    try:
        legal.validate_offense_action(bad)
    except ActionValidationError:
        return
    raise AssertionError("Invalid action was not rejected")


def test_replay_has_no_hidden_seed_value() -> None:
    replay = CoachBenchEngine(seed=123).run_drive(AdaptiveOffense(), AdaptiveDefense())
    assert replay["metadata"]["seed_hash"]
    assert "seed" not in replay["metadata"]
