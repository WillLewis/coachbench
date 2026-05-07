from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(".")
MOTION_TOKENS = {
    "--motion-card-swap",
    "--motion-ball",
    "--motion-outcome",
    "--motion-inspector",
    "--motion-belief-pulse",
    "--autoplay-interval",
}


def test_css_motion_declarations_use_motion_tokens() -> None:
    css = (ROOT / "ui/styles.css").read_text(encoding="utf-8")

    assert "--t-fast" not in css
    assert "--t-base" not in css
    assert "--t-slow" not in css
    assert "--t-mount" not in css
    assert "--stagger" not in css

    declarations = re.findall(r"(?:transition|animation(?:-duration)?):\s*([^;]+);", css)
    for declaration in declarations:
        if "none" in declaration:
            continue
        assert any(token in declaration for token in MOTION_TOKENS) or "0ms" in declaration


def test_js_motion_timing_reads_css_tokens() -> None:
    script = (ROOT / "ui/app.js").read_text(encoding="utf-8")

    assert "motionMs('--motion-outcome')" in script
    assert "motionMs('--motion-belief-pulse')" in script
    assert "motionMs('--autoplay-interval')" in script
    assert "animationDelay = 'var(--motion-card-swap)'" in script
    assert "setTimeout(() => { el.textContent = next; el.style.opacity = '1'; }, 150)" not in script
    assert "setTimeout(() => { runtime.autoScrolling = false; }, reduced() ? 0 : 260)" not in script
    assert "* 40}ms" not in script


def test_mobile_breakpoint_policy_is_declared() -> None:
    css = (ROOT / "ui/styles.css").read_text(encoding="utf-8")
    html = (ROOT / "ui/replay.html").read_text(encoding="utf-8")

    assert "@media (min-width: 640px)" in css
    assert "@media (max-width: 639px)" in css
    assert ".feed-panel { position: static; order: -1; max-height: none; }" in css
    assert ".field { min-height: 0; aspect-ratio: 16 / 9; }" in css
    assert ".garage-workbench { display: none; }" in css
    assert "Garage works best on desktop. Switch to a larger screen to edit, or browse your drafts in read-only mode." in html
