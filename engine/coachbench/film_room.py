from __future__ import annotations

from typing import Any, Dict, List

from .graph_loader import StrategyGraph
from .labels import card_label, concept_label, is_legal_concept

NO_EVENT_FILM_ROOM_NOTE = "No high-leverage graph event dominated the drive; compare call sequencing and risk level across seeds."
NO_EVENT_FILM_ROOM_TWEAK = "Review call sequencing, resource use, and risk level against nearby fixed seeds."


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


def _humanize(value: str) -> str:
    return " ".join(part for part in value.replace("_", " ").split()).title()


def _belief_shift(play: Dict[str, Any], prior: Dict[str, Any] | None) -> Dict[str, float]:
    if prior is None:
        return {}
    current = play.get("offense_observed", {}).get("belief_after", {})
    previous = prior.get("offense_observed", {}).get("belief_after", {})
    shift: Dict[str, float] = {}
    for key, raw in current.items():
        if key not in previous:
            continue
        delta = round(float(raw) - float(previous[key]), 4)
        if abs(delta) >= 0.05:
            shift[key] = delta
    return shift


def film_room_note_for_event(
    event: Dict[str, Any],
    card: Dict[str, Any],
    *,
    label_fn=card_label,
) -> str:
    limitations = card.get("limitations", [])
    limitation_text = f" Limitation: {limitations[0]}" if limitations else ""
    resolved_label = label_fn(card["id"])
    event_label = _humanize(str(event.get("tag", "")))
    return (
        f"{resolved_label} ({event_label}) - see {resolved_label}."
        f"{limitation_text}"
    )


def film_room_tweak_for_card(
    card: Dict[str, Any],
    *,
    legal_concept_label_fn=concept_label,
    is_legal_fn=is_legal_concept,
) -> str | None:
    counters = [counter for counter in card.get("counters", []) if is_legal_fn(counter)]
    if counters:
        counter_labels = [legal_concept_label_fn(counter) for counter in sorted(set(counters))]
        return f"Try {', '.join(counter_labels)} against {card_label(card['id'])}."
    return None


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
            "adaptation_chain": [],
            "next_adjustment": "Next try: review call sequencing across nearby seeds.",
        }

    turning = max(play_results, key=lambda p: abs(float(_internal_play(p).get("expected_value_delta", 0.0))))
    cards_by_id = _graph_cards_by_id(graph)
    notes: List[str] = []
    seen_card_tag_pairs: set[tuple[str, str]] = set()
    card_records: Dict[str, Dict[str, Any]] = {}
    adaptation_candidates: List[tuple[float, Dict[str, Any]]] = []

    for play_index, play in enumerate(play_results):
        for event in _observed_events(play):
            card_id = event.get("graph_card_id")
            if not card_id:
                continue
            pair = (str(card_id), str(event.get("tag", "")))
            if pair not in seen_card_tag_pairs:
                seen_card_tag_pairs.add(pair)
                card = cards_by_id.get(str(card_id))
                if card:
                    notes.append(film_room_note_for_event(event, card))
            card = cards_by_id.get(str(card_id))
            if not card:
                continue
            expected_value = abs(float(_internal_play(play).get("expected_value_delta", 0.0)))
            record = card_records.get(str(card_id))
            if record is None:
                card_records[str(card_id)] = {
                    "card": card,
                    "first_play_index": int(_public_play(play).get("play_index", play_index + 1)),
                    "max_abs_ep": expected_value,
                }
            else:
                record["max_abs_ep"] = max(float(record["max_abs_ep"]), expected_value)

            public = _public_play(play)
            resource_snapshot = public.get("resource_budget_snapshot", {})
            entry = {
                "play_index": public.get("play_index"),
                "trigger_event": _humanize(str(event.get("tag", ""))),
                "graph_card_id": str(card_id),
                "card_label": card_label(str(card_id)),
                "offense_call": concept_label(public.get("offense_action", {}).get("concept_family", "")),
                "defense_call": concept_label(public.get("defense_action", {}).get("coverage_family", "")),
                "belief_shift": _belief_shift(play, play_results[play_index - 1] if play_index > 0 else None),
                "resource_remaining": dict(resource_snapshot.get("offense_remaining", {})),
            }
            adaptation_candidates.append((expected_value, entry))

    tweak_records: List[Dict[str, Any]] = []
    for card_id, record in card_records.items():
        tweak = film_room_tweak_for_card(record["card"])
        if tweak is None:
            continue
        tweak_records.append({
            "card_id": card_id,
            "tweak": tweak,
            "first_play_index": record["first_play_index"],
            "max_abs_ep": record["max_abs_ep"],
            "card": record["card"],
        })
    if len(tweak_records) > 4:
        kept_card_ids = {
            item["card_id"]
            for item in sorted(tweak_records, key=lambda item: (-float(item["max_abs_ep"]), int(item["first_play_index"])))[:4]
        }
        tweak_records = [item for item in tweak_records if item["card_id"] in kept_card_ids]
    tweak_records.sort(key=lambda item: int(item["first_play_index"]))
    tweaks = [item["tweak"] for item in tweak_records]
    if not notes:
        notes.append(NO_EVENT_FILM_ROOM_NOTE)
        tweaks.append(NO_EVENT_FILM_ROOM_TWEAK)

    if len(adaptation_candidates) > 6:
        kept_entries = {
            id(entry)
            for _, entry in sorted(adaptation_candidates, key=lambda item: -item[0])[:6]
        }
        adaptation_chain = [entry for _, entry in adaptation_candidates if id(entry) in kept_entries]
    else:
        adaptation_chain = [entry for _, entry in adaptation_candidates]
    adaptation_chain.sort(key=lambda entry: int(entry.get("play_index") or 0))

    next_adjustment = "Next try: review call sequencing across nearby seeds."
    if tweak_records:
        first_card = tweak_records[0]["card"]
        legal_counters = [counter for counter in first_card.get("counters", []) if is_legal_concept(counter)]
        if legal_counters:
            next_adjustment = f"Next try: {concept_label(legal_counters[0])} to counter {card_label(first_card['id'])}."

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
        "adaptation_chain": adaptation_chain,
        "next_adjustment": next_adjustment,
    }
