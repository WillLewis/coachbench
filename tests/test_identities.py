from __future__ import annotations

import json
from pathlib import Path

from coachbench.graph_loader import StrategyGraph
from coachbench.identities import BANNED_IDENTITY_TOKENS, load_identities, validate_identity


def test_launch_identities_load_and_validate() -> None:
    identities = load_identities()
    assert 2 <= len(identities) <= 4
    for identity in identities:
        validate_identity({
            "id": identity.id,
            "display_name": identity.display_name,
            "side_eligibility": list(identity.side_eligibility),
            "coordinator_style": identity.coordinator_style,
            "default_archetype": identity.default_archetype,
            "default_policy_overrides": identity.default_policy_overrides,
            "preferred_concept_families": list(identity.preferred_concept_families),
            "known_vulnerabilities": list(identity.known_vulnerabilities),
            "bio": identity.bio,
        })


def test_identity_references_existing_archetypes_and_graph_concepts() -> None:
    payload = json.loads(Path("data/identities/launch_identities.json").read_text(encoding="utf-8"))
    profiles = json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))
    graph = StrategyGraph()
    vocab = set(graph.offense_concepts()) | set(graph.defense_calls())
    for identity in payload["identities"]:
        assert identity["default_archetype"]["offense"] in profiles["offense_archetypes"]
        assert identity["default_archetype"]["defense"] in profiles["defense_archetypes"]
        assert set(identity["preferred_concept_families"]) <= vocab
        assert {item["counter_concept"] for item in identity["known_vulnerabilities"]} <= vocab


def test_identity_text_contains_no_prohibited_tokens() -> None:
    for identity in load_identities():
        fields = [
            identity.display_name,
            identity.coordinator_style,
            identity.bio,
            *[item["note"] for item in identity.known_vulnerabilities],
        ]
        text = " ".join(fields).lower()
        assert not any(token in text for token in BANNED_IDENTITY_TOKENS)
