from __future__ import annotations

from typing import Any, Dict, List

from .film_room import (
    NO_EVENT_FILM_ROOM_NOTE,
    NO_EVENT_FILM_ROOM_TWEAK,
    film_room_note_for_event,
    film_room_tweak_for_card,
)
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

PUBLIC_OBSERVATION_FIELDS = {
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
}

OBSERVATION_ALLOWED_FIELDS = {
    "offense": {
        "pre_play": {
            "side",
            "game_state",
            "legal_concepts",
            "own_resource_remaining",
        },
        "post_play": OBSERVED_PLAY_FIELDS,
    },
    "defense": {
        "pre_play": {
            "side",
            "game_state",
            "legal_calls",
            "own_resource_remaining",
        },
        "post_play": OBSERVED_PLAY_FIELDS,
    },
    "public": {
        "post_play": PUBLIC_OBSERVATION_FIELDS,
    },
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
    "hidden_traits",
    "scouting_noise_seed",
    "true_traits",
}

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
    allowed_tweaks = {
        film_room_tweak_for_card(cards_by_id[event["graph_card_id"]])
        for event in events
        if event.get("graph_card_id") in cards_by_id
    }
    if not event_tags:
        allowed_notes.add(NO_EVENT_FILM_ROOM_NOTE)
        allowed_tweaks.add(NO_EVENT_FILM_ROOM_TWEAK)
    if event_tags and not allowed_notes:
        allowed_notes.add(NO_EVENT_FILM_ROOM_NOTE)
        allowed_tweaks.add(NO_EVENT_FILM_ROOM_TWEAK)

    for note in replay.get("film_room", {}).get("notes", []):
        if note not in allowed_notes:
            raise ContractValidationError(f"Film Room note is not event-derived: {note}")
    for tweak in replay.get("film_room", {}).get("suggested_tweaks", []):
        if tweak not in allowed_tweaks:
            raise ContractValidationError(f"Film Room tweak is not graph-derived: {tweak}")


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
    if "inference_report" in replay:
        validate_inference_report(replay["inference_report"])


def validate_match_matrix_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "seed_start", "cases", "questions"}, "match matrix report")
    for case in report["cases"]:
        _require_fields(
            case,
            {"case", "seed", "points", "result", "plays", "film_room_headline", "turning_point"},
            "match matrix case",
        )
    required_question_ids = {
        "adaptive_offense_lift_vs_same_defense",
        "adaptive_defense_suppression_vs_same_offense",
        "adaptive_vs_adaptive_nontrivial_sequencing",
        "obvious_exploits_or_degenerate_strategies",
    }
    seen_question_ids = set()
    for question in report["questions"]:
        _require_fields(
            question,
            {
                "id",
                "question",
                "baseline_case",
                "comparison_case",
                "metric",
                "baseline_value",
                "comparison_value",
                "answer",
            },
            "match matrix question",
        )
        seen_question_ids.add(question["id"])
        if question["answer"] not in {"yes", "no", "needs_review"}:
            raise ContractValidationError(f"Unknown match matrix question answer: {question['answer']}")
    missing = required_question_ids - seen_question_ids
    if missing:
        raise ContractValidationError(f"match matrix report missing PLAN 9.3 questions: {sorted(missing)}")


def validate_daily_slate_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"slate_id", "results", "summary"}, "daily slate report")
    _require_fields(
        report["summary"],
        {"total_points", "average_points", "touchdown_rate", "field_goal_rate", "stopped_rate", "mean_plays_per_drive"},
        "daily slate summary",
    )
    for result in report["results"]:
        _require_fields(
            result,
            {"seed", "seed_hash", "matchup", "offense_label", "defense_label", "points", "result", "plays", "replay_path", "film_room"},
            "daily slate result",
        )


def validate_best_of_n_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "team_a", "team_b", "seeds", "drives"}, "best-of-N report")
    for team_key in ("team_a", "team_b"):
        _require_fields(
            report[team_key],
            {
                "team_id",
                "label",
                "games_played",
                "total_points",
                "mean_points_per_drive",
                "touchdown_rate",
                "field_goal_rate",
                "stopped_rate",
                "mean_plays_per_drive",
                "invalid_action_count_total",
            },
            f"best-of-N {team_key}",
        )
    for drive in report["drives"]:
        _require_fields(
            drive,
            {"seed", "direction", "points", "result", "plays", "film_room_headline"},
            "best-of-N drive",
        )


def validate_tournament_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "teams", "seeds", "standings", "raw_drives"}, "tournament report")
    for team in report["teams"]:
        _require_fields(team, {"team_id", "label"}, "tournament team")
    for row in report["standings"]:
        _require_fields(
            row,
            {
                "rank",
                "team_id",
                "label",
                "games_played",
                "mean_points_per_drive",
                "touchdown_rate",
                "head_to_head",
            },
            "tournament standing",
        )
    for drive in report["raw_drives"]:
        _require_fields(
            drive,
            {"seed", "team_id", "opponent_team_id", "direction", "points", "result", "plays"},
            "tournament raw drive",
        )


def validate_roster_budget(payload: Dict[str, Any]) -> None:
    _require_fields(payload, {"roster_id", "label", "budget_points", "position_groups", "notes"}, "roster budget")
    expected_traits = {
        "qb": "decision_making",
        "running_backs": "run_power",
        "receivers": "separation",
        "offensive_line": "protection",
        "front_seven": "rush_pressure",
        "secondary": "coverage_tightness",
    }
    groups = payload["position_groups"]
    extra = set(groups) - set(expected_traits)
    missing = set(expected_traits) - set(groups)
    if extra or missing:
        raise ContractValidationError(f"roster budget groups invalid; missing={sorted(missing)} extra={sorted(extra)}")
    total = 0
    for group, trait in expected_traits.items():
        item = groups[group]
        _require_fields(item, {"trait", "value"}, f"roster budget {group}")
        if item["trait"] != trait:
            raise ContractValidationError(f"roster budget {group} trait must be {trait}")
        if not isinstance(item["value"], int) or not 0 <= item["value"] <= 100:
            raise ContractValidationError(f"roster budget {group} value must be an integer in [0, 100]")
        total += item["value"]
    if total != payload["budget_points"]:
        raise ContractValidationError(f"roster budget total {total} does not equal budget_points {payload['budget_points']}")


def validate_mirrored_seed_report(report: Dict[str, Any]) -> None:
    _require_fields(
        report,
        {"report_id", "team_a", "team_b", "offense_roster", "defense_roster", "seeds", "drives", "roster_lift_offense", "notes"},
        "mirrored seed report",
    )
    for drive in report["drives"]:
        _require_fields(drive, {"seed", "direction", "points", "result", "plays", "film_room_headline"}, "mirrored seed drive")


def validate_budget_leaderboard_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "entries", "seeds", "standings", "raw_drives"}, "budget leaderboard report")
    for entry in report["entries"]:
        _require_fields(
            entry,
            {"entry_id", "team_id", "roster_id", "label", "budget_points", "games_played", "total_points", "mean_points_per_drive"},
            "budget leaderboard entry",
        )
    for row in report["standings"]:
        _require_fields(row, {"rank", "entry_id", "mean_points_per_drive", "total_points"}, "budget leaderboard standing")
    for drive in report["raw_drives"]:
        _require_fields(drive, {"seed", "entry_id", "opponent_entry_id", "direction", "points", "result", "plays"}, "budget leaderboard drive")


def validate_matchup_traits(payload: Dict[str, Any]) -> None:
    _require_fields(payload, {"matchup_id", "label", "values", "notes"}, "matchup traits")
    allowed = {
        "offense_explosive_propensity",
        "offense_screen_self_belief",
        "offense_run_commitment",
        "defense_disguise_quality",
        "defense_pressure_discipline",
        "defense_redzone_density",
        "matchup_volatility",
    }
    found = set(payload["values"])
    if found != allowed:
        raise ContractValidationError(f"matchup traits invalid; missing={sorted(allowed - found)} extra={sorted(found - allowed)}")
    for key, value in payload["values"].items():
        if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
            raise ContractValidationError(f"matchup trait {key} must be in [0, 1]")


def validate_scouting_report(payload: Dict[str, Any]) -> None:
    _require_fields(payload, {"report_id", "label", "freshness", "completeness", "estimated_traits", "confidence", "notes"}, "scouting report")
    if payload["freshness"] not in {"fresh", "stale"}:
        raise ContractValidationError("scouting report freshness must be fresh or stale")
    if not isinstance(payload["completeness"], (int, float)) or not 0.0 <= float(payload["completeness"]) <= 1.0:
        raise ContractValidationError("scouting report completeness must be in [0, 1]")
    allowed = {
        "offense_explosive_propensity",
        "offense_screen_self_belief",
        "offense_run_commitment",
        "defense_disguise_quality",
        "defense_pressure_discipline",
        "defense_redzone_density",
        "matchup_volatility",
    }
    if set(payload["estimated_traits"]) != allowed:
        raise ContractValidationError("scouting report estimated traits must match allowed traits")
    if set(payload["confidence"]) != allowed:
        raise ContractValidationError("scouting report confidence must match allowed traits")
    for key, value in payload["estimated_traits"].items():
        if value is not None and (not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0):
            raise ContractValidationError(f"scouting estimate {key} must be in [0, 1] or null")
        if payload["confidence"][key] not in {"low", "medium", "high"}:
            raise ContractValidationError(f"scouting confidence {key} is invalid")


def validate_inference_report(report: Dict[str, Any]) -> None:
    _require_fields(
        report,
        {"report_id", "matchup_id", "offense_calibration", "defense_calibration", "scouting_used", "notes"},
        "inference report",
    )
    for side in ("offense_calibration", "defense_calibration"):
        _require_fields(report[side], {"per_trait_error", "mean_absolute_error", "calibrated_traits"}, f"inference {side}")


def validate_calibration_eval_report(report: Dict[str, Any]) -> None:
    _require_fields(
        report,
        {"report_id", "team_a", "team_b", "matchup_traits", "scouting", "seeds", "with_scouting", "without_scouting", "scouting_mae_lift"},
        "calibration eval report",
    )
    for key in ("with_scouting", "without_scouting"):
        _require_fields(
            report[key],
            {"offense_mae", "defense_mae", "per_trait_offense_mae", "per_trait_defense_mae"},
            f"calibration eval {key}",
        )
    _require_fields(report["scouting_mae_lift"], {"offense", "defense"}, "calibration eval scouting_mae_lift")


def validate_qualification_report(report: Dict[str, Any]) -> None:
    _require_fields(
        report,
        {"qualification_id", "agent_path", "side", "submitted_at", "static_validation", "gauntlet", "passed", "reasons"},
        "qualification report",
    )
    _require_fields(report["static_validation"], {"errors", "warnings"}, "qualification static_validation")


def validate_challenge_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"challenge_id", "agent_id", "opponent_kind", "seeds", "summary", "replay_paths"}, "challenge report")
    _require_fields(report["summary"], {"games_played", "mean_points_per_drive", "touchdown_rate"}, "challenge summary")


def validate_leaderboard_snapshot(report: Dict[str, Any]) -> None:
    _require_fields(report, {"season_id", "seed_set_hash", "standings"}, "leaderboard snapshot")
    for row in report["standings"]:
        _require_fields(row, {"agent_id", "label", "games_played", "mean_points_per_drive", "touchdown_rate"}, "leaderboard row")


def validate_comparison_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"report_id", "team_a", "team_b", "seeds", "cases", "answers", "metrics"}, "comparison report")
    _require_fields(report["team_a"], {"team_id", "label"}, "comparison team_a")
    _require_fields(report["team_b"], {"team_id", "label"}, "comparison team_b")
    for case in report["cases"]:
        _require_fields(case, {"case", "mean_points", "mean_plays"}, "comparison case")
    _require_fields(
        report["answers"],
        {
            "adaptive_offense_outperforms_static_offense",
            "adaptive_defense_suppresses_static_offense",
            "adaptive_vs_adaptive_has_nontrivial_sequencing",
            "graph_creates_no_obvious_degeneracies",
        },
        "comparison answers",
    )
    _require_fields(
        report["metrics"],
        {
            "adaptation_lift_offense",
            "suppression_lift_defense",
            "sequencing_diversity_b_vs_b",
            "degenerate_strategy_flags",
        },
        "comparison metrics",
    )


def validate_calibration_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"seeds", "matchup", "ranges"}, "calibration report")
    _require_fields(report["matchup"], {"offense", "defense"}, "calibration matchup")
    for metric in (
        "mean_points_per_drive",
        "touchdown_rate",
        "field_goal_rate",
        "turnover_rate",
        "mean_plays_per_drive",
        "invalid_action_rate",
    ):
        _require_fields(report["ranges"].get(metric, {}), {"min", "max"}, f"calibration range {metric}")


def validate_tier_config(payload: Dict[str, Any]) -> None:
    _require_fields(payload, {"agent_name", "side", "access_tier"}, "tier config")
    if payload["access_tier"] not in {"declarative", "prompt_policy", "remote_endpoint"}:
        raise ContractValidationError("tier config access_tier must be declarative, prompt_policy, or remote_endpoint")
    if payload["side"] not in {"offense", "defense"}:
        raise ContractValidationError("tier config side must be offense or defense")
    if payload["access_tier"] == "declarative":
        _require_fields(payload, {"preferred_concepts", "constraints"}, "tier0 config")
    if payload["access_tier"] == "prompt_policy":
        _require_fields(payload, {"strategy_prompt", "constraints", "rules"}, "tier1 config")
        if payload["constraints"].get("require_legal_action") is not True:
            raise ContractValidationError("tier1 config must require legal actions")


def validate_remote_endpoint_response(payload: Dict[str, Any], legal_actions: list[str] | None = None) -> None:
    _require_fields(payload, {"action"}, "remote endpoint response")
    if not isinstance(payload["action"], str) or not payload["action"]:
        raise ContractValidationError("remote endpoint action must be a non-empty string")
    if legal_actions is not None and payload["action"] not in legal_actions:
        raise ContractValidationError("remote endpoint action must be in legal_actions")
    rationale = payload.get("rationale")
    if rationale is not None and (not isinstance(rationale, str) or len(rationale) > 280):
        raise ContractValidationError("remote endpoint rationale must be <= 280 chars")


def validate_tier_challenge_report(report: Dict[str, Any]) -> None:
    _require_fields(report, {"challenge_id", "agent_id", "access_tier", "league", "seeds", "summary", "replay_paths"}, "tier challenge report")
    if report["access_tier"] not in {"declarative", "prompt_policy", "remote_endpoint", "sandboxed_code"}:
        raise ContractValidationError("tier challenge report has unknown access_tier")
    _require_fields(report["summary"], {"games_played", "mean_points_per_drive", "touchdown_rate"}, "tier challenge summary")
