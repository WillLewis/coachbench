from __future__ import annotations

from coachbench.film_room import build_film_room, film_room_tweak_for_card
from coachbench.graph_loader import StrategyGraph


def _play(index: int, card: dict, expected_value: float = 0.1) -> dict:
    event = dict(card["tactical_events"][0])
    event["graph_card_id"] = card["id"]
    return {
        "public": {
            "play_index": index,
            "terminal_reason": None,
            "graph_card_ids": [card["id"]],
            "offense_action": {"concept_family": card["offense_concepts"][0]},
            "defense_action": {"coverage_family": card["defense_calls"][0]},
            "resource_budget_snapshot": {
                "offense_remaining": {"protection": 10 - index, "spacing": 9 - index},
            },
        },
        "engine_internal": {"expected_value_delta": expected_value},
        "offense_observed": {
            "events": [event],
            "belief_after": {"true_pressure_confidence": 0.2 + index * 0.06},
        },
        "defense_observed": {"events": [event], "belief_after": {}},
    }


def _cards_with_legal_tweaks() -> list[dict]:
    return [
        card
        for card in StrategyGraph().interactions
        if film_room_tweak_for_card(card) is not None
    ]


def test_film_room_tweaks_drop_nonlegal_counters() -> None:
    card = next(card for card in StrategyGraph().interactions if card["id"] == "redzone.play_action_after_run_tendency.v1")
    tweak = film_room_tweak_for_card(card)

    assert tweak is not None
    assert "Edge Contain" not in tweak
    assert "Red-Zone Bracket" in tweak
    assert "Two-High Shell" in tweak


def test_film_room_dedupes_repeated_card_tweaks() -> None:
    card = _cards_with_legal_tweaks()[0]
    room = build_film_room([_play(1, card), _play(3, card), _play(5, card)], points=0)

    assert len(room["suggested_tweaks"]) == 1


def test_film_room_tweaks_cap_at_four_distinct_cards() -> None:
    cards = _cards_with_legal_tweaks()[:7]
    room = build_film_room([_play(index, card, index / 10) for index, card in enumerate(cards, start=1)], points=0)

    assert len(room["suggested_tweaks"]) == 4


def test_adaptation_chain_is_ordered_and_capped() -> None:
    cards = _cards_with_legal_tweaks()[:7]
    room = build_film_room([_play(index, card, index / 10) for index, card in enumerate(cards, start=1)], points=0)
    indexes = [entry["play_index"] for entry in room["adaptation_chain"]]

    assert len(room["adaptation_chain"]) == 6
    assert indexes == sorted(indexes)


def test_next_adjustment_is_single_legal_string() -> None:
    card = next(card for card in StrategyGraph().interactions if card["id"] == "redzone.play_action_after_run_tendency.v1")
    room = build_film_room([_play(1, card)], points=0)

    assert isinstance(room["next_adjustment"], str)
    assert room["next_adjustment"].startswith("Next try: ")
    assert "Edge Contain" not in room["next_adjustment"]
