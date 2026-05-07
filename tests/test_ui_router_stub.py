from __future__ import annotations

from pathlib import Path


def test_ui_loads_state_router_before_app() -> None:
    html = Path("ui/replay.html").read_text(encoding="utf-8")

    state_index = html.index('src="state.js"')
    router_index = html.index('src="router.js"')
    app_index = html.index('src="app.js"')

    assert state_index < router_index < app_index
