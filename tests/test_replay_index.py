from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _replay(points: int, plays: int, result: str = "touchdown") -> dict:
    return {
        "metadata": {"mode": "red_zone_showcase", "max_plays": plays},
        "agents": {"offense": "Team B Adaptive Offense", "defense": "Team B Adaptive Defense"},
        "score": {"points": points, "result": result},
        "plays": [
            {
                "public": {
                    "next_state": {"points": points if index == plays else 0},
                    "events": [
                        {
                            "description": "Bear front constrains outside zone",
                            "counters": ["quick_game"],
                        }
                    ] if index == 1 else [],
                    "validation_result": {"ok": True},
                }
            }
            for index in range(1, plays + 1)
        ],
    }


def test_build_replay_index_from_fixture_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    ui_dir = tmp_path / "ui"
    out = ui_dir / "replay_index.json"
    data_dir.mkdir()
    ui_dir.mkdir()
    (data_dir / "seed_11_replay.json").write_text(json.dumps(_replay(7, 3)), encoding="utf-8")
    (data_dir / "seed_22_replay.json").write_text(json.dumps(_replay(0, 2, "stopped")), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/build_replay_index.py",
            "--data-dir",
            str(data_dir),
            "--ui-dir",
            str(ui_dir),
            "--out",
            str(out),
        ],
        check=True,
        timeout=10,
    )

    index = json.loads(out.read_text(encoding="utf-8"))

    assert [entry["id"] for entry in index] == ["seed-11", "seed-22"]
    for entry in index:
        assert {
            "id",
            "path",
            "matchup",
            "seed",
            "result",
            "outcome_chip",
            "plays",
            "top_graph_event",
            "invalid_actions",
            "tier_offense",
            "tier_defense",
            "offense_label",
            "defense_label",
            "sparkline",
            "generated_at",
        } <= set(entry)
        assert entry["matchup"] == "Team A vs Team B"
        assert entry["invalid_actions"] == 0
        assert entry["tier_offense"] == 0
        assert entry["tier_defense"] == 0
