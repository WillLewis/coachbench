from __future__ import annotations

import json
from pathlib import Path

from coachbench.contracts import validate_replay_contract


STATIC_REPLAY = Path("ui/static_proof_replay.json")


def test_static_proof_replay_validates_contract() -> None:
    replay = json.loads(STATIC_REPLAY.read_text(encoding="utf-8"))

    assert replay["metadata"]["mode"] == "static_proof"
    assert replay["metadata"]["product_boundary"] == "fictional_teams_symbolic_concepts"
    assert replay["debug"] == {"fields": []}
    validate_replay_contract(replay)


def test_static_proof_replay_exercises_visibility_and_ui_branches() -> None:
    replay = json.loads(STATIC_REPLAY.read_text(encoding="utf-8"))
    plays = replay["plays"]
    public_tags = {event["tag"] for play in plays for event in play["public"]["events"]}
    offense_tags = {event["tag"] for play in plays for event in play["offense_observed"]["events"]}
    defense_tags = {event["tag"] for play in plays for event in play["defense_observed"]["events"]}

    assert public_tags
    assert offense_tags - public_tags
    assert defense_tags - public_tags
    assert any(not play["public"]["terminal"] for play in plays)
    assert any(play["public"]["expected_value_delta"] < 0 for play in plays)
    assert plays[-1]["public"]["terminal_reason"] in {"touchdown", "field_goal"}
