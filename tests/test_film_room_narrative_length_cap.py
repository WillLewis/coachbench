from __future__ import annotations

from coachbench import film_room
from coachbench.film_room import NARRATIVE_MAX_CHARS, narrative_for_drive


def _play() -> dict:
    return {
        "public": {
            "play_index": 1,
            "expected_value_delta": 1.0,
            "offense_action": {"concept_family": "quick_game"},
            "defense_action": {"coverage_family": "cover3_match"},
            "events": [{"tag": "pressure_punished", "graph_card_id": "redzone.screen_vs_zero_pressure.v1"}],
            "graph_card_ids": ["redzone.screen_vs_zero_pressure.v1"],
            "terminal_reason": "touchdown",
        },
        "offense_observed": {"events": [{"tag": "pressure_punished", "graph_card_id": "redzone.screen_vs_zero_pressure.v1"}]},
        "defense_observed": {"events": [{"tag": "pressure_punished", "graph_card_id": "redzone.screen_vs_zero_pressure.v1"}]},
    }


def test_narrative_never_exceeds_length_cap(monkeypatch) -> None:
    monkeypatch.setattr(film_room, "card_label", lambda *args, **kwargs: "Card " + ("x" * 240))
    narrative = narrative_for_drive({"points": 7, "adaptation_chain": []}, [_play()])
    assert narrative is None or len(narrative) <= NARRATIVE_MAX_CHARS
