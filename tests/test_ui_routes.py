from __future__ import annotations

import re
from pathlib import Path


def test_ui_declares_five_hash_route_sections() -> None:
    html = Path("ui/index.html").read_text(encoding="utf-8")

    routes = set(re.findall(r'data-route="([^"]+)"', html))

    assert routes == {"replays", "replay-detail", "garage", "reports", "arena"}


def test_top_nav_has_four_visible_route_links() -> None:
    html = Path("ui/index.html").read_text(encoding="utf-8")

    links = re.findall(r'<a href="#/[^"]+" data-route-link="([^"]+)">([^<]+)</a>', html)

    assert links == [
        ("replays", "Replays"),
        ("garage", "Garage"),
        ("reports", "Reports"),
        ("arena", "Arena"),
    ]


def test_router_defaults_empty_or_unknown_hash_to_replays() -> None:
    router = Path("ui/router.js").read_text(encoding="utf-8")

    assert "DEFAULT_HASH = '#/replays'" in router
    assert "if (!location.hash || !isKnown(pathFromHash())) location.hash = DEFAULT_HASH" in router
