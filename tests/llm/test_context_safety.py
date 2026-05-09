from __future__ import annotations

import json
import re
from pathlib import Path

from coachbench.contracts import HIDDEN_OBSERVATION_FIELDS

from arena.llm.context import pack_context


DENIED = re.compile(r"^(seed.*|secret.*|api_key.*|admin.*|debug.*|.*_internal)$", re.IGNORECASE)


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            assert key not in HIDDEN_OBSERVATION_FIELDS
            assert key not in {"session_id", "ip"}
            assert not DENIED.match(str(key))
            _walk(item)
    elif isinstance(value, list):
        for item in value:
            _walk(item)


def test_pack_context_strips_hidden_debug_seed_and_secret_surfaces() -> None:
    replay = json.loads(Path("ui/showcase_replays/seed_42.json").read_text(encoding="utf-8"))
    server_context = {
        "request_type": "film_room_tweak",
        "current_run_id": "seed-42",
        "selected_play_index": 1,
        "selected_identity_id": "harbor_hawk",
        "session_id": "should-not-pass",
        "ip": "127.0.0.1",
        "debug": {"seed": 42},
        "replay": replay,
    }
    packed = pack_context(prompt="", server_context=server_context, budget_state={"remaining_calls_in_session": 2, "kill_switch": False})
    _walk(packed)
    assert "plays" not in packed
    assert packed["replay_summary"]
    assert set(packed["replay_summary"][0]) <= {
        "play_index",
        "concept",
        "counter",
        "outcome",
        "success_flag",
        "validation_ok",
        "graph_card_ids",
        "film_room_event_id",
        "film_room_events",
    }
