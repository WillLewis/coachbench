from __future__ import annotations

from pathlib import Path


def test_garage_query_navigation_is_retired_from_default_ui_path() -> None:
    app = Path("ui/app.js").read_text(encoding="utf-8")
    assert "garage.html?" not in app
    assert "navigateToGarage(" not in app
    assert "function garageUrl" not in app


def test_local_storage_garage_helpers_are_marked_offline_fallback() -> None:
    app = Path("ui/app.js").read_text(encoding="utf-8")
    for function_name in (
        "garageStateFromReplay",
        "applyTweakToGarageState",
        "loadGarageDrafts",
        "loadGarageActiveDraft",
        "persistGarageActiveDraft",
    ):
        marker = f"Offline fallback only"
        start = app.index(f"function {function_name}")
        assert marker in app[max(0, start - 160):start]
