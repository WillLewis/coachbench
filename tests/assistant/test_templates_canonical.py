from __future__ import annotations

import json

from arena.assistant.proposal import validate_proposal
from arena.assistant.templates import propose_from_prompt


CANONICAL_PROMPTS = [
    "Build an offense that punishes pressure without throwing picks.",
    "Make my defense disguise more without burning the rush budget.",
    "We got baited by simulated pressure. What should I change?",
    "Build a run-first coordinator that unlocks play-action.",
    "Give me a safe red-zone defense that prevents explosives.",
]


def test_canonical_prompts_are_stable_and_valid_across_three_retries() -> None:
    for prompt in CANONICAL_PROMPTS:
        outputs = [
            propose_from_prompt(prompt, {}, session_id="session", ip="127.0.0.1")
            for _ in range(3)
        ]
        encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in outputs]
        assert encoded[0] == encoded[1] == encoded[2]
        validate_proposal(outputs[0], current_draft=None)
