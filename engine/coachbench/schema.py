from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional

Side = Literal["offense", "defense"]


@dataclass(frozen=True)
class GameState:
    down: int = 1
    distance: int = 10
    yardline: int = 22
    play_index: int = 0
    max_plays: int = 8
    points: int = 0
    terminal: bool = False
    terminal_reason: Optional[str] = None

    def to_public_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OffenseAction:
    personnel_family: str
    formation_family: str
    motion_family: str
    concept_family: str
    protection_family: str
    risk_level: str
    constraint_tag: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DefenseAction:
    personnel_family: str
    front_family: str
    coverage_family: str
    pressure_family: str
    disguise_family: str
    matchup_focus: str
    risk_level: str
    constraint_tag: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeliefState:
    true_pressure_confidence: float = 0.30
    simulated_pressure_risk: float = 0.30
    match_coverage_stress: float = 0.25
    run_fit_aggression: float = 0.25
    screen_trap_risk: float = 0.25

    def clamp(self) -> "BeliefState":
        for key in self.__dataclass_fields__:
            value = getattr(self, key)
            setattr(self, key, round(max(0.0, min(1.0, float(value))), 4))
        return self

    def to_dict(self) -> Dict[str, float]:
        return {
            key: round(float(value), 4)
            for key, value in asdict(self).items()
        }


@dataclass
class AgentMemory:
    own_recent_calls: List[str] = field(default_factory=list)
    opponent_visible_tendencies: Dict[str, int] = field(default_factory=dict)
    beliefs: BeliefState = field(default_factory=BeliefState)

    def remember_own_call(self, concept: str) -> None:
        self.own_recent_calls.append(concept)
        self.own_recent_calls[:] = self.own_recent_calls[-5:]

    def increment_tendency(self, key: str) -> None:
        self.opponent_visible_tendencies[key] = self.opponent_visible_tendencies.get(key, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "own_recent_calls": list(self.own_recent_calls),
            "opponent_visible_tendencies": dict(self.opponent_visible_tendencies),
            "beliefs": self.beliefs.to_dict(),
        }


@dataclass
class PlayResolution:
    play_index: int
    offense_action: OffenseAction
    defense_action: DefenseAction
    events: List[Dict[str, Any]]
    yards_gained: int
    expected_value_delta: float
    success: bool
    terminal: bool
    terminal_reason: Optional[str]
    next_state: GameState
    graph_card_ids: List[str]
    offense_belief_after: Dict[str, float]
    defense_belief_after: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "play_index": self.play_index,
            "offense_action": self.offense_action.to_dict(),
            "defense_action": self.defense_action.to_dict(),
            "events": self.events,
            "yards_gained": self.yards_gained,
            "expected_value_delta": round(self.expected_value_delta, 3),
            "success": self.success,
            "terminal": self.terminal,
            "terminal_reason": self.terminal_reason,
            "next_state": self.next_state.to_public_dict(),
            "graph_card_ids": self.graph_card_ids,
            "offense_belief_after": self.offense_belief_after,
            "defense_belief_after": self.defense_belief_after,
        }
