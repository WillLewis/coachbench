from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SanitizedObservation:
    side: str
    game_state: dict
    legal_actions: list[str]
    own_resource_remaining: dict
    memory_summary: dict


class TierAdapter(Protocol):
    access_tier: str

    def choose_action(self, obs: SanitizedObservation) -> str: ...


@dataclass(frozen=True)
class DeterministicFallback:
    reason: str

    def choose(self, obs: SanitizedObservation) -> str:
        return sorted(obs.legal_actions)[0]
