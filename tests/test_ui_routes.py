from __future__ import annotations

import re
from pathlib import Path


def test_unified_shell_declares_route_sections() -> None:
    app_html = Path("ui/app.html").read_text(encoding="utf-8")

    routes = set(re.findall(r'data-route="([^"]+)"', app_html))

    assert routes == {"replays", "replay-detail", "reports", "arena", "garage"}


def test_top_nav_routes_into_home_or_unified_shell() -> None:
    topbar = Path("ui/topbar.js").read_text(encoding="utf-8")

    for label in ("Home", "Film Room", "Workbench", "Reports", "Arena"):
        assert label in topbar
    for href in ("/ui/index.html", "/ui/app.html#/replays", "/ui/app.html#/garage", "/ui/app.html#/reports", "/ui/app.html#/arena"):
        assert href in topbar


def test_legacy_pages_redirect_to_unified_shell() -> None:
    routes = {
        "ui/replays.html": "app.html#/replays",
        "ui/garage.html": "app.html#/garage",
        "ui/replay.html": "app.html",
        "ui/reports.html": "app.html#/reports",
        "ui/arena.html": "app.html#/arena",
    }
    for path, target in routes.items():
        assert target in Path(path).read_text(encoding="utf-8")


def test_router_defaults_empty_or_unknown_hash_to_replays() -> None:
    router = Path("ui/router.js").read_text(encoding="utf-8")

    assert "DEFAULT_HASH = '#/replays'" in router
    assert "if (!location.hash || !isKnown(splitHash().path)) location.hash = DEFAULT_HASH" in router
