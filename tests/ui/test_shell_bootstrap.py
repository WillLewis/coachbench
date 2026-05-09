from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_shell_root_marker_boots_left_rail_and_assistant() -> None:
    html = (ROOT / "ui/app.html").read_text(encoding="utf-8")
    left_rail = (ROOT / "ui/left_rail.js").read_text(encoding="utf-8")
    assistant = (ROOT / "ui/assistant.js").read_text(encoding="utf-8")

    assert 'data-shell-root="true"' in html
    assert ".hasAttribute('data-shell-root')" in left_rail
    assert ".hasAttribute('data-shell-root')" in assistant


def test_shell_css_does_not_reserve_drawer_column_until_open() -> None:
    css = (ROOT / "ui/styles.css").read_text(encoding="utf-8")

    assert "body.right-drawer-open .coachbench-shell" in css
    base_rule = css.split(".coachbench-shell {", 1)[1].split("}", 1)[0]
    assert "minmax(380px, 44vw)" not in base_rule


def test_shell_cache_tag_is_current() -> None:
    html = (ROOT / "ui/app.html").read_text(encoding="utf-8")
    assert "styles.css?v=p0-7-shell-fix-v1" in html
    assert "p0-5-assistant-v1" not in html
    assert "p0-4-shell-v1" not in "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ["ui/replay.html", "ui/replays.html", "ui/garage.html", "ui/reports.html", "ui/arena.html"]
    )
