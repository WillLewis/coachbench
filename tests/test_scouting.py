from __future__ import annotations

import json
from pathlib import Path

from coachbench.contracts import validate_scouting_report
from coachbench.matchup_traits import load_matchup_traits
from coachbench.scouting import generate_scouting_report, load_scouting_report


REPORTS = [
    Path("data/scouting_reports/neutral_fresh_complete.json"),
    Path("data/scouting_reports/pass_heavy_stale.json"),
    Path("data/scouting_reports/trap_defense_partial.json"),
]


def test_scouting_samples_load_and_validate() -> None:
    for path in REPORTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_scouting_report(payload)
        assert load_scouting_report(path).report_id == payload["report_id"]


def test_generate_scouting_report_is_deterministic() -> None:
    traits = load_matchup_traits("data/matchup_traits/pass_heavy_offense_v0.json")
    first = generate_scouting_report(traits, "stale", 0.6, 11)
    second = generate_scouting_report(traits, "stale", 0.6, 11)
    assert first == second


def test_fresh_complete_estimates_stay_close_to_true_traits() -> None:
    traits = load_matchup_traits("data/matchup_traits/trap_defense_v0.json")
    report = generate_scouting_report(traits, "fresh", 1.0, 17)
    for key, estimate in report.estimated_traits.items():
        assert estimate is not None
        assert abs(estimate - traits.values[key]) <= 0.05


def test_zero_completeness_yields_all_none_estimates() -> None:
    traits = load_matchup_traits("data/matchup_traits/trap_defense_v0.json")
    report = generate_scouting_report(traits, "fresh", 0.0, 17)
    assert all(value is None for value in report.estimated_traits.values())


def test_report_id_is_stable() -> None:
    traits = load_matchup_traits("data/matchup_traits/neutral_v0.json")
    report = generate_scouting_report(traits, "fresh", 1.0, 3)
    assert report.report_id == "scout_fictional_neutral_v0_fresh_3"
