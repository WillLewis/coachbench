from __future__ import annotations

from arena.tiers.badges import derive_badges


def test_badges_by_tier() -> None:
    assert {"config_agent", "hidden_state_safe", "verified_replayable"} <= set(derive_badges({"access_tier": "declarative", "qualification_status": "passed"}))
    assert "prompt_agent" in derive_badges({"access_tier": "prompt_policy"})
    assert "remote_agent" in derive_badges({"access_tier": "remote_endpoint"})
    assert {"sandboxed_agent", "network_off"} <= set(derive_badges({"access_tier": "sandboxed_code"}))
