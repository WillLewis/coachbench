from __future__ import annotations

import json
from pathlib import Path

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import validate_calibration_report
from coachbench.engine import CoachBenchEngine


def _rate(values: list[bool]) -> float:
    return sum(1.0 if value else 0.0 for value in values) / len(values)


def test_calibration_sanity_ranges_hold_for_adaptive_matchup() -> None:
    config = json.loads(Path("data/calibration/sanity_ranges.json").read_text(encoding="utf-8"))
    validate_calibration_report(config)

    replays = [
        CoachBenchEngine(seed=int(seed)).run_drive(AdaptiveOffense(), AdaptiveDefense())
        for seed in config["seeds"]
    ]
    metrics = {
        "mean_points_per_drive": sum(replay["score"]["points"] for replay in replays) / len(replays),
        "touchdown_rate": _rate([replay["score"]["result"] == "touchdown" for replay in replays]),
        "field_goal_rate": _rate([replay["score"]["result"] == "field_goal" for replay in replays]),
        "turnover_rate": _rate([replay["metadata"]["drive_terminal_condition"] == "turnover" for replay in replays]),
        "mean_plays_per_drive": sum(len(replay["plays"]) for replay in replays) / len(replays),
        "invalid_action_rate": sum(replay["score"]["invalid_action_count"] for replay in replays) / len(replays),
    }

    assert metrics["invalid_action_rate"] == 0.0
    for metric, value in metrics.items():
        bounds = config["ranges"][metric]
        assert bounds["min"] <= value <= bounds["max"], f"{metric}={value} outside {bounds}"
