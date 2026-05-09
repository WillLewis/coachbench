from __future__ import annotations

from coachbench.film_room import NO_EVENT_FILM_ROOM_NOTE, narrative_for_drive


def test_narrative_returns_none_for_no_event_drive() -> None:
    plays = [
        {
            "public": {
                "play_index": 1,
                "expected_value_delta": 0.0,
                "offense_action": {"concept_family": "quick_game"},
                "defense_action": {"coverage_family": "cover3_match"},
                "events": [],
                "graph_card_ids": [],
                "terminal_reason": "max_plays_reached",
            },
            "offense_observed": {"events": []},
            "defense_observed": {"events": []},
        }
    ]
    assert narrative_for_drive({"notes": [NO_EVENT_FILM_ROOM_NOTE], "adaptation_chain": []}, plays) is None
