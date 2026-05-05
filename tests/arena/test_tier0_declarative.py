from __future__ import annotations

from arena.tiers.bridge import TieredAgent
from arena.tiers.declarative import Tier0Adapter, load_tier0_config, validate_tier_config_dict
from coachbench.engine import CoachBenchEngine
from agents.static_defense import StaticDefense


def test_tier0_examples_load_and_run_deterministically() -> None:
    config = load_tier0_config(__import__("pathlib").Path("data/agent_configs/tier0_efficiency_optimizer.json"))
    agent = TieredAgent(Tier0Adapter(config), "offense")
    replay_a = CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), max_plays=6)
    agent_b = TieredAgent(Tier0Adapter(config), "offense")
    replay_b = CoachBenchEngine(seed=42).run_drive(agent_b, StaticDefense(), max_plays=6)
    assert replay_a == replay_b
    assert all(play["public"]["offense_action"]["concept_family"] != "vertical_shot" for play in replay_a["plays"])


def test_tier0_unknown_field_rejects() -> None:
    payload = {
        "agent_name": "Config Agent",
        "side": "offense",
        "access_tier": "declarative",
        "preferred_concepts": ["quick_game"],
        "constraints": {},
        "surprise": True,
    }
    try:
        validate_tier_config_dict(payload)
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("expected rejection")
