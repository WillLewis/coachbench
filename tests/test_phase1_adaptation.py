from __future__ import annotations

from collections import Counter

from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.engine import CoachBenchEngine


def _offense_concept_multiset(offense_cls, seeds: list[int]) -> Counter[str]:
    calls: Counter[str] = Counter()
    for seed in seeds:
        replay = CoachBenchEngine(seed=seed).run_drive(offense_cls(), StaticDefense())
        calls.update(play["public"]["offense_action"]["concept_family"] for play in replay["plays"])
    return calls


def test_adaptive_offense_distribution_differs_from_static_baseline() -> None:
    """Behavioral floor only: adaptation must shift call distribution, not prove better outcomes."""

    seeds = [42, 99, 202, 311, 404]
    static_calls = _offense_concept_multiset(StaticOffense, seeds)
    adaptive_calls = _offense_concept_multiset(AdaptiveOffense, seeds)

    assert adaptive_calls != static_calls
    adaptive_only = set(adaptive_calls) - set(static_calls)
    total_static = sum(static_calls.values())
    total_adaptive = sum(adaptive_calls.values())
    shared_frequency_shift = any(
        abs((adaptive_calls[concept] / total_adaptive) - (static_calls[concept] / total_static)) > 0.15
        for concept in set(adaptive_calls) & set(static_calls)
    )
    assert adaptive_only or shared_frequency_shift
