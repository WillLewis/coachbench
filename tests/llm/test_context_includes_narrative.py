from __future__ import annotations

from arena.llm.context import pack_context


def test_pack_context_includes_top_level_film_room_narrative() -> None:
    narrative = "You attacked Screens can punish true pressure with Screen against Zero Pressure."
    payload = pack_context(
        prompt="What should I change?",
        server_context={"replay": {"plays": [], "film_room": {"narrative": narrative}}},
        budget_state={"remaining_calls_in_session": 8, "kill_switch": False},
    )
    assert payload["film_room_narrative"] == narrative
    assert "narrative" not in (payload["replay_summary"][0] if payload["replay_summary"] else {})


def test_pack_context_sets_film_room_narrative_none_when_absent() -> None:
    assert pack_context(prompt="", server_context={"replay": {"film_room": {"narrative": None}, "plays": []}}, budget_state={})["film_room_narrative"] is None
    assert pack_context(prompt="", server_context={}, budget_state={})["film_room_narrative"] is None
