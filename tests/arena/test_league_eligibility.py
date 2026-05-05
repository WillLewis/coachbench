from __future__ import annotations

from arena.tiers.league import is_eligible


def test_league_eligibility_matrix() -> None:
    assert is_eligible("rookie", "declarative")
    assert not is_eligible("rookie", "prompt_policy")
    assert is_eligible("policy", "prompt_policy")
    assert not is_eligible("policy", "remote_endpoint")
    assert is_eligible("endpoint", "remote_endpoint")
    assert not is_eligible("endpoint", "sandboxed_code")
    assert is_eligible("sandbox", "sandboxed_code")
