from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arena.api.deps import moderate
from coachbench.graph_loader import StrategyGraph

ALLOWED_FIELDS = {
    "agent_name",
    "side",
    "access_tier",
    "risk_tolerance",
    "red_zone",
    "third_down",
    "preferred_concepts",
    "avoided_concepts",
    "adaptation_speed",
    "tendency_break_rate",
    "constraints",
}
ALLOWED_RISK = {"low", "medium", "high"}


@dataclass(frozen=True)
class Tier0Config:
    agent_name: str
    side: str
    access_tier: str
    risk_tolerance: str
    red_zone: dict
    third_down: dict
    preferred_concepts: list[str]
    avoided_concepts: list[str]
    adaptation_speed: float
    tendency_break_rate: float
    constraints: dict


def validate_tier_config_dict(payload: dict[str, Any]) -> None:
    extra = set(payload) - ALLOWED_FIELDS
    if extra:
        raise ValueError(f"unknown tier0 fields: {sorted(extra)}")
    if payload.get("access_tier") != "declarative":
        raise ValueError("tier0 config access_tier must be declarative")
    if payload.get("side") not in {"offense", "defense"}:
        raise ValueError("side must be offense or defense")
    if payload.get("risk_tolerance", "medium") not in ALLOWED_RISK:
        raise ValueError("risk_tolerance must be low, medium, or high")
    moderate(str(payload.get("agent_name", "")))
    graph = StrategyGraph()
    vocab = set(graph.offense_concepts() if payload.get("side") == "offense" else graph.defense_calls())
    referenced = set(payload.get("preferred_concepts", [])) | set(payload.get("avoided_concepts", []))
    referenced |= {value for value in dict(payload.get("red_zone", {})).values() if isinstance(value, str)}
    referenced |= {value for value in dict(payload.get("third_down", {})).values() if isinstance(value, str)}
    unknown = referenced - vocab
    if unknown:
        raise ValueError(f"unknown tier0 concepts: {sorted(unknown)}")


def load_tier0_config(path: Path) -> Tier0Config:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_tier_config_dict(payload)
    return Tier0Config(
        agent_name=payload["agent_name"],
        side=payload["side"],
        access_tier="declarative",
        risk_tolerance=payload.get("risk_tolerance", "medium"),
        red_zone=dict(payload.get("red_zone", {})),
        third_down=dict(payload.get("third_down", {})),
        preferred_concepts=list(payload.get("preferred_concepts", [])),
        avoided_concepts=list(payload.get("avoided_concepts", [])),
        adaptation_speed=float(payload.get("adaptation_speed", 0.5)),
        tendency_break_rate=float(payload.get("tendency_break_rate", 0.0)),
        constraints=dict(payload.get("constraints", {})),
    )


class Tier0Adapter:
    access_tier = "declarative"

    def __init__(self, config: Tier0Config) -> None:
        self.config = config
        self.name = config.agent_name

    def _allowed_by_rate(self, concept: str, obs) -> bool:
        key = f"max_{concept}_rate"
        if key not in self.config.constraints:
            return True
        limit = float(self.config.constraints[key])
        recent = obs.memory_summary.get("own_recent_calls", [])
        total = max(1, len(recent))
        return (recent.count(concept) / total) < limit

    def choose_action(self, obs) -> str:
        legal = [item for item in obs.legal_actions if self._allowed_by_rate(item, obs)]
        if not legal:
            legal = list(obs.legal_actions)
        legal_non_avoided = [item for item in legal if item not in self.config.avoided_concepts]
        candidates = legal_non_avoided or legal
        state = obs.game_state
        third_pick = self.config.third_down.get("default")
        if int(state.get("down") or 0) >= 3 and third_pick in candidates:
            return third_pick
        red_pick = self.config.red_zone.get("default")
        if int(state.get("yardline") or 99) <= 5 and red_pick in candidates:
            return red_pick
        for concept in self.config.preferred_concepts:
            if concept in candidates:
                return concept
        return sorted(candidates)[0]
