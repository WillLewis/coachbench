from __future__ import annotations

import json
from typing import Any

from coachbench.model_observation import render_observation_for_defense, render_observation_for_offense


def _json_payload(rendered: str) -> dict[str, Any]:
    return json.loads(rendered.split("\n", 1)[1])


def _offense_observation() -> dict[str, Any]:
    return {
        "side": "offense",
        "game_state": {"down": 1, "distance": 10, "yardline": 22, "play_index": 0, "max_plays": 8},
        "legal_concepts": ["inside_zone", "quick_game"],
        "own_resource_remaining": {"protection": 14, "spacing": 18},
    }


def _defense_observation() -> dict[str, Any]:
    return {
        "side": "defense",
        "game_state": {"down": 1, "distance": 10, "yardline": 22, "play_index": 0, "max_plays": 8},
        "legal_calls": ["base_cover3", "two_high_shell"],
        "own_resource_remaining": {"rush": 16, "coverage": 20},
    }


def test_render_offense_includes_required_fields() -> None:
    payload = _json_payload(render_observation_for_offense(_offense_observation()))
    assert payload["game_state"]["down"] == 1
    assert payload["legal_concepts"] == ["inside_zone", "quick_game"]
    assert payload["own_resource_remaining"] == {"protection": 14, "spacing": 18}


def test_render_offense_omits_graph_card_ids() -> None:
    observation = _offense_observation() | {
        "graph_card_ids": ["hidden"],
        "belief_after": {"x": 1.0},
        "next_state": {"down": 2},
        "engine_internal": {"debug": True},
    }
    rendered = render_observation_for_offense(observation)
    for forbidden in ("graph_card_ids", "belief_after", "next_state", "engine_internal"):
        assert forbidden not in rendered


def test_render_offense_includes_events_when_present() -> None:
    observation = _offense_observation() | {"events": [{"tag": "visible"}]}
    assert _json_payload(render_observation_for_offense(observation))["events"] == [{"tag": "visible"}]


def test_render_offense_omits_events_when_absent() -> None:
    assert "events" not in _json_payload(render_observation_for_offense(_offense_observation()))


def test_render_offense_deterministic() -> None:
    observation = _offense_observation()
    assert render_observation_for_offense(observation) == render_observation_for_offense(observation)


def test_render_offense_sorted_keys() -> None:
    rendered = render_observation_for_offense(_offense_observation())
    payload_text = rendered.split("\n", 1)[1]
    assert payload_text.index('"game_state"') < payload_text.index('"legal_concepts"')
    assert payload_text.index('"legal_concepts"') < payload_text.index('"own_resource_remaining"')
    assert payload_text.index('"own_resource_remaining"') < payload_text.index('"side"')


def test_render_defense_includes_required_fields() -> None:
    payload = _json_payload(render_observation_for_defense(_defense_observation()))
    assert payload["game_state"]["down"] == 1
    assert payload["legal_calls"] == ["base_cover3", "two_high_shell"]
    assert payload["own_resource_remaining"] == {"rush": 16, "coverage": 20}


def test_render_defense_omits_graph_card_ids() -> None:
    observation = _defense_observation() | {
        "graph_card_ids": ["hidden"],
        "belief_after": {"x": 1.0},
        "next_state": {"down": 2},
        "engine_internal": {"debug": True},
    }
    rendered = render_observation_for_defense(observation)
    for forbidden in ("graph_card_ids", "belief_after", "next_state", "engine_internal"):
        assert forbidden not in rendered


def test_render_defense_includes_events_when_present() -> None:
    observation = _defense_observation() | {"events": [{"tag": "visible"}]}
    assert _json_payload(render_observation_for_defense(observation))["events"] == [{"tag": "visible"}]


def test_render_defense_omits_events_when_absent() -> None:
    assert "events" not in _json_payload(render_observation_for_defense(_defense_observation()))


def test_render_defense_deterministic() -> None:
    observation = _defense_observation()
    assert render_observation_for_defense(observation) == render_observation_for_defense(observation)


def test_render_defense_sorted_keys() -> None:
    rendered = render_observation_for_defense(_defense_observation())
    payload_text = rendered.split("\n", 1)[1]
    assert payload_text.index('"game_state"') < payload_text.index('"legal_calls"')
    assert payload_text.index('"legal_calls"') < payload_text.index('"own_resource_remaining"')
    assert payload_text.index('"own_resource_remaining"') < payload_text.index('"side"')
