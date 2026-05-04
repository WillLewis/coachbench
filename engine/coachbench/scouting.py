from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .matchup_traits import ALLOWED_TRAITS, MatchupTraits


FRESHNESS = ("fresh", "stale")
CONFIDENCE = ("low", "medium", "high")
BELIEF_TO_TRAIT = {
    "true_pressure_confidence": "offense_explosive_propensity",
    "simulated_pressure_risk": "defense_disguise_quality",
    "match_coverage_stress": "defense_redzone_density",
    "run_fit_aggression": "offense_run_commitment",
    "screen_trap_risk": "offense_screen_self_belief",
}


@dataclass(frozen=True)
class ScoutingReport:
    report_id: str
    label: str
    freshness: str
    completeness: float
    estimated_traits: dict[str, float | None]
    confidence: dict[str, str]
    notes: str

    def to_agent_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "freshness": self.freshness,
            "completeness": self.completeness,
            "estimated_traits": dict(self.estimated_traits),
            "confidence": dict(self.confidence),
            "notes": self.notes,
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "label": self.label,
            **self.to_agent_dict(),
        }


def load_scouting_report(path: Path | str) -> ScoutingReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    report = ScoutingReport(
        report_id=payload.get("report_id", ""),
        label=payload.get("label", ""),
        freshness=payload.get("freshness", ""),
        completeness=float(payload.get("completeness", 0.0)),
        estimated_traits=dict(payload.get("estimated_traits", {})),
        confidence=dict(payload.get("confidence", {})),
        notes=payload.get("notes", ""),
    )
    validate_scouting_report_obj(report)
    return report


def validate_scouting_report_obj(report: ScoutingReport) -> None:
    if report.freshness not in FRESHNESS:
        raise ValueError(f"Scouting freshness must be one of {FRESHNESS}")
    if not 0.0 <= report.completeness <= 1.0:
        raise ValueError("Scouting completeness must be in [0, 1]")
    if set(report.estimated_traits) != set(ALLOWED_TRAITS):
        raise ValueError("Scouting estimated traits must match allowed traits")
    if set(report.confidence) != set(ALLOWED_TRAITS):
        raise ValueError("Scouting confidence must match allowed traits")
    for key, value in report.estimated_traits.items():
        if value is not None and not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"Scouting estimate {key} must be in [0, 1] or null")
        if report.confidence[key] not in CONFIDENCE:
            raise ValueError(f"Scouting confidence {key} is invalid")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def generate_scouting_report(
    true_traits: MatchupTraits,
    freshness: str,
    completeness: float,
    noise_seed: int,
) -> ScoutingReport:
    if freshness not in FRESHNESS:
        raise ValueError(f"Scouting freshness must be one of {FRESHNESS}")
    rng = random.Random(noise_seed)
    scale = 0.05 if freshness == "fresh" else 0.20
    estimates = {
        trait: round(_clamp01(value + rng.uniform(-scale, scale)), 4)
        for trait, value in sorted(true_traits.values.items())
    }
    drop_count = int((1.0 - completeness) * len(ALLOWED_TRAITS))
    for trait in sorted(ALLOWED_TRAITS)[:drop_count]:
        estimates[trait] = None
    confidence = {
        trait: "low" if estimates[trait] is None or freshness == "stale" else "high"
        for trait in ALLOWED_TRAITS
    }
    report = ScoutingReport(
        report_id=f"scout_{true_traits.matchup_id}_{freshness}_{noise_seed}",
        label=f"{true_traits.label} Scouting",
        freshness=freshness,
        completeness=round(completeness, 4),
        estimated_traits=estimates,
        confidence=confidence,
        notes="Fictional deterministic scouting estimate.",
    )
    validate_scouting_report_obj(report)
    return report


def belief_calibration_error(
    true_traits: MatchupTraits,
    agent_beliefs: dict[str, float],
    mapped_traits: list[str] | None = None,
) -> dict[str, Any]:
    selected = mapped_traits or list(BELIEF_TO_TRAIT)
    per_trait = {}
    calibrated_traits = []
    for belief_key in selected:
        trait = BELIEF_TO_TRAIT.get(belief_key)
        if trait is None or belief_key not in agent_beliefs:
            continue
        per_trait[trait] = round(abs(float(agent_beliefs[belief_key]) - float(true_traits.values[trait])), 4)
        calibrated_traits.append(trait)
    mae = round(sum(per_trait.values()) / len(per_trait), 4) if per_trait else 0.0
    return {
        "per_trait_error": per_trait,
        "mean_absolute_error": mae,
        "calibrated_traits": calibrated_traits,
    }
