from __future__ import annotations

import json
from pathlib import Path

from arena.assistant.templates import propose_from_prompt


CANONICAL_PROMPTS = [
    "Build an offense that punishes pressure without throwing picks.",
    "Make my defense disguise more without burning the rush budget.",
    "We got baited by simulated pressure. What should I change?",
    "Build a run-first coordinator that unlocks play-action.",
    "Give me a safe red-zone defense that prevents explosives.",
]


def test_canonical_templates_only_emit_glossary_parameters() -> None:
    glossary = json.loads(Path("agent_garage/parameter_glossary.json").read_text(encoding="utf-8"))
    for prompt in CANONICAL_PROMPTS:
        proposal = propose_from_prompt(prompt, {}, session_id="s", ip="ip")
        for change in proposal["proposed_changes"]:
            assert change["parameter"] in glossary
