from __future__ import annotations

import re
from typing import Any, Dict, List

from .graph_loader import StrategyGraph
from .labels import card_label, concept_label, is_legal_concept

NO_EVENT_FILM_ROOM_NOTE = "No high-leverage graph event dominated the drive; compare call sequencing and risk level across seeds."
NO_EVENT_FILM_ROOM_TWEAK = "Review call sequencing, resource use, and risk level against nearby fixed seeds."
NARRATIVE_MAX_CHARS = 200

TWEAK_PARAMETERS = {
    "risk_tolerance",
    "adaptation_speed",
    "screen_trigger_confidence",
    "explosive_shot_tolerance",
    "run_pass_tendency",
    "disguise_sensitivity",
    "pressure_frequency",
    "counter_repeat_tolerance",
}
TWEAK_DIRECTIONS = {"increase", "decrease", "set"}
TWEAK_MAGNITUDES = {"small", "medium", "large"}
TWEAK_SIGNALS = {
    "play_distribution",
    "belief_trajectory",
    "resource_burn",
    "graph_event_frequency",
    "drive_outcome",
}
TWEAK_TEMPLATE_IDS = {
    "belief_event_crossed_threshold",
    "event_count_crossed_threshold",
    "resource_burn_crossed_threshold",
    "play_mix_crossed_threshold",
    "drive_outcome_after_event",
}

CARD_TWEAK_RULES: Dict[str, Dict[str, Any]] = {
    "redzone.bunch_mesh_vs_match.v1": {
        "parameter": "counter_repeat_tolerance",
        "direction": "decrease",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.screen_vs_zero_pressure.v1": {
        "parameter": "pressure_frequency",
        "direction": "decrease",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.screen_vs_simulated_pressure.v1": {
        "parameter": "screen_trigger_confidence",
        "direction": "increase",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.outside_zone_vs_bear.v1": {
        "parameter": "adaptation_speed",
        "direction": "increase",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.play_action_after_run_tendency.v1": {
        "parameter": "counter_repeat_tolerance",
        "direction": "decrease",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.vertical_vs_two_high.v1": {
        "parameter": "explosive_shot_tolerance",
        "direction": "decrease",
        "magnitude": "medium",
        "signal": "graph_event_frequency",
    },
    "redzone.quick_game_vs_two_high.v1": {
        "parameter": "risk_tolerance",
        "direction": "increase",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
    "redzone.rpo_vs_static_zone.v1": {
        "parameter": "disguise_sensitivity",
        "direction": "increase",
        "magnitude": "small",
        "signal": "graph_event_frequency",
    },
}


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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _plays_text(play_indices: List[int]) -> str:
    if len(play_indices) == 1:
        return f"Play {play_indices[0]}"
    if len(play_indices) == 2:
        return f"Plays {play_indices[0]} and {play_indices[1]}"
    return f"Plays {', '.join(str(index) for index in play_indices[:-1])}, and {play_indices[-1]}"


def _count_text(count: int) -> str:
    if count == 1:
        return "once"
    if count == 2:
        return "twice"
    return f"{count} times"


def render_tweak_rationale(template_id: str, arguments: Dict[str, Any]) -> str:
    play_indices = [int(index) for index in arguments.get("play_indices", [])]
    play_text = _plays_text(play_indices)
    event_tag = str(arguments.get("event_tag", "event"))
    parameter = str(arguments.get("parameter", "parameter"))
    direction = str(arguments.get("direction", "adjust"))
    observed = arguments.get("observed_value", {})
    threshold = arguments.get("threshold", {})

    if template_id == "belief_event_crossed_threshold":
        belief = observed.get("belief", "belief") if isinstance(observed, dict) else "belief"
        value = observed.get("value", observed) if isinstance(observed, dict) else observed
        return f"{play_text} produced {event_tag} and {belief} reached {value}, so {direction} {parameter}."
    if template_id == "resource_burn_crossed_threshold":
        resource = observed.get("resource", "resource") if isinstance(observed, dict) else "resource"
        spent = observed.get("spent", observed) if isinstance(observed, dict) else observed
        call = observed.get("call", event_tag) if isinstance(observed, dict) else event_tag
        return f"{play_text} spent {spent} {resource} on {call}, so {direction} {parameter}."
    if template_id == "play_mix_crossed_threshold":
        mix = observed.get("mix", observed) if isinstance(observed, dict) else observed
        gate = threshold.get("mix", threshold) if isinstance(threshold, dict) else threshold
        return f"{play_text} reached {mix} against mix gate {gate}, so {direction} {parameter}."
    if template_id == "drive_outcome_after_event":
        outcome = observed.get("outcome", observed) if isinstance(observed, dict) else observed
        return f"{play_text} produced {event_tag} before {outcome}, so {direction} {parameter}."

    count = observed.get("count", len(play_indices)) if isinstance(observed, dict) else len(play_indices)
    return f"{play_text} produced {event_tag} {_count_text(int(count))}, so {direction} {parameter}."


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


def structured_tweak_for_card_record(record: Dict[str, Any]) -> Dict[str, Any] | None:
    card = record["card"]
    card_id = str(card["id"])
    rule = CARD_TWEAK_RULES.get(card_id)
    if not rule:
        return None

    event_play_indices_by_tag = record.get("event_play_indices_by_tag", {})
    if not event_play_indices_by_tag:
        return None
    event_tag = next(iter(event_play_indices_by_tag))
    play_indices = sorted({int(index) for index in event_play_indices_by_tag[event_tag]})
    if not play_indices:
        return None

    observed_value: Dict[str, Any] = {
        "event_tag": event_tag,
        "count": len(play_indices),
    }
    offense_calls = record.get("offense_calls", [])
    defense_calls = record.get("defense_calls", [])
    if offense_calls:
        observed_value["offense_call"] = offense_calls[0]
    if defense_calls:
        observed_value["defense_call"] = defense_calls[0]

    threshold = {"event_count": 1}
    arguments = {
        "play_indices": play_indices,
        "signal": rule["signal"],
        "event_tag": event_tag,
        "graph_card_id": card_id,
        "observed_value": observed_value,
        "threshold": threshold,
        "parameter": rule["parameter"],
        "direction": rule["direction"],
    }
    template_id = "event_count_crossed_threshold"
    tweak = {
        "tweak_id": f"twk_{_slug(rule['parameter'])}_{_slug(event_tag)}_{play_indices[0]:03d}",
        "parameter": rule["parameter"],
        "direction": rule["direction"],
        "magnitude": rule["magnitude"],
        "evidence": {
            "signal": rule["signal"],
            "observed_value": observed_value,
            "threshold": threshold,
            "play_indices": play_indices,
        },
        "source": {
            "graph_card_id": card_id,
        },
        "rationale": {
            "template_id": template_id,
            "arguments": arguments,
            "rendered": render_tweak_rationale(template_id, arguments),
        },
    }
    if "target_value" in rule:
        tweak["target_value"] = rule["target_value"]
    return tweak


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


def _outcome_phrase(points: int | None, terminal_reason: str | None) -> str:
    if terminal_reason == "touchdown" or (points is not None and points >= 7):
        return f"scored {points} points" if points is not None else "scored"
    if terminal_reason == "turnover":
        return "the defense forced a turnover"
    if terminal_reason == "turnover_on_downs":
        return "the defense held on downs"
    if terminal_reason == "max_plays_reached":
        return "the drive stalled out of plays" if not points else "the drive ended with field position"
    if points == 3:
        return "the drive ended with field position"
    return "the drive stopped"


def _terminal_points(plays: List[Dict[str, Any]]) -> int | None:
    if not plays:
        return None
    next_state = _public_play(plays[-1]).get("next_state", {})
    points = next_state.get("points") if isinstance(next_state, dict) else None
    return int(points) if isinstance(points, int) else None


def _fit_narrative(sentences: List[str]) -> str | None:
    text = "".join(sentences)
    if len(text) <= NARRATIVE_MAX_CHARS:
        return text
    if sentences and len(sentences[0]) <= NARRATIVE_MAX_CHARS:
        return sentences[0]
    return None


def _event_candidates(plays: List[Dict[str, Any]], graph: StrategyGraph | None) -> List[Dict[str, Any]]:
    cards_by_id = _graph_cards_by_id(graph)
    candidates: List[Dict[str, Any]] = []
    for fallback_index, play in enumerate(plays, start=1):
        public = _public_play(play)
        play_index = int(public.get("play_index", fallback_index))
        offense_call = public.get("offense_action", {}).get("concept_family")
        defense_call = public.get("defense_action", {}).get("coverage_family")
        if not offense_call or not defense_call:
            continue
        for event in _observed_events(play):
            card_id = event.get("graph_card_id")
            if not card_id or str(card_id) not in cards_by_id:
                continue
            candidates.append({
                "card_id": str(card_id),
                "play_index": play_index,
                "max_abs_ep": abs(float(public.get("expected_value_delta", 0.0))),
                "offense_call": str(offense_call),
                "defense_call": str(defense_call),
            })
    return candidates


def _adaptation_candidate(card_id: str, play_index: int, candidates: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    for candidate in candidates:
        if candidate["card_id"] == card_id and candidate["play_index"] == play_index:
            return candidate
    return None


def narrative_for_drive(
    film_room_data: Dict[str, Any],
    plays: List[Dict[str, Any]],
    graph: StrategyGraph | None = None,
) -> str | None:
    if not plays:
        return None
    if film_room_data.get("notes") == [NO_EVENT_FILM_ROOM_NOTE]:
        return None

    candidates = _event_candidates(plays, graph)
    if not candidates:
        return None

    primary = sorted(candidates, key=lambda item: (-float(item["max_abs_ep"]), int(item["play_index"]), item["card_id"]))[0]
    points = film_room_data.get("points")
    points = int(points) if isinstance(points, int) else _terminal_points(plays)
    terminal_reason = _public_play(plays[-1]).get("terminal_reason")
    outcome = _outcome_phrase(points, terminal_reason)

    first = (
        f"You attacked {card_label(primary['card_id'], graph)} with "
        f"{concept_label(primary['offense_call'], graph)} against {concept_label(primary['defense_call'], graph)}."
    )

    second_candidate: Dict[str, Any] | None = None
    adaptation_chain = sorted(
        [entry for entry in film_room_data.get("adaptation_chain", []) if entry.get("graph_card_id")],
        key=lambda entry: int(entry.get("play_index") or 0),
    )
    for entry in adaptation_chain:
        candidate = _adaptation_candidate(str(entry["graph_card_id"]), int(entry.get("play_index") or 0), candidates)
        if candidate and (candidate["play_index"] > primary["play_index"] or candidate["card_id"] != primary["card_id"]):
            second_candidate = candidate
            break
    if second_candidate is None:
        for candidate in sorted(candidates, key=lambda item: (int(item["play_index"]), item["card_id"])):
            if candidate["play_index"] > primary["play_index"] or candidate["card_id"] != primary["card_id"]:
                second_candidate = candidate
                break

    if second_candidate:
        second = f" The offense adjusted to {concept_label(second_candidate['offense_call'], graph)}, then {outcome}."
    else:
        second = f" The drive {outcome}."
    return _fit_narrative([first, second])


def build_film_room(play_results: List[Dict[str, Any]], points: int, graph: StrategyGraph | None = None) -> Dict[str, Any]:
    if not play_results:
        return {
            "headline": "No plays were resolved.",
            "narrative": None,
            "turning_point": None,
            "notes": [],
            "suggested_tweaks": [],
            "film_room_tweaks": [],
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
                    "event_tags": [],
                    "event_play_indices_by_tag": {},
                    "offense_calls": [],
                    "defense_calls": [],
                }
                record = card_records[str(card_id)]
            else:
                record["max_abs_ep"] = max(float(record["max_abs_ep"]), expected_value)

            public = _public_play(play)
            public_play_index = int(public.get("play_index", play_index + 1))
            event_tag = str(event.get("tag", ""))
            if event_tag:
                if event_tag not in record["event_tags"]:
                    record["event_tags"].append(event_tag)
                event_play_indices = record["event_play_indices_by_tag"].setdefault(event_tag, [])
                if public_play_index not in event_play_indices:
                    event_play_indices.append(public_play_index)
            offense_call = public.get("offense_action", {}).get("concept_family")
            defense_call = public.get("defense_action", {}).get("coverage_family")
            if offense_call and offense_call not in record["offense_calls"]:
                record["offense_calls"].append(offense_call)
            if defense_call and defense_call not in record["defense_calls"]:
                record["defense_calls"].append(defense_call)
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
        structured_tweak = structured_tweak_for_card_record(record)
        tweak_records.append({
            "card_id": card_id,
            "tweak": tweak,
            "structured_tweak": structured_tweak,
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
    structured_tweaks = [item["structured_tweak"] for item in tweak_records if item["structured_tweak"] is not None]
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
    film_room_data = {
        "headline": headline_for_terminal(points, terminal_reason),
        "points": points,
        "turning_point": {
            "play_index": _public_play(turning).get("play_index"),
            "expected_value_delta": _internal_play(turning).get("expected_value_delta"),
            "graph_card_ids": _public_play(turning).get("graph_card_ids", []),
            "metric": "largest_abs_expected_value_delta",
        },
        "notes": notes,
        "suggested_tweaks": tweaks,
        "film_room_tweaks": structured_tweaks,
        "adaptation_chain": adaptation_chain,
        "next_adjustment": next_adjustment,
    }
    narrative = narrative_for_drive(film_room_data, play_results, graph)
    return {
        "headline": film_room_data["headline"],
        "narrative": narrative,
        "turning_point": film_room_data["turning_point"],
        "notes": notes,
        "suggested_tweaks": tweaks,
        "film_room_tweaks": structured_tweaks,
        "adaptation_chain": adaptation_chain,
        "next_adjustment": next_adjustment,
    }
