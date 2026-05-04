from __future__ import annotations

from typing import Any, Dict, List

from .film_room import film_room_note_for_event
from .graph_loader import StrategyGraph


OFFENSE_ACTION_FIELDS = {
    "personnel_family",
    "formation_family",
    "motion_family",
    "concept_family",
    "protection_family",
    "risk_level",
    "constraint_tag",
}

DEFENSE_ACTION_FIELDS = {
    "personnel_family",
    "front_family",
    "coverage_family",
    "pressure_family",
    "disguise_family",
    "matchup_focus",
    "risk_level",
    "constraint_tag",
}

REPLAY_METADATA_FIELDS = {
    "episode_id",
    "seed_hash",
    "graph_version",
    "engine_version",
    "mode",
    "product_boundary",
    "start_yardline",
    "max_plays",
    "initial_down",
    "initial_distance",
    "score_mode",
    "drive_terminal_condition",
}

PUBLIC_PLAY_FIELDS = {
    "play_index",
    "offense_action",
    "defense_action",
    "yards_gained",
    "expected_value_delta",
    "success",
    "terminal",
    "terminal_reason",
    "events",
    "graph_card_ids",
    "next_state",
    "legal_action_set_id",
    "legal_action_sets",
    "resource_budget_snapshot",
    "validation_result",
}

OBSERVED_PLAY_FIELDS = {
    "play_index",
    "yards_gained",
    "success",
    "terminal",
    "terminal_reason",
    "events",
    "graph_card_ids",
    "next_state",
    "belief_after",
}

FILM_ROOM_FIELDS = {
    "headline",
    "turning_point",
    "notes",
    "suggested_tweaks",
}

TURNING_POINT_FIELDS = {
    "play_index",
    "expected_value_delta",
    "graph_card_ids",
    "metric",
}

HIDDEN_OBSERVATION_FIELDS = {
    "seed",
    "seed_hash",
    "offense_action",
    "defense_action",
    "engine_internal",
    "debug",
    "future_plays",
    "opponent_action",
}

NO_EVENT_FILM_ROOM_NOTE = "No high-leverage graph event dominated the drive; compare call sequencing and risk level across seeds."


class ContractValidationError(AssertionError):
    pass


def _require_fields(obj: Dict[str, Any], fields: set[str], label: str) -> None:
    missing = fields - set(obj)
    if missing:
        raise ContractValidationError(f"{label} missing fields: {sorted(missing)}")


def _all_events_from_play(play: Dict[str, Any]) -> List[Dict[str, Any]]:
    events_by_tag: Dict[str, Dict[str, Any]] = {}
    for key in ("public", "offense_observed", "defense_observed"):
        for event in play.get(key, {}).get("events", []):
            events_by_tag.setdefault(event["tag"], event)
    return list(events_by_tag.values())


def validate_action_schema(action: Dict[str, Any], side: str) -> None:
    if side == "offense":
        _require_fields(action, OFFENSE_ACTION_FIELDS, "offense_action")
    elif side == "defense":
        _require_fields(action, DEFENSE_ACTION_FIELDS, "defense_action")
    else:
        raise ContractValidationError(f"Unknown action side: {side}")

    if not isinstance(action.get("risk_level"), str) or not action["risk_level"]:
        raise ContractValidationError(f"{side} action risk_level must be a non-empty string")
    if not str(action.get("constraint_tag", "")).startswith("legal:"):
        raise ContractValidationError(f"{side} action constraint_tag must be legal-prefixed")


def validate_observation_safety(observation: Dict[str, Any], side: str) -> None:
    leaked = HIDDEN_OBSERVATION_FIELDS & set(observation)
    if leaked:
        raise ContractValidationError(f"{side} observation leaks hidden fields: {sorted(leaked)}")

    for event in observation.get("events", []):
        visible_to = set(event.get("visible_to", []))
        if side not in visible_to:
            raise ContractValidationError(f"{side} observation includes hidden event: {event.get('tag')}")


def validate_film_room_is_event_derived(replay: Dict[str, Any]) -> None:
    cards_by_id = {card["id"]: card for card in StrategyGraph().interactions}
    events = [
        event
        for play in replay.get("plays", [])
        for event in _all_events_from_play(play)
    ]
    event_tags = {event["tag"] for event in events}
    allowed_notes = {
        film_room_note_for_event(event, cards_by_id[event["graph_card_id"]])
        for event in events
        if event.get("graph_card_id") in cards_by_id
    }
    if not event_tags:
        allowed_notes.add(NO_EVENT_FILM_ROOM_NOTE)
    if event_tags and not allowed_notes:
        allowed_notes.add(NO_EVENT_FILM_ROOM_NOTE)

    for note in replay.get("film_room", {}).get("notes", []):
        if note not in allowed_notes:
            raise ContractValidationError(f"Film Room note is not event-derived: {note}")


def validate_film_room_schema(film_room: Dict[str, Any]) -> None:
    _require_fields(film_room, FILM_ROOM_FIELDS, "film_room")
    if not isinstance(film_room["notes"], list):
        raise ContractValidationError("film_room notes must be a list")
    if not isinstance(film_room["suggested_tweaks"], list):
        raise ContractValidationError("film_room suggested_tweaks must be a list")

    turning_point = film_room["turning_point"]
    if turning_point is not None:
        _require_fields(turning_point, TURNING_POINT_FIELDS, "film_room turning_point")
        if turning_point["metric"] != "largest_abs_expected_value_delta":
            raise ContractValidationError(f"Unknown turning-point metric: {turning_point['metric']}")


def validate_replay_contract(replay: Dict[str, Any]) -> None:
    _require_fields(replay, {"metadata", "agents", "legal_sets", "plays", "score", "film_room", "debug"}, "replay")
    _require_fields(replay["metadata"], REPLAY_METADATA_FIELDS, "metadata")
    if "seed" in replay["metadata"]:
        raise ContractValidationError("metadata must not expose raw seed")
    if replay["debug"] != {"fields": []}:
        raise ContractValidationError("P0 debug partition must be present and empty")
    validate_film_room_schema(replay["film_room"])

    _require_fields(replay["score"], {"points", "result", "invalid_action_count"}, "score")
    if replay["score"]["result"] not in {"touchdown", "field_goal", "stopped"}:
        raise ContractValidationError(f"Unknown score result: {replay['score']['result']}")

    for index, play in enumerate(replay["plays"], start=1):
        _require_fields(play, {"public", "offense_observed", "defense_observed", "engine_internal"}, f"play {index}")
        _require_fields(play["public"], PUBLIC_PLAY_FIELDS, f"play {index} public")
        _require_fields(play["offense_observed"], OBSERVED_PLAY_FIELDS, f"play {index} offense_observed")
        _require_fields(play["defense_observed"], OBSERVED_PLAY_FIELDS, f"play {index} defense_observed")

        validate_action_schema(play["public"]["offense_action"], "offense")
        validate_action_schema(play["public"]["defense_action"], "defense")
        validate_observation_safety(play["offense_observed"], "offense")
        validate_observation_safety(play["defense_observed"], "defense")

        if "belief_after" in play["public"]:
            raise ContractValidationError("public play must not include side belief state")

    validate_film_room_is_event_derived(replay)


def validate_match_matrix_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "seed_start", "cases"}, "match matrix report")
    for case in report["cases"]:
        _require_fields(
            case,
            {"case", "seed", "points", "result", "plays", "film_room_headline", "turning_point"},
            "match matrix case",
        )


def validate_daily_slate_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"slate_id", "results", "summary"}, "daily slate report")
    _require_fields(report["summary"], {"total_points", "average_points"}, "daily slate summary")
    for result in report["results"]:
        _require_fields(result, {"seed_hash", "matchup", "points", "result", "plays", "film_room"}, "daily slate result")
