from __future__ import annotations

import json
from pathlib import Path

from coachbench.contracts import DEFENSE_ACTION_FIELDS, OFFENSE_ACTION_FIELDS


ROOT = Path(".")


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_static_ui_replay_has_renderable_phase_0b_panel_data() -> None:
    replay = _load_json("ui/static_proof_replay.json")
    graph = _load_json("graph/redzone_v0/interactions.json")
    graph_ids = {card["id"] for card in graph["interactions"]}

    assert replay["metadata"]["mode"] == "static_proof"
    assert replay["score"]["result"]
    assert replay["plays"]
    assert replay["film_room"]["notes"]
    assert replay["film_room"]["suggested_tweaks"]

    for play in replay["plays"]:
        public = play["public"]
        assert OFFENSE_ACTION_FIELDS <= set(public["offense_action"])
        assert DEFENSE_ACTION_FIELDS <= set(public["defense_action"])
        for key in ("yards_gained", "expected_value_delta", "success", "terminal", "terminal_reason", "next_state"):
            assert key in public
        for key in ("offense_before", "offense_cost", "offense_remaining", "defense_before", "defense_cost", "defense_remaining"):
            assert public["resource_budget_snapshot"][key]
        assert "ok" in public["validation_result"]
        for card_id in public["graph_card_ids"]:
            assert card_id in graph_ids
        assert play["offense_observed"]["belief_after"]
        assert "events" in public


def test_agent_garage_shell_has_plan_5_2_controls_or_dash_fallback() -> None:
    replay = _load_json("ui/static_proof_replay.json")
    offense = replay["agent_garage_config"]["offense_profile"]
    defense = replay["agent_garage_config"]["defense_profile"]
    controls = (
        "offensive_archetype",
        "defensive_archetype",
        "risk_tolerance",
        "adaptation_speed",
        "pressure_punish_threshold",
        "screen_trigger_confidence",
        "explosive_shot_tolerance",
        "run_pass_tendency",
        "disguise_sensitivity",
        "counter_repeat_tolerance",
        "resource_conservation",
    )

    assert set(offense) <= set(controls) | {"label", "source"}
    assert set(defense) <= set(controls) | {"label", "source"}
    assert any(key not in offense for key in controls)
    assert any(key not in defense for key in controls)
    script = Path("ui/app.js").read_text(encoding="utf-8")
    for key in controls:
        assert key in script


def test_ui_defaults_to_demo_replay_before_static_fallback() -> None:
    script = Path("ui/app.js").read_text(encoding="utf-8")

    assert "'seed-42': 'demo_replay.json'" in script
    assert "'static-proof': 'static_proof_replay.json'" in script
    assert "if (id === 'seed-42') return fetchJson(replaySources['static-proof']);" in script
    assert "Phase 0B static schema/UI proof" in script
