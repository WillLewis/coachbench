from __future__ import annotations

from typing import Any

from coachbench.schema import AgentMemory, OffenseAction


class ExampleScoutingOffense:
    name = "Example Scouting Offense"

    def __init__(self) -> None:
        self._report: dict[str, Any] | None = None
        self.report_count = 0
        self.first_choose_saw_report = False

    def pre_drive_observation(self, report: dict[str, Any]) -> None:
        self.report_count += 1
        self._report = dict(report)

    def choose_action(self, observation: dict[str, Any], memory: AgentMemory, legal: Any) -> OffenseAction:
        self.first_choose_saw_report = self._report is not None
        legal_concepts = observation.get("legal_concepts", [])
        estimates = (self._report or {}).get("estimated_traits", {})
        confidence = (self._report or {}).get("confidence", {})
        if (
            estimates.get("offense_explosive_propensity", 0.0) is not None
            and estimates.get("offense_explosive_propensity", 0.0) > 0.6
            and confidence.get("offense_explosive_propensity") == "high"
            and "vertical_shot" in legal_concepts
        ):
            return legal.build_offense_action("vertical_shot", "balanced")
        if "quick_game" in legal_concepts:
            return legal.build_offense_action("quick_game", "conservative")
        return legal.build_offense_action(legal.legal_offense_concepts()[0], "conservative")
