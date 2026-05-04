from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_POSITION_GROUPS = (
    "qb",
    "running_backs",
    "receivers",
    "offensive_line",
    "front_seven",
    "secondary",
)

ALLOWED_TRAITS = {
    "qb": "decision_making",
    "running_backs": "run_power",
    "receivers": "separation",
    "offensive_line": "protection",
    "front_seven": "rush_pressure",
    "secondary": "coverage_tightness",
}

CONCEPT_TO_OFFENSE_GROUPS = {
    "inside_zone": ["running_backs", "offensive_line"],
    "outside_zone": ["running_backs", "offensive_line"],
    "power_counter": ["running_backs", "offensive_line"],
    "quick_game": ["qb", "receivers"],
    "bunch_mesh": ["qb", "receivers"],
    "rpo_glance": ["qb", "running_backs", "receivers"],
    "play_action_flood": ["qb", "receivers", "offensive_line"],
    "vertical_shot": ["qb", "receivers", "offensive_line"],
    "screen": ["qb", "receivers"],
    "bootleg": ["qb", "offensive_line"],
}

COVERAGE_TO_DEFENSE_GROUPS = {
    "base_cover3": ["secondary"],
    "cover3_match": ["secondary"],
    "quarters_match": ["secondary"],
    "cover1_man": ["secondary"],
    "two_high_shell": ["secondary"],
    "zero_pressure": ["front_seven"],
    "simulated_pressure": ["front_seven", "secondary"],
    "bear_front": ["front_seven"],
    "trap_coverage": ["secondary"],
    "redzone_bracket": ["secondary"],
}


@dataclass(frozen=True)
class RosterBudget:
    roster_id: str
    label: str
    budget_points: int
    values: dict[str, int]
    notes: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "roster_id": self.roster_id,
            "label": self.label,
            "budget_points": self.budget_points,
            "values": dict(self.values),
            "notes": self.notes,
        }


def load_roster(path: Path | str) -> RosterBudget:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    groups = payload.get("position_groups", {})
    roster = RosterBudget(
        roster_id=payload.get("roster_id", ""),
        label=payload.get("label", ""),
        budget_points=int(payload.get("budget_points", 0)),
        values={group: groups.get(group, {}).get("value") for group in groups},
        notes=payload.get("notes", ""),
    )
    validate_roster(roster, raw_payload=payload)
    return roster


def validate_roster(roster: RosterBudget, raw_payload: dict[str, Any] | None = None) -> None:
    raw_groups = (raw_payload or {}).get("position_groups", {})
    groups = set(roster.values)
    expected = set(ALLOWED_POSITION_GROUPS)
    if groups != expected:
        raise ValueError(f"Roster groups must match allowed groups; missing={sorted(expected - groups)} extra={sorted(groups - expected)}")
    if raw_payload is not None:
        for group, trait in ALLOWED_TRAITS.items():
            if raw_groups[group].get("trait") != trait:
                raise ValueError(f"Roster group {group} must use trait {trait}")
    total = 0
    for group, value in roster.values.items():
        if not isinstance(value, int) or not 0 <= value <= 100:
            raise ValueError(f"Roster group {group} value must be an integer in [0, 100]")
        total += value
    if total != roster.budget_points:
        raise ValueError(f"Roster total {total} does not equal budget_points {roster.budget_points}")


def _bounded_modifier(roster: RosterBudget, groups: list[str]) -> tuple[float, float]:
    raw = sum((roster.values[group] - 50) / 500 for group in groups) / len(groups)
    epa_delta = max(-0.10, min(0.10, raw))
    success_delta = max(-0.05, min(0.05, raw / 2))
    return round(epa_delta, 4), round(success_delta, 4)


def offense_modifier(roster: RosterBudget, concept: str) -> tuple[float, float]:
    return _bounded_modifier(roster, CONCEPT_TO_OFFENSE_GROUPS.get(concept, [])) if concept in CONCEPT_TO_OFFENSE_GROUPS else (0.0, 0.0)


def defense_modifier(roster: RosterBudget, coverage: str) -> tuple[float, float]:
    return _bounded_modifier(roster, COVERAGE_TO_DEFENSE_GROUPS.get(coverage, [])) if coverage in COVERAGE_TO_DEFENSE_GROUPS else (0.0, 0.0)


def has_nonzero_modifier(roster: RosterBudget) -> bool:
    return any(value != 50 for value in roster.values.values())
