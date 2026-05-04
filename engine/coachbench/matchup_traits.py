from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_TRAITS = (
    "offense_explosive_propensity",
    "offense_screen_self_belief",
    "offense_run_commitment",
    "defense_disguise_quality",
    "defense_pressure_discipline",
    "defense_redzone_density",
    "matchup_volatility",
)


@dataclass(frozen=True)
class MatchupTraits:
    matchup_id: str
    label: str
    values: dict[str, float]
    notes: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "matchup_id": self.matchup_id,
            "label": self.label,
            "values": dict(self.values),
            "notes": self.notes,
        }


def load_matchup_traits(path: Path | str) -> MatchupTraits:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    traits = MatchupTraits(
        matchup_id=payload.get("matchup_id", ""),
        label=payload.get("label", ""),
        values={key: float(value) for key, value in payload.get("values", {}).items()},
        notes=payload.get("notes", ""),
    )
    validate_matchup_traits_obj(traits)
    return traits


def validate_matchup_traits_obj(traits: MatchupTraits) -> None:
    expected = set(ALLOWED_TRAITS)
    found = set(traits.values)
    if found != expected:
        raise ValueError(f"Matchup traits must match allowed traits; missing={sorted(expected - found)} extra={sorted(found - expected)}")
    for key, value in traits.values.items():
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"Matchup trait {key} must be in [0, 1]")


def has_nonzero_trait_modifier(traits: MatchupTraits) -> bool:
    return any(float(value) != 0.5 for value in traits.values.values())


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _finish(epa: float, success: float, noise: int) -> tuple[float, float, int]:
    return round(_clamp(epa, -0.15, 0.15), 4), round(_clamp(success, -0.10, 0.10), 4), int(_clamp(noise, -2, 2))


def offense_trait_modifier(traits: MatchupTraits, concept: str) -> tuple[float, float, int]:
    epa = 0.0
    success = 0.0
    if concept in {"vertical_shot", "play_action_flood"}:
        value = traits.values["offense_explosive_propensity"] - 0.5
        epa += value * 0.16
        success += value * 0.10
    if concept in {"screen", "rpo_glance"}:
        value = traits.values["offense_screen_self_belief"] - 0.5
        epa += value * 0.12
        success += value * 0.08
    if concept in {"inside_zone", "outside_zone", "power_counter"}:
        value = traits.values["offense_run_commitment"] - 0.5
        epa += value * 0.10
        success += value * 0.06
    noise = int(round((traits.values["matchup_volatility"] - 0.5) * 4))
    return _finish(epa, success, noise)


def defense_trait_modifier(traits: MatchupTraits, coverage: str) -> tuple[float, float, int]:
    epa = 0.0
    success = 0.0
    if coverage in {"simulated_pressure", "trap_coverage", "two_high_shell"}:
        value = traits.values["defense_disguise_quality"] - 0.5
        epa -= value * 0.16
        success -= value * 0.10
    if coverage in {"zero_pressure", "simulated_pressure"}:
        value = traits.values["defense_pressure_discipline"] - 0.5
        success -= value * 0.10
    if coverage in {"redzone_bracket", "cover1_man"}:
        value = traits.values["defense_redzone_density"] - 0.5
        epa -= value * 0.12
    return _finish(epa, success, 0)
