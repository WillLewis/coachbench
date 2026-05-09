from __future__ import annotations

from pathlib import Path


def test_wordmark_link_points_home_on_home_and_replay_pages() -> None:
    for path in ("ui/index.html", "ui/replay.html"):
        html = Path(path).read_text(encoding="utf-8")
        assert 'href="/ui/index.html"' in html
        assert "topbar.js" in html


def test_topbar_component_exposes_desktop_and_mobile_nav() -> None:
    script = Path("ui/topbar.js").read_text(encoding="utf-8")

    assert "window.CBTopbar" in script
    assert "topbar-burger" in script
    assert "topbar-dropdown" in script
    for label in ("Home", "Film Room", "Workbench", "Reports", "Arena"):
        assert label in script
