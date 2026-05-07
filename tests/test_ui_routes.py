from __future__ import annotations

import re
from pathlib import Path


def test_ui_declares_five_hash_route_sections() -> None:
    html = Path("ui/replay.html").read_text(encoding="utf-8")

    routes = set(re.findall(r'data-route="([^"]+)"', html))

    assert routes == {"replays", "replay-detail", "garage", "reports", "arena"}


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
