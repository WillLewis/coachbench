from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from coachbench.graph_loader import StrategyGraph, project_root
from coachbench.identities import get_identity, load_identities

from arena.tiers.declarative import validate_tier_config_dict
from arena.tiers.prompt_policy import validate_tier1_config_dict


class ProposalRejected(ValueError):
    pass


INTENTS = {"create", "tweak", "save_as_new", "clarify"}
TARGET_TIERS = {"declarative", "prompt_policy"}
TARGET_SIDES = {"offense", "defense"}
EVIDENCE_TYPES = {"film_room_event", "graph_card", "identity_fact"}
RISK_VALUES = ("low", "medium_low", "medium", "medium_high", "high")
RUN_PASS_VALUES = ("balanced_pass", "pass_heavy", "constraint_heavy", "run_to_play_action")
OFFENSE_PARAMETERS = {
    "risk_tolerance",
    "adaptation_speed",
    "screen_trigger_confidence",
    "explosive_shot_tolerance",
    "run_pass_tendency",
}
DEFENSE_PARAMETERS = {
    "risk_tolerance",
    "disguise_sensitivity",
    "pressure_frequency",
    "counter_repeat_tolerance",
}
NUMERIC_PARAMETERS = {
    "adaptation_speed",
    "screen_trigger_confidence",
    "explosive_shot_tolerance",
    "disguise_sensitivity",
    "pressure_frequency",
    "counter_repeat_tolerance",
}
REQUIRED_PROPOSAL_KEYS = {
    "summary",
    "intent",
    "target_draft_id",
    "target_tier",
    "target_side",
    "target_identity_id",
    "proposed_changes",
    "evidence_refs",
    "requires_confirmation",
}
REQUIRED_CHANGE_KEYS = {"parameter", "from", "to", "reason"}
REQUIRED_EVIDENCE_KEYS = {"type", "id", "play_index"}


def load_parameter_glossary() -> dict[str, Any]:
    path = project_root() / "agent_garage" / "parameter_glossary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parameter_specs() -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for key in load_parameter_glossary():
        if key in NUMERIC_PARAMETERS:
            specs[key] = {"type": "number", "minimum": 0.0, "maximum": 1.0}
        elif key == "risk_tolerance":
            specs[key] = {"type": "enum", "values": list(RISK_VALUES)}
        elif key == "run_pass_tendency":
            specs[key] = {"type": "enum", "values": list(RUN_PASS_VALUES)}
        else:
            specs[key] = {"type": "unknown"}
    return specs


def _profiles() -> dict[str, Any]:
    path = project_root() / "agent_garage" / "profiles.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _public_config(current_draft: dict[str, Any] | None) -> dict[str, Any] | None:
    if not current_draft:
        return None
    raw = current_draft.get("config_json")
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return deepcopy(raw)
    raise ProposalRejected("current draft config_json must be an object")


def _identity_ids() -> set[str]:
    return {identity.id for identity in load_identities()}


def _graph_card_ids() -> set[str]:
    return {card["id"] for card in StrategyGraph().interactions}


def _all_concepts(side: str) -> set[str]:
    graph = StrategyGraph()
    return set(graph.offense_concepts() if side == "offense" else graph.defense_calls())


def _dedupe_valid(values: list[str], side: str) -> list[str]:
    valid = _all_concepts(side)
    result: list[str] = []
    for value in values:
        if value in valid and value not in result:
            result.append(value)
    return result


def _tier_risk(value: Any) -> str:
    raw = str(value or "medium")
    if raw == "low":
        return "low"
    if raw == "high":
        return "high"
    return "medium"


def _assistant_parameters(config: dict[str, Any]) -> dict[str, Any]:
    constraints = config.setdefault("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
        config["constraints"] = constraints
    params = constraints.setdefault("assistant_parameters", {})
    if not isinstance(params, dict):
        params = {}
        constraints["assistant_parameters"] = params
    return params


def current_parameter_value(config: dict[str, Any], parameter: str) -> Any:
    params = _assistant_parameters(config)
    if parameter in params:
        return params[parameter]
    if parameter in {"risk_tolerance", "adaptation_speed"} and parameter in config:
        return config[parameter]
    if parameter == "run_pass_tendency":
        preferred = set(config.get("preferred_concepts", []))
        if {"inside_zone", "play_action_flood"} <= preferred:
            return "run_to_play_action"
        if {"rpo_glance", "screen"} & preferred:
            return "constraint_heavy"
        return "balanced_pass"
    if parameter in NUMERIC_PARAMETERS:
        return 0.5
    if parameter == "risk_tolerance":
        return "medium"
    return None


def _parameter_allowed_for_side(parameter: str, side: str) -> bool:
    allowed = DEFENSE_PARAMETERS if side == "defense" else OFFENSE_PARAMETERS
    return parameter in allowed


def _validate_value(parameter: str, raw: Any) -> None:
    spec = parameter_specs().get(parameter)
    if not spec:
        raise ProposalRejected(f"unknown parameter: {parameter}")
    if spec["type"] == "number":
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise ProposalRejected(f"{parameter} must be a number")
        if float(raw) < spec["minimum"] or float(raw) > spec["maximum"]:
            raise ProposalRejected(f"{parameter} must be between 0 and 1")
    elif spec["type"] == "enum":
        if raw not in spec["values"]:
            raise ProposalRejected(f"{parameter} must be one of {spec['values']}")
    else:
        raise ProposalRejected(f"{parameter} has no supported P0-5 validator")


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return left == right


def _validate_identity_ref(identity_id: str | None) -> None:
    if identity_id is None:
        return
    try:
        get_identity(identity_id)
    except KeyError as exc:
        raise ProposalRejected(f"unknown identity: {identity_id}") from exc


def _validate_film_room_ref(ref: dict[str, Any], context: dict[str, Any] | None) -> None:
    if not context or not context.get("replay"):
        raise ProposalRejected("film_room_event evidence requires replay context")
    play_index = ref.get("play_index")
    if not isinstance(play_index, int):
        raise ProposalRejected("film_room_event evidence requires an integer play_index")
    replay = context["replay"]
    for play in replay.get("plays", []):
        public = play.get("public", play)
        if int(public.get("play_index", -1)) == play_index:
            return
    raise ProposalRejected(f"film_room_event play_index does not exist: {play_index}")


def _validate_evidence_ref(ref: dict[str, Any], context: dict[str, Any] | None) -> None:
    if set(ref) != REQUIRED_EVIDENCE_KEYS:
        raise ProposalRejected("evidence_refs entries must contain type, id, and play_index")
    ref_type = ref.get("type")
    ref_id = str(ref.get("id") or "")
    if ref_type not in EVIDENCE_TYPES:
        raise ProposalRejected(f"unknown evidence type: {ref_type}")
    if not ref_id:
        raise ProposalRejected("evidence id is required")
    if ref_type == "graph_card" and ref_id not in _graph_card_ids():
        raise ProposalRejected(f"unknown graph card evidence: {ref_id}")
    if ref_type == "identity_fact":
        identity_id = ref_id.split(":", 1)[0]
        if identity_id not in _identity_ids():
            raise ProposalRejected(f"unknown identity evidence: {ref_id}")
    if ref_type == "film_room_event":
        _validate_film_room_ref(ref, context)


def _validate_tier_config(target_tier: str, payload: dict[str, Any]) -> None:
    try:
        if target_tier == "declarative":
            validate_tier_config_dict(payload)
        else:
            validate_tier1_config_dict(payload)
    except ValueError as exc:
        raise ProposalRejected(f"merged config failed tier validator: {exc}") from exc


def _profile_params(side: str, identity_id: str | None) -> tuple[str, dict[str, Any]]:
    profiles = _profiles()
    if identity_id:
        identity = get_identity(identity_id)
        key = identity.default_archetype[side]
    else:
        key = "efficiency_optimizer" if side == "offense" else "coverage_shell_conservative"
    bucket = "offense_archetypes" if side == "offense" else "defense_archetypes"
    profile = profiles[bucket][key]
    params = dict(profile.get("parameters", {}))
    if identity_id:
        params.update(get_identity(identity_id).default_policy_overrides)
    return key, params


def base_declarative_config(side: str, identity_id: str | None = None, agent_name: str = "Assistant Draft") -> dict[str, Any]:
    _key, params = _profile_params(side, identity_id)
    if side == "offense":
        config = {
            "agent_name": agent_name,
            "side": "offense",
            "access_tier": "declarative",
            "risk_tolerance": _tier_risk(params.get("risk_tolerance", "medium")),
            "red_zone": {"default": "quick_game"},
            "third_down": {"default": "quick_game"},
            "preferred_concepts": ["quick_game", "inside_zone"],
            "avoided_concepts": [],
            "adaptation_speed": float(params.get("adaptation_speed", 0.5)),
            "tendency_break_rate": 0.1,
            "constraints": {},
        }
        for key in OFFENSE_PARAMETERS:
            if key in params:
                _apply_parameter_to_config(config, key, params[key])
        return config
    config = {
        "agent_name": agent_name,
        "side": "defense",
        "access_tier": "declarative",
        "risk_tolerance": _tier_risk(params.get("risk_tolerance", "medium")),
        "red_zone": {"default": "redzone_bracket"},
        "third_down": {"default": "cover3_match"},
        "preferred_concepts": ["cover3_match", "redzone_bracket"],
        "avoided_concepts": [],
        "adaptation_speed": float(params.get("adaptation_speed", 0.5)),
        "tendency_break_rate": 0.1,
        "constraints": {},
    }
    for key in DEFENSE_PARAMETERS:
        if key in params:
            _apply_parameter_to_config(config, key, params[key])
    return config


def _set_preferred(config: dict[str, Any], side: str, concepts: list[str]) -> None:
    config["preferred_concepts"] = _dedupe_valid(concepts + list(config.get("preferred_concepts", [])), side)


def _set_avoided(config: dict[str, Any], side: str, concepts: list[str]) -> None:
    preferred = set(config.get("preferred_concepts", []))
    config["avoided_concepts"] = _dedupe_valid([item for item in concepts if item not in preferred] + list(config.get("avoided_concepts", [])), side)


def _remove_avoided(config: dict[str, Any], concepts: list[str]) -> None:
    blocked = set(concepts)
    config["avoided_concepts"] = [item for item in config.get("avoided_concepts", []) if item not in blocked]


def _apply_parameter_to_config(config: dict[str, Any], parameter: str, raw: Any) -> None:
    side = config["side"]
    _assistant_parameters(config)[parameter] = raw
    constraints = config.setdefault("constraints", {})
    if parameter == "risk_tolerance":
        config["risk_tolerance"] = _tier_risk(raw)
    elif parameter == "adaptation_speed":
        config["adaptation_speed"] = round(float(raw), 4)
    elif parameter == "screen_trigger_confidence":
        if float(raw) >= 0.55:
            _set_preferred(config, side, ["screen", "quick_game"])
            _remove_avoided(config, ["screen"])
        else:
            _set_avoided(config, side, ["screen"])
    elif parameter == "explosive_shot_tolerance":
        if float(raw) <= 0.35:
            _set_avoided(config, side, ["vertical_shot"])
            constraints["max_vertical_shot_rate"] = 0.0
        else:
            _remove_avoided(config, ["vertical_shot"])
            constraints.pop("max_vertical_shot_rate", None)
            if float(raw) >= 0.65:
                _set_preferred(config, side, ["vertical_shot"])
    elif parameter == "run_pass_tendency":
        mapping = {
            "balanced_pass": ["quick_game", "inside_zone", "play_action_flood"],
            "pass_heavy": ["quick_game", "rpo_glance", "bunch_mesh", "play_action_flood"],
            "constraint_heavy": ["rpo_glance", "screen", "bootleg", "quick_game"],
            "run_to_play_action": ["inside_zone", "outside_zone", "play_action_flood", "bootleg"],
        }
        config["preferred_concepts"] = _dedupe_valid(mapping[str(raw)], side)
        config["red_zone"] = {"default": config["preferred_concepts"][0]}
        config["third_down"] = {"default": "play_action_flood" if "play_action_flood" in config["preferred_concepts"] else config["preferred_concepts"][0]}
    elif parameter == "disguise_sensitivity":
        if float(raw) >= 0.55:
            _set_preferred(config, side, ["simulated_pressure", "trap_coverage"])
        else:
            _set_preferred(config, side, ["cover3_match", "redzone_bracket"])
    elif parameter == "pressure_frequency":
        if float(raw) <= 0.45:
            _set_avoided(config, side, ["zero_pressure"])
            constraints["max_zero_pressure_rate"] = 0.0
        else:
            constraints.pop("max_zero_pressure_rate", None)
            _set_preferred(config, side, ["simulated_pressure"])
            if float(raw) >= 0.75:
                _set_preferred(config, side, ["zero_pressure"])
        config["third_down"] = {"default": "simulated_pressure" if float(raw) >= 0.45 else "cover3_match"}
    elif parameter == "counter_repeat_tolerance":
        if float(raw) <= 0.45:
            constraints["max_redzone_bracket_rate"] = 0.5
            constraints["max_bear_front_rate"] = 0.5
        else:
            constraints.pop("max_redzone_bracket_rate", None)
            constraints.pop("max_bear_front_rate", None)


def _base_config_for_proposal(proposal: dict[str, Any], current_draft: dict[str, Any] | None) -> dict[str, Any]:
    current_config = _public_config(current_draft)
    if current_config and proposal["intent"] in {"tweak", "save_as_new"}:
        return current_config
    if proposal["target_tier"] != "declarative":
        raise ProposalRejected("prompt_policy authoring is schema-only in P0-5")
    return base_declarative_config(
        proposal["target_side"],
        proposal.get("target_identity_id"),
        agent_name="Assistant Draft",
    )


def apply_proposal(proposal: dict[str, Any], *, current_draft: dict[str, Any] | None) -> dict[str, Any]:
    if proposal.get("intent") == "clarify":
        return _public_config(current_draft) or {}
    config = _base_config_for_proposal(proposal, current_draft)
    for change in proposal.get("proposed_changes", []):
        _apply_parameter_to_config(config, change["parameter"], change["to"])
    return config


def validate_proposal(
    payload: dict[str, Any],
    *,
    current_draft: dict[str, Any] | None,
    context: dict[str, Any] | None = None,
) -> None:
    if set(payload) != REQUIRED_PROPOSAL_KEYS:
        missing = REQUIRED_PROPOSAL_KEYS - set(payload)
        extra = set(payload) - REQUIRED_PROPOSAL_KEYS
        raise ProposalRejected(f"proposal fields mismatch missing={sorted(missing)} extra={sorted(extra)}")
    if not str(payload["summary"]).strip():
        raise ProposalRejected("proposal summary is required")
    intent = payload["intent"]
    if intent not in INTENTS:
        raise ProposalRejected(f"unknown intent: {intent}")
    if payload["target_tier"] not in TARGET_TIERS:
        raise ProposalRejected(f"unknown target_tier: {payload['target_tier']}")
    if payload["target_side"] not in TARGET_SIDES:
        raise ProposalRejected(f"unknown target_side: {payload['target_side']}")
    _validate_identity_ref(payload.get("target_identity_id"))
    if intent == "clarify":
        if payload["proposed_changes"]:
            raise ProposalRejected("clarify proposals cannot contain proposed_changes")
        return
    if intent == "tweak" and (not payload.get("target_draft_id") or not current_draft):
        raise ProposalRejected("tweak proposals require a known target_draft_id")
    if payload["target_tier"] == "prompt_policy" and payload.get("proposed_changes"):
        raise ProposalRejected("prompt_policy authoring is schema-only in P0-5")
    current_config = _public_config(current_draft)
    if current_config and current_config.get("side") != payload["target_side"]:
        raise ProposalRejected("target_side does not match current draft side")
    changes = payload["proposed_changes"]
    if not isinstance(changes, list):
        raise ProposalRejected("proposed_changes must be a list")
    for change in changes:
        if set(change) != REQUIRED_CHANGE_KEYS:
            raise ProposalRejected("proposed_changes entries must contain parameter, from, to, and reason")
        parameter = str(change["parameter"])
        if parameter not in load_parameter_glossary():
            raise ProposalRejected(f"unknown parameter: {parameter}")
        if not _parameter_allowed_for_side(parameter, payload["target_side"]):
            raise ProposalRejected(f"{parameter} is not valid for {payload['target_side']}")
        _validate_value(parameter, change["to"])
        if not str(change["reason"]).strip():
            raise ProposalRejected("change reason is required")
        if intent == "tweak":
            expected = current_parameter_value(current_config or {}, parameter)
            if not _same_value(change["from"], expected):
                raise ProposalRejected(f"stale from value for {parameter}: expected {expected!r}")
    evidence_refs = payload["evidence_refs"]
    if not isinstance(evidence_refs, list):
        raise ProposalRejected("evidence_refs must be a list")
    for ref in evidence_refs:
        _validate_evidence_ref(ref, context)
    merged = apply_proposal(payload, current_draft=current_draft)
    _validate_tier_config(payload["target_tier"], merged)
