from __future__ import annotations

from copy import deepcopy
from typing import Any
import re

from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS
from coachbench.film_room import film_room_note_for_event
from coachbench.graph_loader import StrategyGraph
from coachbench.identities import get_identity, identity_to_dict

from arena.assistant.proposal import (
    DEFENSE_PARAMETERS,
    OFFENSE_PARAMETERS,
    REQUIRED_CHANGE_KEYS,
    REQUIRED_EVIDENCE_KEYS,
    REQUIRED_PROPOSAL_KEYS,
    _all_concepts,
    _graph_card_ids,
    _identity_ids,
    load_parameter_glossary,
    parameter_specs,
)
from arena.assistant.templates import propose_from_prompt


DENIED_KEY_RE = re.compile(r"^(seed.*|secret.*|api_key.*|admin.*|debug.*|.*_internal)$", re.IGNORECASE)
DENIED_TEXT_RE = re.compile(r"\b(seed|secret|api_key|admin|debug|tier 0|tier 1|tier 2)\b", re.IGNORECASE)
EXPLICIT_DENY_KEYS = set(HIDDEN_OBSERVATION_FIELDS) | {"session_id", "ip", "current_draft_id"}
SAFE_REPLAY_PLAY_FIELDS = {
    "play_index",
    "concept",
    "counter",
    "outcome",
    "success_flag",
    "validation_ok",
    "graph_card_ids",
    "film_room_event_id",
    "film_room_events",
}
CANONICAL_PROMPTS = (
    "Build an offense that punishes pressure without throwing picks.",
    "Make my defense disguise more without burning the rush budget.",
    "We got baited by simulated pressure. What should I change?",
    "Build a run-first coordinator that unlocks play-action.",
    "Give me a safe red-zone defense that prevents explosives.",
)


def _target_side(server_context: dict[str, Any], prompt: str) -> str | None:
    draft = server_context.get("current_draft")
    config = draft.get("config_json") if isinstance(draft, dict) else None
    if isinstance(config, dict) and config.get("side") in {"offense", "defense"}:
        return config["side"]
    lowered = prompt.lower()
    if "defense" in lowered or "disguise" in lowered or "rush budget" in lowered:
        return "defense"
    if "offense" in lowered or "run-first" in lowered or "pressure" in lowered:
        return "offense"
    return None


def _legal_parameters(side: str | None) -> dict[str, Any]:
    specs = parameter_specs()
    if side == "offense":
        keys = OFFENSE_PARAMETERS
    elif side == "defense":
        keys = DEFENSE_PARAMETERS
    else:
        keys = set(specs)
    return {key: specs[key] for key in sorted(keys)}


def _schema() -> dict[str, Any]:
    return {
        "required_fields": sorted(REQUIRED_PROPOSAL_KEYS),
        "proposal": {
            "summary": "string",
            "intent": ["create", "tweak", "save_as_new", "clarify"],
            "target_draft_id": "string|null",
            "target_tier": ["declarative", "prompt_policy"],
            "target_side": ["offense", "defense"],
            "target_identity_id": "string|null",
            "proposed_changes": {
                "required_fields": sorted(REQUIRED_CHANGE_KEYS),
                "shape": {"parameter": "string", "from": "any|null", "to": "any", "reason": "string"},
            },
            "evidence_refs": {
                "required_fields": sorted(REQUIRED_EVIDENCE_KEYS),
                "shape": {"type": ["film_room_event", "graph_card", "identity_fact"], "id": "string", "play_index": "integer|null"},
            },
            "requires_confirmation": "boolean",
        },
    }


def _canonical_prompt_examples() -> list[dict[str, Any]]:
    return [
        {
            "prompt": prompt,
            "proposal": propose_from_prompt(prompt, {}, session_id="context-pack", ip="0.0.0.0"),
        }
        for prompt in CANONICAL_PROMPTS
    ]


def _selected_identity(identity_id: str | None) -> dict[str, Any] | None:
    if not identity_id:
        return None
    try:
        return identity_to_dict(get_identity(identity_id))
    except KeyError:
        return None


def _event_tags(public: dict[str, Any]) -> list[str]:
    return sorted({str(event.get("tag")) for event in public.get("events", []) if event.get("tag")})


def _validation_ok(public: dict[str, Any]) -> bool:
    result = public.get("validation_result")
    if isinstance(result, dict):
        return not result.get("errors")
    return True


def _card_notes(public: dict[str, Any]) -> list[str]:
    graph = StrategyGraph()
    cards = {card["id"]: card for card in graph.interactions}
    notes: list[str] = []
    for event in public.get("events", []):
        card_id = event.get("graph_card_id")
        if card_id in cards:
            notes.append(film_room_note_for_event(event, cards[card_id]))
    return notes[:3]


def _play_summary(play: dict[str, Any]) -> dict[str, Any]:
    public = play.get("public", play)
    play_index = int(public.get("play_index", 0))
    offense_action = public.get("offense_action", {})
    defense_action = public.get("defense_action", {})
    return {
        "play_index": play_index,
        "concept": offense_action.get("concept_family"),
        "counter": defense_action.get("coverage_family"),
        "outcome": public.get("terminal_reason") or ("success" if public.get("success") else "no_success"),
        "success_flag": bool(public.get("success")),
        "validation_ok": _validation_ok(public),
        "graph_card_ids": sorted(public.get("graph_card_ids", [])),
        "film_room_event_id": f"play:{play_index}",
        "film_room_events": _event_tags(public),
    }


def _replay_summary(replay: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(replay, dict):
        return []
    return [_play_summary(play) for play in replay.get("plays", [])]


def _selected_play(summary: list[dict[str, Any]], replay: dict[str, Any] | None, selected_play_index: Any) -> dict[str, Any] | None:
    if selected_play_index is None:
        return None
    try:
        play_index = int(selected_play_index)
    except (TypeError, ValueError):
        return None
    selected = next((item for item in summary if item["play_index"] == play_index), None)
    if not selected or not isinstance(replay, dict):
        return selected
    for play in replay.get("plays", []):
        public = play.get("public", play)
        if int(public.get("play_index", -1)) == play_index:
            return {**selected, "film_room_notes": _card_notes(public)}
    return selected


def _sanitize_user_override(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    result = {key: deepcopy(raw[key]) for key in ("parameter", "to") if key in raw}
    return result or None


def _film_room_narrative(replay: dict[str, Any] | None) -> str | None:
    if not isinstance(replay, dict):
        return None
    narrative = replay.get("film_room", {}).get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        return None
    if DENIED_TEXT_RE.search(narrative):
        raise ValueError("unsafe LLM context narrative")
    return narrative


def assert_safe_context(payload: Any) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in EXPLICIT_DENY_KEYS or DENIED_KEY_RE.match(str(key)):
                    raise ValueError(f"unsafe LLM context key: {key}")
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)


def pack_context(*, prompt: str, server_context: dict[str, Any], budget_state: dict[str, Any]) -> dict[str, Any]:
    side = _target_side(server_context, prompt)
    current_draft = server_context.get("current_draft") if isinstance(server_context.get("current_draft"), dict) else None
    current_policy = None
    if current_draft and isinstance(current_draft.get("config_json"), dict):
        current_policy = {
            "name": current_draft.get("name"),
            "version": current_draft.get("version"),
            "side": current_draft["config_json"].get("side"),
            "config_json": deepcopy(current_draft["config_json"]),
        }
    replay_summary = _replay_summary(server_context.get("replay"))
    film_room_narrative = _film_room_narrative(server_context.get("replay"))
    payload = {
        "task_schema": _schema(),
        "canonical_prompt_examples": _canonical_prompt_examples(),
        "parameter_glossary": load_parameter_glossary(),
        "legal_parameters": _legal_parameters(side),
        "legal_concepts": sorted(_all_concepts(side)) if side else sorted(_all_concepts("offense") | _all_concepts("defense")),
        "legal_graph_cards": sorted(_graph_card_ids()),
        "legal_identity_ids": sorted(_identity_ids()),
        "current_policy": current_policy,
        "selected_identity": _selected_identity(server_context.get("selected_identity_id")),
        "film_room_narrative": film_room_narrative,
        "replay_summary": replay_summary,
        "selected_play": _selected_play(replay_summary, server_context.get("replay"), server_context.get("selected_play_index")),
        "user_override": _sanitize_user_override(server_context.get("user_override")),
        "budget_state": {
            "remaining_calls_in_session": int(budget_state.get("remaining_calls_in_session", 0)),
            "kill_switch": bool(budget_state.get("kill_switch", False)),
        },
        "request": {
            "type": server_context.get("request_type"),
            "has_current_policy": current_policy is not None,
            "has_replay": bool(replay_summary),
        },
    }
    assert set(payload.get("replay_summary", [{}])[0] if payload.get("replay_summary") else {}) <= SAFE_REPLAY_PLAY_FIELDS
    assert_safe_context(payload)
    return payload
