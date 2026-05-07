from __future__ import annotations

import json
import re
from pathlib import Path

from coachbench.contracts import validate_replay_contract


BANNED = re.compile(r"\b(nfl|nflpa|ncaa|super bowl|madden|dfs|draftkings|fanduel|odds|bet|wager)\b", re.I)
HANDLE = re.compile(r"^[a-z0-9_]+$")


def test_home_page_declares_fixed_headline() -> None:
    html = Path("ui/index.html").read_text(encoding="utf-8")

    assert "Can your agent discover the edge before the opponent adjusts?" in html


def test_showcase_manifest_has_twelve_valid_fictional_replays() -> None:
    manifest = json.loads(Path("ui/showcase_manifest.json").read_text(encoding="utf-8"))
    replays = manifest["replays"]

    assert len(replays) >= 12
    for entry in replays:
        assert HANDLE.match(entry["offense_handle"])
        assert HANDLE.match(entry["defense_handle"])
        assert not BANNED.search(entry["offense_handle"])
        assert not BANNED.search(entry["defense_handle"])
        assert entry["offense_tier"] in {"declarative", "prompt_policy"}
        assert entry["defense_tier"] in {"declarative", "prompt_policy"}
        replay_path = Path("ui") / entry["replay_path"]
        assert replay_path.exists()
        validate_replay_contract(json.loads(replay_path.read_text(encoding="utf-8")))


def test_home_manifest_cards_have_required_summary_fields() -> None:
    manifest = json.loads(Path("ui/showcase_manifest.json").read_text(encoding="utf-8"))

    for entry in manifest["replays"]:
        summary = entry["summary"]
        assert {"result", "points", "plays", "invalid_action_count", "top_concept"} <= set(summary)
        assert isinstance(entry["ep_sparkline"], list)
        assert entry["ep_sparkline"]
