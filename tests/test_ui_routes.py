from __future__ import annotations

import re
from pathlib import Path


def test_replay_and_standalone_pages_declare_route_sections() -> None:
    replay_html = Path("ui/replay.html").read_text(encoding="utf-8")
    garage_html = Path("ui/garage.html").read_text(encoding="utf-8")

    replay_routes = set(re.findall(r'data-route="([^"]+)"', replay_html))

    assert replay_routes == {"replays", "replay-detail", "reports", "arena"}
    assert 'data-route="garage"' in garage_html


def test_top_nav_has_four_visible_route_links() -> None:
    topbar = Path("ui/topbar.js").read_text(encoding="utf-8")

    for label in ("Home", "Replays", "Garage", "Reports", "Arena"):
        assert label in topbar
    for href in ("/ui/index.html", "/ui/replays.html", "/ui/garage.html", "/ui/reports.html", "/ui/arena.html"):
        assert href in topbar


def test_router_defaults_empty_or_unknown_hash_to_replays() -> None:
    router = Path("ui/router.js").read_text(encoding="utf-8")

    assert "DEFAULT_HASH = '#/replays'" in router
    assert "if (!location.hash || !isKnown(splitHash().path)) location.hash = DEFAULT_HASH" in router
