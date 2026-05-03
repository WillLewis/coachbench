from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


GRAPH_DIR = Path("graph/redzone_v0")


def _load_graph_json(name: str) -> dict[str, Any]:
    return json.loads((GRAPH_DIR / name).read_text(encoding="utf-8"))


def test_every_interaction_declares_counters_and_limitations() -> None:
    interactions = _load_graph_json("interactions.json")["interactions"]

    for interaction in interactions:
        assert interaction.get("counters"), f"{interaction['id']} must declare at least one counter"
        assert interaction.get("limitations"), f"{interaction['id']} must document limitations"


def test_every_tactical_event_declares_visibility() -> None:
    interactions = _load_graph_json("interactions.json")["interactions"]
    allowed_sides = {"offense", "defense"}

    for interaction in interactions:
        for event in interaction.get("tactical_events", []):
            assert isinstance(event, dict), f"{interaction['id']} tactical events must be objects"
            assert event.get("tag"), f"{interaction['id']} has a tactical event without a tag"
            visible_to = set(event.get("visible_to", []))
            assert visible_to, f"{interaction['id']} event {event['tag']} must declare visible_to"
            assert visible_to <= allowed_sides, (
                f"{interaction['id']} event {event['tag']} has invalid visibility: {sorted(visible_to)}"
            )


def test_concept_cards_declare_action_fields_and_resolution_priors() -> None:
    concepts = _load_graph_json("concepts.json")
    offense_fields = {"personnel_family", "formation_family", "motion_family", "protection_family"}
    defense_fields = {"personnel_family", "front_family", "pressure_family", "disguise_family", "matchup_focus"}

    for concept in concepts["offense"]:
        assert offense_fields <= set(concept.get("action_fields", {})), f"{concept['id']} missing offense action fields"
        assert "base_ep" in concept, f"{concept['id']} missing base_ep"
        assert "base_success" in concept, f"{concept['id']} missing base_success"

    for call in concepts["defense"]:
        assert defense_fields <= set(call.get("action_fields", {})), f"{call['id']} missing defense action fields"


def test_belief_model_only_references_declared_tactical_events() -> None:
    interactions = _load_graph_json("interactions.json")["interactions"]
    declared_tags = {
        event["tag"]
        for interaction in interactions
        for event in interaction.get("tactical_events", [])
    }
    belief_tags = set(_load_graph_json("belief_model.json")["belief_deltas"])

    assert belief_tags <= declared_tags


def test_interaction_modifiers_stay_within_declared_bounds() -> None:
    interactions = _load_graph_json("interactions.json")["interactions"]
    bounds = _load_graph_json("graph_tests.json")["modifier_bounds"]

    for interaction in interactions:
        for modifier, (lower, upper) in bounds.items():
            value = float(interaction.get(modifier, 0.0))
            assert lower <= value <= upper, (
                f"{interaction['id']} {modifier}={value} is outside declared bounds "
                f"[{lower}, {upper}]"
            )


def test_all_interaction_references_exist_in_concept_vocabularies() -> None:
    concepts = _load_graph_json("concepts.json")
    offense_ids = {item["id"] for item in concepts["offense"]}
    defense_ids = {item["id"] for item in concepts["defense"]}
    interactions = _load_graph_json("interactions.json")["interactions"]

    for interaction in interactions:
        unknown_offense = set(interaction.get("offense_concepts", [])) - offense_ids
        unknown_defense = set(interaction.get("defense_calls", [])) - defense_ids
        assert not unknown_offense, f"{interaction['id']} references unknown offense concepts: {sorted(unknown_offense)}"
        assert not unknown_defense, f"{interaction['id']} references unknown defense calls: {sorted(unknown_defense)}"

        trigger = interaction.get("sequence_trigger", {})
        unknown_trigger_concepts = set(trigger.get("offense_recent", [])) - offense_ids
        assert not unknown_trigger_concepts, (
            f"{interaction['id']} references unknown sequence-trigger concepts: "
            f"{sorted(unknown_trigger_concepts)}"
        )


def test_graph_contains_no_banned_licensed_or_wagering_terms() -> None:
    graph_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(GRAPH_DIR.glob("*.json")))
    banned_patterns = [
        r"\bnfl\b",
        r"\bnflpa\b",
        r"\bncaa\b",
        r"\bsuper\s+bowl\b",
        r"\bpro\s+bowl\b",
        r"\bmadden\b",
        r"\bpff\b",
        r"\bnext\s+gen\s+stats\b",
        r"\bodds?\b",
        r"\bbet(?:s|ting)?\b",
        r"\bwager(?:s|ing)?\b",
        r"\bsportsbook\b",
        r"\bpayouts?\b",
        r"\bcash\s+contests?\b",
        r"\bprize\s+pools?\b",
        r"\bdfs\b",
        r"\bdraftkings\b",
        r"\bfanduel\b",
        r"\bkansas\s+city\s+chiefs\b",
        r"\bdallas\s+cowboys\b",
        r"\bgreen\s+bay\s+packers\b",
        r"\bnew\s+england\s+patriots\b",
        r"\bpittsburgh\s+steelers\b",
        r"\bsan\s+francisco\s+49ers\b",
        r"\btom\s+brady\b",
        r"\bpatrick\s+mahomes\b",
    ]

    for pattern in banned_patterns:
        assert not re.search(pattern, graph_text, flags=re.IGNORECASE), f"Graph contains banned term pattern: {pattern}"
