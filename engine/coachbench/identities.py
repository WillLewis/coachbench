from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph_loader import StrategyGraph, project_root


BANNED_IDENTITY_TOKENS = (
    "n" + "fl",
    "n" + "flpa",
    "n" + "caa",
    "super " + "bowl",
    "pro " + "bowl",
    "mad" + "den",
    "p" + "ff",
    "next " + "gen stats",
    "od" + "ds",
    "b" + "et",
    "wag" + "er",
    "sports" + "book",
    "pay" + "out",
    "ca" + "sh",
    "draft" + "kings",
    "fan" + "duel",
    "kansas city " + "chiefs",
    "dallas " + "cowboys",
    "green bay " + "packers",
    "new england " + "patriots",
    "pittsburgh " + "steelers",
    "san francisco " + "49ers",
    "tom " + "brady",
    "patrick " + "mahomes",
)


@dataclass(frozen=True)
class Identity:
    id: str
    display_name: str
    side_eligibility: tuple[str, ...]
    coordinator_style: str
    default_archetype: dict[str, str]
    default_policy_overrides: dict[str, Any]
    preferred_concept_families: tuple[str, ...]
    known_vulnerabilities: tuple[dict[str, str], ...]
    bio: str


def _identity_path() -> Path:
    return project_root() / "data" / "identities" / "launch_identities.json"


def _profiles_path() -> Path:
    return project_root() / "agent_garage" / "profiles.json"


def _load_profiles() -> dict[str, Any]:
    return json.loads(_profiles_path().read_text(encoding="utf-8"))


def _contains_banned_token(text: str) -> str | None:
    lowered = text.lower()
    for token in BANNED_IDENTITY_TOKENS:
        if token in lowered:
            return token
    return None


def _validate_text(value: str, field: str) -> None:
    token = _contains_banned_token(value)
    if token:
        raise ValueError(f"identity {field} contains prohibited token: {token}")


def _graph_vocabulary() -> set[str]:
    graph = StrategyGraph()
    return set(graph.offense_concepts()) | set(graph.defense_calls())


def validate_identity(payload: dict[str, Any]) -> None:
    required = {
        "id",
        "display_name",
        "side_eligibility",
        "coordinator_style",
        "default_archetype",
        "default_policy_overrides",
        "preferred_concept_families",
        "known_vulnerabilities",
        "bio",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"identity missing fields: {sorted(missing)}")
    if not payload["id"] or not str(payload["id"]).replace("_", "").isalnum():
        raise ValueError("identity id must be snake-case compatible")
    sides = set(payload["side_eligibility"])
    if not sides or not sides <= {"offense", "defense"}:
        raise ValueError("identity side_eligibility must contain offense and/or defense")
    for field in ("display_name", "coordinator_style", "bio"):
        _validate_text(str(payload[field]), field)
    profiles = _load_profiles()
    archetypes = dict(payload["default_archetype"])
    if archetypes.get("offense") not in profiles["offense_archetypes"]:
        raise ValueError("identity default offense archetype is unknown")
    if archetypes.get("defense") not in profiles["defense_archetypes"]:
        raise ValueError("identity default defense archetype is unknown")
    vocab = _graph_vocabulary()
    unknown = set(payload["preferred_concept_families"]) - vocab
    if unknown:
        raise ValueError(f"identity references unknown preferred concepts: {sorted(unknown)}")
    for item in payload["known_vulnerabilities"]:
        if item.get("counter_concept") not in vocab:
            raise ValueError(f"identity references unknown counter concept: {item.get('counter_concept')}")
        _validate_text(str(item.get("note", "")), "known vulnerability note")


def _to_identity(payload: dict[str, Any]) -> Identity:
    return Identity(
        id=payload["id"],
        display_name=payload["display_name"],
        side_eligibility=tuple(payload["side_eligibility"]),
        coordinator_style=payload["coordinator_style"],
        default_archetype=dict(payload["default_archetype"]),
        default_policy_overrides=dict(payload["default_policy_overrides"]),
        preferred_concept_families=tuple(payload["preferred_concept_families"]),
        known_vulnerabilities=tuple(dict(item) for item in payload["known_vulnerabilities"]),
        bio=payload["bio"],
    )


def load_identities() -> list[Identity]:
    payload = json.loads(_identity_path().read_text(encoding="utf-8"))
    identities = list(payload.get("identities", []))
    for identity in identities:
        validate_identity(identity)
    return [_to_identity(identity) for identity in identities]


def get_identity(identity_id: str) -> Identity:
    for identity in load_identities():
        if identity.id == identity_id:
            return identity
    raise KeyError(f"unknown identity: {identity_id}")


def identity_to_dict(identity: Identity) -> dict[str, Any]:
    return {
        "id": identity.id,
        "display_name": identity.display_name,
        "side_eligibility": list(identity.side_eligibility),
        "coordinator_style": identity.coordinator_style,
        "default_archetype": dict(identity.default_archetype),
        "default_policy_overrides": dict(identity.default_policy_overrides),
        "preferred_concept_families": list(identity.preferred_concept_families),
        "known_vulnerabilities": [dict(item) for item in identity.known_vulnerabilities],
        "bio": identity.bio,
    }
