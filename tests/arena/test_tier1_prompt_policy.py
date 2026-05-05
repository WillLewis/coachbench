from __future__ import annotations

import json
from pathlib import Path

from arena.tiers.bridge import TieredAgent
from arena.tiers.prompt_policy import Tier1Adapter, load_tier1_config, validate_tier1_config_dict
from agents.static_defense import StaticDefense
from coachbench.engine import CoachBenchEngine


def test_tier1_strategy_prompt_is_documentation_only(tmp_path) -> None:
    source = json.loads(Path("data/agent_configs/tier1_constraint_setter.json").read_text(encoding="utf-8"))
    with_prompt = tmp_path / "with.json"
    without_prompt = tmp_path / "without.json"
    with_prompt.write_text(json.dumps(source), encoding="utf-8")
    source["strategy_prompt"] = "Completely different documentation text."
    without_prompt.write_text(json.dumps(source), encoding="utf-8")
    replay_a = CoachBenchEngine(seed=99).run_drive(TieredAgent(Tier1Adapter(load_tier1_config(with_prompt)), "offense"), StaticDefense())
    replay_b = CoachBenchEngine(seed=99).run_drive(TieredAgent(Tier1Adapter(load_tier1_config(without_prompt)), "offense"), StaticDefense())
    assert replay_a == replay_b


def test_tier1_rejects_unsafe_policy() -> None:
    payload = {
        "agent_name": "Policy Agent",
        "side": "offense",
        "access_tier": "prompt_policy",
        "strategy_prompt": "Use quick game.",
        "constraints": {"require_legal_action": False},
        "rules": [],
    }
    try:
        validate_tier1_config_dict(payload)
    except ValueError as exc:
        assert "require_legal_action" in str(exc)
    else:
        raise AssertionError("expected rejection")
