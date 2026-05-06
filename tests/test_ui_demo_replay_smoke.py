from __future__ import annotations

import json
import re
from pathlib import Path

from coachbench.contracts import validate_replay_contract
from coachbench.graph_loader import StrategyGraph
from coachbench.labels import is_legal_concept


def test_ui_demo_replay_shows_final_success_loop() -> None:
    replay_path = Path("ui/demo_replay.json")
    assert replay_path.exists()

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    graph_card_ids = {card["id"] for card in StrategyGraph().interactions}

    assert replay["metadata"]["mode"] != "static_proof"
    assert replay["metadata"]["seed_hash"]
    assert "seed" not in replay
    assert "seed" not in replay["metadata"]
    assert replay["plays"]

    eventful_plays = [play for play in replay["plays"] if play["public"]["events"]]
    assert eventful_plays
    for play in eventful_plays:
        for event in play["public"]["events"]:
            assert event["graph_card_id"] in graph_card_ids

    for play in replay["plays"]:
        snapshot = play["public"]["resource_budget_snapshot"]
        for key in ("offense_remaining", "defense_remaining"):
            assert snapshot[key]
            assert all(isinstance(value, (int, float)) for value in snapshot[key].values())

    chain = replay["film_room"]["adaptation_chain"]
    assert isinstance(chain, list)
    if eventful_plays:
        assert chain
    for entry in chain:
        assert {"play_index", "graph_card_id", "card_label", "offense_call", "defense_call"} <= set(entry)
        assert entry["graph_card_id"] in graph_card_ids

    assert replay["film_room"]["next_adjustment"]
    tweaks = replay["film_room"]["suggested_tweaks"]
    assert len(tweaks) == len(set(tweaks))
    for tweak in tweaks:
        for raw_id in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", tweak):
            assert is_legal_concept(raw_id)

    validate_replay_contract(replay)
