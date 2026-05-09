from __future__ import annotations

from pathlib import Path


def test_replay_detail_has_feed_layout_and_resume_control() -> None:
    html = Path("ui/app.html").read_text(encoding="utf-8")

    assert 'class="replay-layout row-mount"' in html
    assert 'id="playFeed"' in html
    assert 'id="resumeFeed"' in html
    assert 'class="right-drawer"' in html
    assert "Adaptation Chain" not in html


def test_replay_feed_uses_adaptation_annotations_not_section_render() -> None:
    script = Path("ui/app.js").read_text(encoding="utf-8")

    assert "is_adaptation" in script
    assert "adaptation_reason" in script
    assert "CBAdaptation.classifyAdaptationReasons" in script
    assert "data-assistant-play" in script
    assert "function renderAdaptationChain" not in script
