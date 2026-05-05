from __future__ import annotations

LEAGUE_ELIGIBILITY = {
    "rookie": {"declarative"},
    "policy": {"declarative", "prompt_policy"},
    "endpoint": {"declarative", "prompt_policy", "remote_endpoint"},
    "sandbox": {"sandboxed_code"},
    "research": {"sandboxed_code"},
}

PUBLIC_LEAGUES = {"rookie", "policy", "endpoint"}


def is_eligible(league: str, access_tier: str) -> bool:
    return access_tier in LEAGUE_ELIGIBILITY.get(league, set())
