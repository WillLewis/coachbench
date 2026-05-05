from __future__ import annotations

from arena.tiers import ACCESS_TIERS, TIER_LABELS
from arena.storage.registry import SCHEMA


def test_tier_constants_match_registry_check() -> None:
    assert ACCESS_TIERS == ("declarative", "prompt_policy", "remote_endpoint", "sandboxed_code")
    assert set(TIER_LABELS) == set(ACCESS_TIERS)
    for tier in ACCESS_TIERS:
        assert tier in SCHEMA
