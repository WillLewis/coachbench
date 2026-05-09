from __future__ import annotations

import pytest

from arena.llm.context import pack_context


@pytest.mark.parametrize("bad", ["seed value", "debug note", "api_key leak", "admin token", "Tier 2 path"])
def test_pack_context_rejects_unsafe_film_room_narrative_text(bad: str) -> None:
    with pytest.raises(ValueError):
        pack_context(
            prompt="What should I change?",
            server_context={"replay": {"plays": [], "film_room": {"narrative": bad}}},
            budget_state={"remaining_calls_in_session": 8, "kill_switch": False},
        )
