from __future__ import annotations

import signal
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from .base import DeterministicFallback
from .sanitized_observation import build_tier_observation


class DeadlineExceeded(TimeoutError):
    pass


@contextmanager
def deadline(timeout_ms: int):
    if not hasattr(signal, "SIGALRM") or timeout_ms <= 0:
        yield
        return

    def _raise(_signum, _frame):
        raise DeadlineExceeded("tier adapter deadline exceeded")

    old = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@dataclass
class TieredAgent:
    adapter: Any
    side: str
    fallback: DeterministicFallback = field(default_factory=lambda: DeterministicFallback("tier_fallback"))
    per_call_timeout_ms: int = 50
    name: str = "Tiered Agent"

    def __post_init__(self) -> None:
        self.access_tier = getattr(self.adapter, "access_tier", "unknown")
        self.name = getattr(self.adapter, "name", self.name)
        self.fallback_count = 0
        self.fallback_reasons: list[str] = []
        self.observations_seen: list[Any] = []

    def _legal_actions(self, legal: Any) -> list[str]:
        return legal.legal_offense_concepts() if self.side == "offense" else legal.legal_defense_calls()

    def choose_action(self, observation: dict, memory: Any, legal: Any):
        legal_actions = self._legal_actions(legal)
        resources = observation.get("own_resource_remaining", {})
        obs = build_tier_observation(self.side, observation, memory, legal_actions, resources)
        self.observations_seen.append(obs)
        reason = None
        try:
            with deadline(self.per_call_timeout_ms):
                pick = self.adapter.choose_action(obs)
        except Exception:
            pick = self.fallback.choose(obs)
            reason = "tier_timeout_or_exception"
        if pick not in obs.legal_actions:
            pick = self.fallback.choose(obs)
            reason = "tier_invalid_action"
        if reason:
            self.fallback_count += 1
            self.fallback_reasons.append(reason)
        if self.side == "offense":
            return legal.build_offense_action(pick, "balanced")
        return legal.build_defense_action(pick, "balanced")
