from __future__ import annotations

from pathlib import Path


ROOT = Path(".")
MOTION_TOKENS = (
    "--motion-card-swap",
    "--motion-ball",
    "--motion-outcome",
    "--motion-inspector",
    "--motion-belief-pulse",
    "--autoplay-interval",
)


def test_reduced_motion_media_block_zeroes_every_motion_token() -> None:
    css = (ROOT / "ui/styles.css").read_text(encoding="utf-8")

    assert "@media (prefers-reduced-motion: reduce)" in css
    for token in MOTION_TOKENS:
        assert f"{token}: 0ms;" in css
    assert "animation-duration: 0ms !important;" in css
    assert "transition-duration: 0ms !important;" in css
    assert "scroll-behavior: auto !important;" in css
    assert ".autoplay-progress.running::before { animation: none !important; }" in css


def test_reduced_motion_class_hook_stops_autoplay() -> None:
    script = (ROOT / "ui/app.js").read_text(encoding="utf-8")

    assert "classList.contains('reduced-motion')" in script
    assert "classList.toggle('reduced-motion', motionQuery.matches)" in script
    assert "runtime.auto?.stop()" in script
    assert "if (reduced() || running || count < 2 || intervalMs <= 0) return;" in script
