from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMUsage:
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd_est: float = 0.0


ZERO_USAGE = LLMUsage()
