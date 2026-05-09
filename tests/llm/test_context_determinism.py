from __future__ import annotations

import json

from arena.llm.context import pack_context


def test_pack_context_is_byte_deterministic_for_identical_inputs() -> None:
    server_context = {
        "request_type": "canonical_prompt",
        "selected_identity_id": "harbor_hawk",
        "current_draft": None,
        "replay": None,
        "user_override": None,
    }
    budget_state = {"remaining_calls_in_session": 7, "kill_switch": False}
    first = pack_context(prompt="Build an offense that punishes pressure without throwing picks.", server_context=server_context, budget_state=budget_state)
    second = pack_context(prompt="Build an offense that punishes pressure without throwing picks.", server_context=server_context, budget_state=budget_state)
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
