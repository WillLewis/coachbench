from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from coachbench.contracts import validate_film_room_tweak_schema, validate_replay_contract
from coachbench.engine import CoachBenchEngine


def _live_profile_parameters() -> set[str]:
    profiles = json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))
    return {
        parameter
        for bucket in profiles.values()
        for profile in bucket.values()
        for parameter in profile["parameters"]
    }


def _events_by_play(replay: dict[str, Any]) -> dict[int, set[tuple[str, str]]]:
    events: dict[int, set[tuple[str, str]]] = {}
    for play in replay["plays"]:
        play_index = int(play["public"]["play_index"])
        events[play_index] = set()
        for section in ("public", "offense_observed", "defense_observed"):
            for event in play[section]["events"]:
                events[play_index].add((event["graph_card_id"], event["tag"]))
    return events


def test_film_room_structured_tweaks_conform_and_persist() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())

    assert replay["film_room_tweaks"]
    assert replay["film_room"]["film_room_tweaks"] == replay["film_room_tweaks"]
    for tweak in replay["film_room_tweaks"]:
        validate_film_room_tweak_schema(tweak)
    validate_replay_contract(replay)


def test_film_room_structured_tweak_evidence_resolves_to_replay_events() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    events_by_play = _events_by_play(replay)

    for tweak in replay["film_room_tweaks"]:
        graph_card_id = tweak["source"]["graph_card_id"]
        event_tag = tweak["rationale"]["arguments"]["event_tag"]
        for play_index in tweak["evidence"]["play_indices"]:
            assert (graph_card_id, event_tag) in events_by_play[play_index]


def test_film_room_structured_tweaks_only_reference_live_profile_parameters() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(AdaptiveOffense(), AdaptiveDefense())
    live_parameters = _live_profile_parameters()

    assert replay["film_room_tweaks"]
    for tweak in replay["film_room_tweaks"]:
        assert tweak["parameter"] in live_parameters
