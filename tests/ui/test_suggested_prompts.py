from __future__ import annotations

from pathlib import Path


PROMPTS = [
    "Build an offense that punishes pressure without throwing picks.",
    "Make my defense disguise more without burning the rush budget.",
    "We got baited by simulated pressure. What should I change?",
    "Build a run-first coordinator that unlocks play-action.",
    "Give me a safe red-zone defense that prevents explosives.",
]


def test_unified_shell_renders_canonical_prompt_cards() -> None:
    html = Path("ui/app.html").read_text(encoding="utf-8")
    left_rail = Path("ui/left_rail.js").read_text(encoding="utf-8")

    positions = [html.index(prompt) for prompt in PROMPTS]
    assert positions == sorted(positions)
    for prompt in PROMPTS:
        assert f'data-canonical-prompt="{prompt}"' in html
    assert "type: 'canonical_prompt'" in left_rail
    assert "coachbench:assistant:request" in left_rail
