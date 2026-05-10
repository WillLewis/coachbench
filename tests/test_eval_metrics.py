from __future__ import annotations

from coachbench.eval_metrics import (
    bootstrap_ci_95,
    canonical_report_hash,
    concept_entropy,
    concept_frequency,
    degenerate_strategy_flags,
    fallback_rate,
    paired_seed_lift,
    points_per_drive,
    touchdown_rate,
)


def _play(
    *,
    concept: str = "quick_game",
    coverage: str = "cover3_match",
    offense_fallback: bool = False,
    defense_fallback: bool = False,
) -> dict:
    return {
        "public": {
            "offense_action": {"concept_family": concept, "concept_id": "wrong"},
            "defense_action": {"coverage_family": coverage, "call_id": "wrong"},
        },
        "engine_internal": {
            "validation_result": {
                "offense": {"fallback_used": offense_fallback},
                "defense": {"fallback_used": defense_fallback},
            },
            "resource_budget_snapshot": {
                "offense_remaining": {"spacing": 1},
                "defense_remaining": {"coverage": 1},
            },
        },
    }


def _replay(points: int = 0, result: str = "stopped", plays: list[dict] | None = None) -> dict:
    return {
        "plays": plays if plays is not None else [_play()],
        "score": {"points": points, "result": result},
    }


def test_fallback_rate_zero_when_no_fallbacks() -> None:
    assert fallback_rate([_replay(plays=[_play(), _play()])], "offense") == 0.0


def test_fallback_rate_aggregates_across_plays_and_replays() -> None:
    replays = [
        _replay(plays=[_play(offense_fallback=True), _play()]),
        _replay(plays=[_play(), _play(offense_fallback=True)]),
        _replay(plays=[_play(), _play()]),
    ]
    assert fallback_rate(replays, "offense") == 2 / 6


def test_fallback_rate_per_side() -> None:
    replays = [_replay(plays=[_play(offense_fallback=True), _play(defense_fallback=True)])]
    assert fallback_rate(replays, "offense") == 1 / 2
    assert fallback_rate(replays, "defense") == 1 / 2


def test_points_per_drive() -> None:
    assert points_per_drive([_replay(points=7), _replay(points=0), _replay(points=3)]) == 3.3333


def test_touchdown_rate() -> None:
    assert touchdown_rate([
        _replay(result="touchdown"),
        _replay(result="stopped"),
        _replay(result="touchdown"),
    ]) == 2 / 3


def test_concept_frequency_sums_to_one() -> None:
    frequency = concept_frequency([
        _replay(plays=[_play(concept="quick_game"), _play(concept="inside_zone")]),
        _replay(plays=[_play(concept="quick_game")]),
    ], "offense")
    assert sum(frequency.values()) == 1.0
    assert frequency["quick_game"] == 2 / 3


def test_concept_frequency_uses_concept_family_field() -> None:
    frequency = concept_frequency([_replay(plays=[_play(concept="quick_game")])], "offense")
    assert frequency == {"quick_game": 1.0}
    assert "wrong" not in frequency


def test_concept_entropy_zero_for_single_call() -> None:
    assert concept_entropy({"quick_game": 1.0}) == 0.0


def test_concept_entropy_max_for_uniform() -> None:
    assert concept_entropy({"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}) == 2.0


def test_paired_seed_lift_win_rate() -> None:
    summary = paired_seed_lift([
        {"seed": 1, "candidate_points": 7, "baseline_points": 0},
        {"seed": 2, "candidate_points": 0, "baseline_points": 7},
        {"seed": 3, "candidate_points": 3, "baseline_points": 3},
    ])
    assert summary == {"mean": 0.0, "win_rate": 1 / 3, "n": 3, "wins": 1, "losses": 1, "ties": 1}


def test_bootstrap_ci_95_deterministic_with_seed() -> None:
    first = bootstrap_ci_95([1.0, 2.0, 3.0], iterations=100, seed=7)
    second = bootstrap_ci_95([1.0, 2.0, 3.0], iterations=100, seed=7)
    assert first == second
    assert first != (0.0, 0.0)


def test_canonical_report_hash_excludes_volatile_fields() -> None:
    first = {"report_hash": "a", "generated_at": "one", "metrics": {"value": 1}}
    second = {"report_hash": "b", "generated_at": "two", "metrics": {"value": 1}}
    assert canonical_report_hash(first) == canonical_report_hash(second)


def test_canonical_report_hash_changes_with_content() -> None:
    first = {"report_hash": "a", "generated_at": "one", "metrics": {"value": 1}}
    second = {"report_hash": "a", "generated_at": "one", "metrics": {"value": 2}}
    assert canonical_report_hash(first) != canonical_report_hash(second)


def test_degenerate_flag_at_threshold() -> None:
    replays = [_replay(plays=[
        *[_play(concept="quick_game", coverage="cover3_match") for _ in range(7)],
        *[_play(concept="inside_zone", coverage="trap_coverage") for _ in range(3)],
    ])]
    flags = degenerate_strategy_flags(replays, threshold=0.7)
    assert {"side": "offense", "concept": "quick_game", "frequency": 0.7} in flags
    assert {"side": "defense", "concept": "cover3_match", "frequency": 0.7} in flags
