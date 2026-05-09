from __future__ import annotations

import json
from pathlib import Path

from coachbench.graph_loader import StrategyGraph
from coachbench.identities import load_identities

from arena.assistant.proposal import base_declarative_config, validate_proposal
from arena.assistant.templates import propose_from_prompt


def _graph_cards() -> set[str]:
    return {card["id"] for card in StrategyGraph().interactions}


def _identity_ids() -> set[str]:
    return {identity.id for identity in load_identities()}


def _draft() -> dict:
    return {"id": "draft-1", "config_json": base_declarative_config("offense")}


def test_stub_evidence_refs_resolve_to_known_sources() -> None:
    proposal = propose_from_prompt(
        "Build an offense that punishes pressure without throwing picks.",
        {"selected_identity_id": "harbor_hawk"},
        session_id="s",
        ip="ip",
    )
    for ref in proposal["evidence_refs"]:
        if ref["type"] == "graph_card":
            assert ref["id"] in _graph_cards()
        elif ref["type"] == "identity_fact":
            assert ref["id"].split(":", 1)[0] in _identity_ids()
        else:
            raise AssertionError(f"unexpected evidence type: {ref['type']}")


def test_film_room_tweak_evidence_resolves_to_real_replay_play() -> None:
    replay = json.loads(Path("ui/showcase_replays/seed_42.json").read_text(encoding="utf-8"))
    proposal = propose_from_prompt(
        "",
        {
            "request_type": "film_room_tweak",
            "current_draft": _draft(),
            "current_run_id": "seed-42",
            "selected_play_index": 1,
            "replay": replay,
        },
        session_id="s",
        ip="ip",
    )
    validate_proposal(proposal, current_draft=_draft(), context={"replay": replay})
    film_refs = [ref for ref in proposal["evidence_refs"] if ref["type"] == "film_room_event"]
    assert film_refs
    replay_play_indexes = {play["public"]["play_index"] for play in replay["plays"]}
    assert film_refs[0]["play_index"] in replay_play_indexes
