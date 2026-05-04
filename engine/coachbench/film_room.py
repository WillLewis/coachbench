from __future__ import annotations

from typing import Any, Dict, List

from .graph_loader import StrategyGraph


def _public_play(play: Dict[str, Any]) -> Dict[str, Any]:
    return play.get("public", play)


def _internal_play(play: Dict[str, Any]) -> Dict[str, Any]:
    return play.get("engine_internal", play)


def _observed_events(play: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "offense_observed" not in play and "defense_observed" not in play:
        return play.get("events", [])

    events_by_tag: Dict[str, Dict[str, Any]] = {}
    for key in ("offense_observed", "defense_observed"):
        for event in play.get(key, {}).get("events", []):
            events_by_tag.setdefault(event["tag"], event)
    return list(events_by_tag.values())


def _graph_cards_by_id(graph: StrategyGraph | None = None) -> Dict[str, Dict[str, Any]]:
    graph = graph or StrategyGraph()
    return {card["id"]: card for card in graph.interactions}


def film_room_note_for_event(event: Dict[str, Any], card: Dict[str, Any]) -> str:
    limitations = card.get("limitations", [])
    limitation_text = f" Limitation: {limitations[0]}" if limitations else ""
    return (
        f"Graph card \"{card['name']}\" fired ({event['tag']}); "
        f"see {card['id']}.{limitation_text}"
    )


def film_room_tweak_for_card(card: Dict[str, Any]) -> str:
    counters = card.get("counters", [])
    if counters:
        return f"Review graph-listed counters for {card['id']}: {', '.join(counters)}."
    return f"Review sequencing around graph card {card['id']}."


def headline_for_terminal(points: int, terminal_reason: str | None) -> str:
    if terminal_reason == "touchdown" or points >= 7:
        return "Touchdown drive"
    if terminal_reason == "turnover":
        return "Turnover"
    if terminal_reason == "turnover_on_downs":
        return "Turnover on downs"
    if terminal_reason == "max_plays_reached":
        return "Stopped - out of plays" if points == 0 else "Field-position drive"
    if points == 3:
        return "Field-position drive"
    return "Drive stopped"


def build_film_room(play_results: List[Dict[str, Any]], points: int, graph: StrategyGraph | None = None) -> Dict[str, Any]:
    if not play_results:
        return {
            "headline": "No plays were resolved.",
            "turning_point": None,
            "notes": [],
            "suggested_tweaks": [],
        }

    turning = max(play_results, key=lambda p: abs(float(_internal_play(p).get("expected_value_delta", 0.0))))
    cards_by_id = _graph_cards_by_id(graph)
    notes: List[str] = []
    tweaks: List[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    for play in play_results:
        for event in _observed_events(play):
            card_id = event.get("graph_card_id")
            if not card_id:
                continue
            pair = (str(card_id), str(event.get("tag", "")))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            card = cards_by_id.get(str(card_id))
            if not card:
                continue
            notes.append(film_room_note_for_event(event, card))
            tweaks.append(film_room_tweak_for_card(card))

    if not notes:
        notes.append("No high-leverage graph event dominated the drive; compare call sequencing and risk level across seeds.")
        tweaks.append("Review call sequencing, resource use, and risk level against nearby fixed seeds.")

    terminal_reason = _public_play(play_results[-1]).get("terminal_reason")

    return {
        "headline": headline_for_terminal(points, terminal_reason),
        "turning_point": {
            "play_index": _public_play(turning).get("play_index"),
            "expected_value_delta": _internal_play(turning).get("expected_value_delta"),
            "graph_card_ids": _public_play(turning).get("graph_card_ids", []),
            "metric": "largest_abs_expected_value_delta",
        },
        "notes": notes,
        "suggested_tweaks": tweaks,
    }
