from __future__ import annotations

import json
from pathlib import Path


def test_replay_index_seeds_gallery_with_three_cards() -> None:
    index = json.loads(Path("ui/replay_index.json").read_text(encoding="utf-8"))
    ids = {entry["id"] for entry in index}

    assert {"seed-42", "static-proof", "seed-99"} <= ids
    for entry in index:
        assert entry["matchup"] == "Team A vs Team B"
        assert isinstance(entry["sparkline"], list)
        assert len(entry["sparkline"]) == entry["plays"]
        assert entry["invalid_actions"] >= 0
        assert entry["top_graph_event"]


def test_gallery_template_exposes_metrics_and_tier_chips() -> None:
    script = Path("ui/app.js").read_text(encoding="utf-8")
    html = Path("ui/replay.html").read_text(encoding="utf-8")

    for field in ("eyebrow", "matchup", "result", "sparkline", "invalid_actions", "top_graph_event"):
        assert f'data-card-field="{field}"' in script
    assert 'data-tier-chip="offense"' in script
    assert 'data-tier-chip="defense"' in script
    assert 'data-compare-id="' in script
    assert 'id="compareTray"' in html
