from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from coachbench.identities import get_identity

from .proposal import (
    current_parameter_value,
    load_parameter_glossary,
    parameter_specs,
)


GRAPH_PRESSURE_SCREEN = "redzone.screen_vs_zero_pressure.v1"
GRAPH_SIM_PRESSURE = "redzone.screen_vs_simulated_pressure.v1"
GRAPH_RUN_ACTION = "redzone.play_action_after_run_tendency.v1"
GRAPH_EXPLOSIVE_CAP = "redzone.vertical_vs_two_high.v1"


def _clean(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.lower()).strip()


def _current_draft(context: dict[str, Any]) -> dict[str, Any] | None:
    draft = context.get("current_draft")
    return dict(draft) if isinstance(draft, dict) else None


def _current_config(context: dict[str, Any]) -> dict[str, Any] | None:
    draft = _current_draft(context)
    if not draft:
        return None
    raw = draft.get("config_json")
    if isinstance(raw, dict):
        return deepcopy(raw)
    return None


def _intent_for(side: str, context: dict[str, Any]) -> tuple[str, str | None]:
    draft = _current_draft(context)
    config = _current_config(context)
    if draft and config and config.get("side") == side:
        return "tweak", str(draft["id"])
    return "create", None


def _identity_id(context: dict[str, Any]) -> str | None:
    raw = context.get("selected_identity_id")
    return str(raw) if raw else None


def _from_value(parameter: str, context: dict[str, Any], intent: str) -> Any:
    config = _current_config(context)
    if intent == "tweak" and config:
        return current_parameter_value(config, parameter)
    return None


def _bounded(parameter: str, raw: Any) -> Any:
    spec = parameter_specs()[parameter]
    if spec["type"] == "number":
        return round(max(spec["minimum"], min(spec["maximum"], float(raw))), 2)
    return raw


def _change(parameter: str, to: Any, reason: str, context: dict[str, Any], intent: str) -> dict[str, Any]:
    return {
        "parameter": parameter,
        "from": _from_value(parameter, context, intent),
        "to": _bounded(parameter, to),
        "reason": reason,
    }


def _proposal(
    *,
    summary: str,
    intent: str,
    side: str,
    context: dict[str, Any],
    changes: list[tuple[str, Any, str]],
    evidence_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved_intent, target_draft_id = _intent_for(side, context)
    if intent == "clarify":
        resolved_intent = "clarify"
        target_draft_id = None
    elif intent in {"create", "tweak"}:
        resolved_intent = resolved_intent if intent == "tweak" else "create"
    else:
        resolved_intent = intent
    return {
        "summary": summary,
        "intent": resolved_intent,
        "target_draft_id": target_draft_id,
        "target_tier": "declarative",
        "target_side": side,
        "target_identity_id": _identity_id(context),
        "proposed_changes": [
            _change(parameter, to, reason, context, resolved_intent)
            for parameter, to, reason in changes
        ],
        "evidence_refs": evidence_refs,
        "requires_confirmation": resolved_intent != "clarify",
    }


def _clarify(summary: str, *, side: str = "offense", context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "summary": summary,
        "intent": "clarify",
        "target_draft_id": None,
        "target_tier": "declarative",
        "target_side": side,
        "target_identity_id": _identity_id(context or {}),
        "proposed_changes": [],
        "evidence_refs": [],
        "requires_confirmation": False,
    }


def _graph_ref(card_id: str) -> dict[str, Any]:
    return {"type": "graph_card", "id": card_id, "play_index": None}


def _identity_ref(identity_id: str | None) -> list[dict[str, Any]]:
    if not identity_id:
        return []
    return [{"type": "identity_fact", "id": f"{identity_id}:default_archetype", "play_index": None}]


def _selected_play(context: dict[str, Any]) -> dict[str, Any] | None:
    replay = context.get("replay")
    if not isinstance(replay, dict):
        return None
    selected = int(context.get("selected_play_index") or 0)
    for play in replay.get("plays", []):
        public = play.get("public", play)
        if int(public.get("play_index", -1)) == selected:
            return play
    return None


def _event_tags(play: dict[str, Any] | None) -> set[str]:
    if not play:
        return set()
    tags: set[str] = set()
    for bucket in ("offense_observed", "defense_observed"):
        for event in play.get(bucket, {}).get("events", []):
            if event.get("tag"):
                tags.add(str(event["tag"]))
    for event in play.get("events", []):
        if event.get("tag"):
            tags.add(str(event["tag"]))
    return tags


def _film_room_proposal(context: dict[str, Any]) -> dict[str, Any]:
    draft = _current_draft(context)
    config = _current_config(context)
    if not draft or not config:
        return _clarify(
            "Select or save a draft first, then I can turn this Film Room note into a concrete tweak.",
            context=context,
        )
    side = str(config.get("side", "offense"))
    play = _selected_play(context)
    play_index = int(context.get("selected_play_index") or 0)
    tags = _event_tags(play)
    run_id = str(context.get("current_run_id") or "replay")
    evidence_refs = [{"type": "film_room_event", "id": f"{run_id}:play:{play_index}", "play_index": play_index}]
    if "screen_baited" in tags or "simulated_pressure_revealed" in tags:
        evidence_refs.append(_graph_ref(GRAPH_SIM_PRESSURE))
    if side == "defense":
        return _proposal(
            summary="Use the selected Film Room event to make the defense disguise earlier without adding a new concept.",
            intent="tweak",
            side="defense",
            context=context,
            changes=[
                ("disguise_sensitivity", max(float(current_parameter_value(config, "disguise_sensitivity")), 0.72), "Film Room event play:%d and graph card %s support earlier disguise." % (play_index, GRAPH_SIM_PRESSURE)),
            ],
            evidence_refs=evidence_refs,
        )
    return _proposal(
        summary="Use the selected Film Room event to make pressure answers arrive earlier while keeping shots capped.",
        intent="tweak",
        side="offense",
        context=context,
        changes=[
            ("screen_trigger_confidence", max(float(current_parameter_value(config, "screen_trigger_confidence")), 0.68), "Film Room event play:%d and graph card %s support a quicker screen answer." % (play_index, GRAPH_SIM_PRESSURE)),
            ("explosive_shot_tolerance", min(float(current_parameter_value(config, "explosive_shot_tolerance")), 0.3), "Graph card %s supports keeping volatile shots capped after the selected event." % GRAPH_EXPLOSIVE_CAP),
        ],
        evidence_refs=evidence_refs,
    )


def _apply_user_override(proposal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    override = context.get("user_override")
    if not isinstance(override, dict):
        return proposal
    parameter = override.get("parameter")
    if parameter not in load_parameter_glossary():
        return proposal
    for change in proposal["proposed_changes"]:
        if change["parameter"] == parameter:
            change["to"] = _bounded(parameter, override.get("to"))
            change["reason"] = f"User override for {parameter}; server validation still applies."
    return proposal


def propose_from_prompt(prompt: str, context: dict[str, Any], *, session_id: str, ip: str) -> dict[str, Any]:
    del session_id, ip
    request_type = context.get("request_type")
    if request_type == "identity_selected":
        identity_id = _identity_id(context)
        if not identity_id:
            return _clarify("Pick an identity, then choose whether this draft should play offense or defense.", context=context)
        identity = get_identity(identity_id)
        return _clarify(
            f"Selected {identity.display_name}. What kind of coordinator do you want - offense or defense, and how should they play?",
            side=identity.side_eligibility[0],
            context=context,
        )
    if request_type == "film_room_tweak":
        return _apply_user_override(_film_room_proposal(context), context)

    text = _clean(prompt)
    identity_refs = _identity_ref(_identity_id(context))
    if "punish" in text and "pressure" in text and ("pick" in text or "turnover" in text):
        return _apply_user_override(_proposal(
            summary="Shift the offense toward pressure answers while capping volatile shot calls.",
            intent="create",
            side="offense",
            context=context,
            changes=[
                ("screen_trigger_confidence", 0.68, f"Graph card {GRAPH_PRESSURE_SCREEN} supports screen answers to pressure looks."),
                ("explosive_shot_tolerance", 0.25, f"Graph card {GRAPH_EXPLOSIVE_CAP} supports keeping high-variance shots capped."),
                ("risk_tolerance", "medium", "Risk stays medium so the proposal does not chase hidden outcomes."),
            ],
            evidence_refs=[_graph_ref(GRAPH_PRESSURE_SCREEN), _graph_ref(GRAPH_EXPLOSIVE_CAP), *identity_refs],
        ), context)
    if "disguise" in text and ("rush budget" in text or "burn" in text):
        return _apply_user_override(_proposal(
            summary="Make the defense show more late movement while reducing pressure spend.",
            intent="create",
            side="defense",
            context=context,
            changes=[
                ("disguise_sensitivity", 0.76, f"Graph card {GRAPH_SIM_PRESSURE} is the grounded disguise reference."),
                ("pressure_frequency", 0.42, "Lower pressure frequency limits rush-resource burn without inventing a new call."),
            ],
            evidence_refs=[_graph_ref(GRAPH_SIM_PRESSURE), *identity_refs],
        ), context)
    if "baited" in text and "simulated pressure" in text:
        return _apply_user_override(_proposal(
            summary="Answer simulated pressure by moving screen timing earlier and keeping the shot cap conservative.",
            intent="tweak",
            side="offense",
            context=context,
            changes=[
                ("screen_trigger_confidence", 0.7, f"Graph card {GRAPH_SIM_PRESSURE} is the grounded simulated-pressure reference."),
                ("explosive_shot_tolerance", 0.28, f"Graph card {GRAPH_EXPLOSIVE_CAP} supports avoiding volatile answers."),
            ],
            evidence_refs=[_graph_ref(GRAPH_SIM_PRESSURE), _graph_ref(GRAPH_EXPLOSIVE_CAP), *identity_refs],
        ), context)
    if "run-first" in text or ("run" in text and "play-action" in text):
        return _apply_user_override(_proposal(
            summary="Build the offense around run tendency before shifting into graph-backed play-action.",
            intent="create",
            side="offense",
            context=context,
            changes=[
                ("run_pass_tendency", "run_to_play_action", f"Graph card {GRAPH_RUN_ACTION} supports play-action after run tendency."),
                ("adaptation_speed", 0.78, "Adaptation speed helps the draft move once run tendency is observed."),
                ("explosive_shot_tolerance", 0.22, "The shot cap stays low so play-action is not treated as a separate phantom knob."),
            ],
            evidence_refs=[_graph_ref(GRAPH_RUN_ACTION), *identity_refs],
        ), context)
    if "safe" in text and ("red-zone" in text or "red zone" in text) and "explosive" in text:
        return _apply_user_override(_proposal(
            summary="Keep the defense compact by pairing moderate disguise with less repeated counter exposure.",
            intent="create",
            side="defense",
            context=context,
            changes=[
                ("risk_tolerance", "low", "Risk stays low for a safer red-zone profile."),
                ("disguise_sensitivity", 0.58, f"Graph card {GRAPH_EXPLOSIVE_CAP} is the grounded explosive-window reference."),
                ("counter_repeat_tolerance", 0.35, "Lower repeat tolerance reduces repeated counter exposure in the saved config."),
            ],
            evidence_refs=[_graph_ref(GRAPH_EXPLOSIVE_CAP), *identity_refs],
        ), context)
    return _clarify(
        "I need a bit more on what you want to optimize. Try one of the suggested prompts or specify offense vs defense and risk preference.",
        context=context,
    )
