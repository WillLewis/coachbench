from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import types

from arena.assistant.proposal import validate_proposal
from arena.llm.client import call_llm_real
from arena.llm.context import pack_context


CANONICAL_PROMPTS = [
    "Build an offense that punishes pressure without throwing picks.",
    "Make my defense disguise more without burning the rush budget.",
    "We got baited by simulated pressure. What should I change?",
    "Build a run-first coordinator that unlocks play-action.",
    "Give me a safe red-zone defense that prevents explosives.",
]


@dataclass
class FakeUsage:
    input_tokens: int = 1200
    output_tokens: int = 220
    cache_creation_input_tokens: int = 800
    cache_read_input_tokens: int = 0


@dataclass
class FakeContent:
    text: str


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage = field(default_factory=FakeUsage)

    @property
    def content(self):
        return [FakeContent(self.text)]


def test_recorded_tape_outputs_are_schema_valid_and_grounded(monkeypatch) -> None:
    tapes = json.loads(Path("tests/fixtures/llm_tapes/canonical_responses.json").read_text(encoding="utf-8"))
    queue: list[str] = []

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse(queue.pop(0))

    class FakeAnthropic:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    fake_module = types.SimpleNamespace(Anthropic=FakeAnthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_VIRAL_SPIKE_COST_CEILING_USD", "500")
    monkeypatch.setenv("COACHBENCH_LLM_MODEL", "claude-opus-4-7")

    for prompt in CANONICAL_PROMPTS:
        for taped in tapes[prompt]:
            queue.append(json.dumps(taped, sort_keys=True, separators=(",", ":")))
            context = pack_context(prompt=prompt, server_context={}, budget_state={"remaining_calls_in_session": 8, "kill_switch": False})
            proposal, usage = call_llm_real(prompt, context, session_id="s", ip="127.0.0.1")
            validate_proposal(proposal, current_draft=None)
            legal_ids = set(context["legal_graph_cards"]) | set(context["legal_identity_ids"])
            for ref in proposal["evidence_refs"]:
                if ref["type"] == "graph_card":
                    assert ref["id"] in legal_ids
            assert usage.tokens_in > 0
            assert usage.tokens_out > 0
