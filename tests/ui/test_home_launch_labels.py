from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_home_featured_replay_uses_launch_identity_labels() -> None:
    home_js = (ROOT / "ui/home.js").read_text(encoding="utf-8")

    assert "item.offense_label || compact(item.offense_handle)" in home_js
    assert "item.defense_label || compact(item.defense_handle)" in home_js
    assert "${item.offense_handle} ⇌ ${item.defense_handle}" not in home_js
