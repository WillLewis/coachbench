from __future__ import annotations

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import validate_inference_report
from coachbench.engine import CoachBenchEngine
from coachbench.matchup_traits import load_matchup_traits


def test_no_matchup_traits_means_no_inference_report() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    assert "inference_report" not in replay


def test_nonneutral_traits_create_valid_inference_report() -> None:
    traits = load_matchup_traits("data/matchup_traits/pass_heavy_offense_v0.json")
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), matchup_traits=traits)
    validate_inference_report(replay["inference_report"])
    assert 0 <= replay["inference_report"]["offense_calibration"]["mean_absolute_error"] <= 1


def test_hostile_traits_create_nonzero_calibration_error() -> None:
    traits = load_matchup_traits("data/matchup_traits/trap_defense_v0.json")
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense(), matchup_traits=traits)
    validate_inference_report(replay["inference_report"])
    assert replay["inference_report"]["offense_calibration"]["mean_absolute_error"] > 0
