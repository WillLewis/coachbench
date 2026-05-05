from __future__ import annotations

from arena.tiers.sanitized_observation import build_tier_observation
from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS
from coachbench.schema import AgentMemory


def test_sanitized_observation_excludes_hidden_and_admin_fields() -> None:
    raw = {
        "game_state": {"down": 2, "distance": 4, "yardline": 9, "play_index": 1, "points": 0, "max_plays": 8, "seed": 42},
        "seed": 42,
        "seed_hash": "hidden",
        "legal_action_set_id": "hidden",
        "resource_budget_snapshot": {"offense_before": {"spacing": 10}},
        "admin_metadata": "hidden",
    }
    obs = build_tier_observation("offense", raw, AgentMemory(), ["quick_game"], {"spacing": 10})
    encoded = repr(obs)
    for key in HIDDEN_OBSERVATION_FIELDS | {"seed", "seed_hash", "legal_action_set_id", "resource_budget_snapshot", "admin_metadata"}:
        assert key not in encoded
    assert obs.own_resource_remaining == {"spacing": 10}
