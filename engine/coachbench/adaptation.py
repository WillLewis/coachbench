from __future__ import annotations

from typing import Any


REASON_ORDER = ("graph-fire", "belief-shift", "counter-call")


def _public(play: dict[str, Any]) -> dict[str, Any]:
    return play.get("public", play)


def _beliefs(play: dict[str, Any]) -> dict[str, float]:
    public = _public(play)
    beliefs = public.get("beliefs")
    if isinstance(beliefs, dict):
        return beliefs
    observed = play.get("offense_observed", {})
    beliefs = observed.get("belief_after")
    return beliefs if isinstance(beliefs, dict) else {}


def _offense_call(play: dict[str, Any]) -> str | None:
    action = _public(play).get("offense_action", {})
    return action.get("concept_family")


def _defense_call(play: dict[str, Any]) -> str | None:
    action = _public(play).get("defense_action", {})
    return action.get("coverage_family")


def _cards(play: dict[str, Any]) -> list[str]:
    return list(_public(play).get("graph_card_ids") or [])


def _card_map(graph_cards: dict[str, Any] | list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if isinstance(graph_cards, list):
        return {card["id"]: card for card in graph_cards}
    return graph_cards


def classify_adaptation_reasons(
    plays: list[dict[str, Any]],
    graph_cards: dict[str, Any] | list[dict[str, Any]],
) -> dict[int, str]:
    cards_by_id = _card_map(graph_cards)
    seen_cards: set[str] = set()
    reasons: dict[int, str] = {}

    for index, play in enumerate(plays):
        current_cards = _cards(play)
        first_fire = any(card_id not in seen_cards for card_id in current_cards)
        if first_fire:
            reasons[index] = "graph-fire"

        if index > 0 and index not in reasons:
            prior_beliefs = _beliefs(plays[index - 1])
            current_beliefs = _beliefs(play)
            for key in set(prior_beliefs) | set(current_beliefs):
                if abs(float(current_beliefs.get(key, 0)) - float(prior_beliefs.get(key, 0))) >= 0.10:
                    reasons[index] = "belief-shift"
                    break

        if index > 0 and index not in reasons:
            prior_cards = _cards(plays[index - 1])
            counters = {
                counter
                for card_id in prior_cards
                for counter in cards_by_id.get(card_id, {}).get("counters", [])
            }
            if counters:
                prior_offense, current_offense = _offense_call(plays[index - 1]), _offense_call(play)
                prior_defense, current_defense = _defense_call(plays[index - 1]), _defense_call(play)
                offense_counter = current_offense != prior_offense and current_offense in counters
                defense_counter = current_defense != prior_defense and current_defense in counters
                if offense_counter or defense_counter:
                    reasons[index] = "counter-call"

        seen_cards.update(current_cards)

    return reasons


def classify_adaptation(
    plays: list[dict[str, Any]],
    graph_cards: dict[str, Any] | list[dict[str, Any]],
) -> set[int]:
    return set(classify_adaptation_reasons(plays, graph_cards))
